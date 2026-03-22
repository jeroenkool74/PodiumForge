from __future__ import annotations

import re
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    AdvancementKind,
    MatchStatus,
    ParticipantKind,
    RoundStatus,
    TournamentFormat,
    TournamentStatus,
)
from app.core.tournament_formats import (
    requires_manual_advance_count,
    uses_fixed_head_to_head_matches,
)
from app.models import (
    AdvancementRule,
    Match,
    MatchParticipant,
    MatchResult,
    Participant,
    PointsScheme,
    Round,
    Stage,
    Team,
    TieBreakRule,
    Tournament,
    User,
)
from app.repositories.tournaments import get_tournament_by_identifier
from app.services.directory_service import (
    load_directory_players_by_ids,
    load_directory_team,
    load_directory_teams_by_ids,
    team_directory_member_names,
)
from app.services.tie_break_service import (
    DEFAULT_TIE_BREAK_RULES,
    normalize_tie_break_rules,
)
from app.schemas.tournament import (
    ParticipantCreateRequest,
    TournamentCreateRequest,
    TournamentUpdateRequest,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "tournament"


def ensure_unique_slug(db: Session, name: str) -> str:
    base_slug = slugify(name)
    candidate = base_slug
    suffix = 2
    while get_tournament_by_identifier(db, candidate, public_only=False):
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate


def build_points_mapping(points_scheme: list) -> dict[str, int]:
    if not points_scheme:
        return {"1": 10, "2": 7, "3": 5, "4": 3, "5": 1}
    return {str(item.placement): item.points for item in points_scheme}


DOUBLE_ELIMINATION_WINNERS = "WINNERS"
DOUBLE_ELIMINATION_LOSERS = "LOSERS"
DOUBLE_ELIMINATION_GRAND_FINAL = "GRAND_FINAL"
PAGE_PLAYOFF_OPENING = "OPENING"
PAGE_PLAYOFF_QUALIFIER = "QUALIFIER"
PAGE_PLAYOFF_ELIMINATOR = "ELIMINATOR"


def is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def ensure_unique_participant_names(names: list[str]) -> None:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for name in names:
        normalized = name.strip().lower()
        if normalized in seen:
            duplicates.append(name.strip())
            continue
        seen[normalized] = name.strip()
    if duplicates:
        duplicate_names = ", ".join(sorted({name for name in duplicates}))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Participant names must be unique within a tournament: {duplicate_names}",
        )


def chunk_participants(
    participants: list[Participant], match_size: int
) -> list[list[Participant]]:
    return [
        participants[index : index + match_size]
        for index in range(0, len(participants), match_size)
    ]


def next_power_of_two(value: int) -> int:
    power = 1
    while power < value:
        power *= 2
    return power


def build_bracket_seed_order(field_size: int) -> list[int]:
    order = [1, 2]
    while len(order) < field_size:
        mirror = len(order) * 2 + 1
        order = [
            seed
            for pair in zip(order, [mirror - seed for seed in order])
            for seed in pair
        ]
    return order


def bracket_round_name(field_size: int) -> str:
    names = {
        2: "Final",
        4: "Semifinals",
        8: "Quarterfinals",
    }
    return names.get(field_size, f"Round of {field_size}")


def bracket_match_name(round_name: str, match_index: int, total_matches: int) -> str:
    if total_matches == 1:
        return round_name
    singular_name = {
        "Quarterfinals": "Quarterfinal",
        "Semifinals": "Semifinal",
    }.get(round_name, round_name)
    return f"{singular_name} {match_index}"


def double_elimination_round_name(
    kind: str, bracket_round: int, field_size: int
) -> str:
    total_winners_rounds = field_size.bit_length() - 1
    if kind == DOUBLE_ELIMINATION_WINNERS:
        entrants_in_round = max(2, field_size // (2 ** (bracket_round - 1)))
        base_name = bracket_round_name(entrants_in_round)
        return f"Winners {base_name}" if base_name != "Final" else "Winners Final"
    if kind == DOUBLE_ELIMINATION_LOSERS:
        if bracket_round == 2 * total_winners_rounds - 2:
            return "Losers Final"
        return f"Losers Round {bracket_round}"
    return "Grand Final"


def double_elimination_match_name(
    round_name: str, match_index: int, total_matches: int
) -> str:
    if total_matches == 1:
        return round_name
    return f"{round_name} {match_index}"


def round_robin_round_count(participant_count: int) -> int:
    if participant_count <= 1:
        return 0
    return participant_count - 1 if participant_count % 2 == 0 else participant_count


def swiss_round_count(participant_count: int) -> int:
    if participant_count <= 1:
        return 0
    return (participant_count - 1).bit_length()


def build_round_robin_groups(
    participants: list[Participant], round_number: int
) -> list[list[Participant]]:
    if round_number < 1:
        return []

    rotation: list[Participant | None] = list(participants)
    if len(rotation) % 2 == 1:
        rotation.append(None)

    total_rounds = len(rotation) - 1
    if round_number > total_rounds:
        return []

    for _ in range(round_number - 1):
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

    groups: list[list[Participant]] = []
    for index in range(len(rotation) // 2):
        left = rotation[index]
        right = rotation[-(index + 1)]
        if left is None or right is None:
            continue
        groups.append([left, right])
    return groups


def build_swiss_opening_groups(
    participants: list[Participant],
) -> list[list[Participant]]:
    ordered = list(participants)
    bye_group: list[list[Participant]] = []
    if len(ordered) % 2 == 1:
        bye_group = [[ordered[-1]]]
        ordered = ordered[:-1]

    midpoint = len(ordered) // 2
    top_half = ordered[:midpoint]
    bottom_half = ordered[midpoint:]
    groups = [[top_half[index], bottom_half[index]] for index in range(len(top_half))]
    return groups + bye_group


def resolve_participant_blueprints(
    db: Session, payload: TournamentCreateRequest
) -> list[dict]:
    blueprints = [
        {"name": name.strip(), "members": []}
        for name in payload.participants
        if name.strip()
    ]

    if payload.participant_type == ParticipantKind.TEAM:
        for team in load_directory_teams_by_ids(db, payload.directory_team_ids):
            blueprints.append(
                {
                    "name": team.name,
                    "members": team_directory_member_names(team),
                    "directory_entry_id": team.id,
                }
            )
    else:
        for player in load_directory_players_by_ids(db, payload.directory_player_ids):
            blueprints.append(
                {
                    "name": player.name,
                    "members": [],
                    "directory_entry_id": player.id,
                }
            )

    return blueprints


def create_tournament(
    db: Session, payload: TournamentCreateRequest, actor: User
) -> Tournament:
    participant_blueprints = resolve_participant_blueprints(db, payload)
    names = [item["name"] for item in participant_blueprints]
    ensure_unique_participant_names(names)
    effective_match_size = (
        2 if uses_fixed_head_to_head_matches(payload.format) else payload.match_size
    )
    if len(names) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least two participants are required",
        )
    if (
        requires_manual_advance_count(payload.format)
        and len(names) > effective_match_size
        and payload.advance_count is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advance count is required for multi-match formats",
        )
    points_mapping = (
        {"1": 3, "2": 0}
        if uses_fixed_head_to_head_matches(payload.format) and not payload.points_scheme
        else build_points_mapping(payload.points_scheme)
    )
    if payload.format == TournamentFormat.PAGE_PLAYOFF and len(names) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page playoff requires exactly 4 seeded participants",
        )

    tournament = Tournament(
        name=payload.name,
        slug=ensure_unique_slug(db, payload.name),
        description=payload.description,
        format=payload.format.value,
        participant_type=payload.participant_type.value,
        status=TournamentStatus.LIVE.value,
        is_public=payload.is_public,
        settings={"match_size": effective_match_size},
        created_by=actor,
    )
    db.add(tournament)

    points_scheme = PointsScheme(
        name="Default points",
        placements=points_mapping,
        tournament=tournament,
    )
    tie_break_rule = TieBreakRule(
        name="Default tie-breaks",
        rules=[dict(rule) for rule in DEFAULT_TIE_BREAK_RULES],
        tournament=tournament,
    )
    stage = Stage(
        name="Main Stage",
        order_index=1,
        tournament=tournament,
        settings={
            "match_size": effective_match_size,
            "format": payload.format.value,
            **(
                {"field_size": len(names)}
                if payload.format == TournamentFormat.DOUBLE_ELIMINATION
                else {}
            ),
            **(
                {"round_robin_total_rounds": round_robin_round_count(len(names))}
                if payload.format == TournamentFormat.ROUND_ROBIN
                else {}
            ),
            **(
                {"swiss_total_rounds": swiss_round_count(len(names))}
                if payload.format == TournamentFormat.SWISS
                else {}
            ),
        },
        points_scheme=points_scheme,
        tie_break_rule=tie_break_rule,
    )
    db.add_all([points_scheme, tie_break_rule, stage])

    participants: list[Participant] = []
    for index, blueprint in enumerate(participant_blueprints, start=1):
        display_name = blueprint["name"]
        metadata_json = {}
        if blueprint.get("directory_entry_id"):
            metadata_json["directory_entry_id"] = blueprint["directory_entry_id"]
        if blueprint.get("members"):
            metadata_json["members"] = list(blueprint["members"])
        if payload.participant_type.value == ParticipantKind.TEAM.value:
            team = Team(tournament=tournament, name=display_name, seed_number=index)
            participant = Participant(
                tournament=tournament,
                team=team,
                display_name=display_name,
                kind=ParticipantKind.TEAM.value,
                seed_number=index,
                metadata_json=metadata_json,
            )
            db.add(team)
        else:
            participant = Participant(
                tournament=tournament,
                display_name=display_name,
                kind=ParticipantKind.PLAYER.value,
                seed_number=index,
                metadata_json=metadata_json,
            )
        participants.append(participant)
        db.add(participant)

    if payload.format == TournamentFormat.STANDALONE_MATCH:
        round_name = "Feature Match"
        groups = [participants]
        is_final = True
    elif payload.format == TournamentFormat.ROUND_ROBIN:
        round_name = "Round 1"
        groups = build_round_robin_groups(participants, 1)
        is_final = round_robin_round_count(len(participants)) == 1
    elif payload.format == TournamentFormat.SWISS:
        round_name = "Round 1"
        groups = build_swiss_opening_groups(participants)
        is_final = swiss_round_count(len(participants)) == 1
    elif payload.format == TournamentFormat.PAGE_PLAYOFF:
        round_name = "Opening Round"
        groups = [
            [participants[0], participants[1]],
            [participants[2], participants[3]],
        ]
        is_final = False
    elif payload.format == TournamentFormat.BRACKET:
        field_size = next_power_of_two(len(participants))
        bracket_slots = [
            {participant.seed_number: participant for participant in participants}.get(
                seed
            )
            for seed in build_bracket_seed_order(field_size)
        ]
        groups = [
            [
                participant
                for participant in bracket_slots[index : index + 2]
                if participant
            ]
            for index in range(0, len(bracket_slots), 2)
        ]
        round_name = bracket_round_name(field_size)
        is_final = len(groups) == 1
    elif payload.format == TournamentFormat.DOUBLE_ELIMINATION:
        if len(participants) < 4 or not is_power_of_two(len(participants)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Double-elimination brackets require a power-of-two field of at least 4 participants",
            )
        groups = chunk_participants(
            [
                {participant.seed_number: participant for participant in participants}[
                    seed
                ]
                for seed in build_bracket_seed_order(len(participants))
            ],
            2,
        )
        round_name = double_elimination_round_name(
            DOUBLE_ELIMINATION_WINNERS, 1, len(participants)
        )
        is_final = False
    else:
        round_name = "Round 1"
        groups = chunk_participants(participants, effective_match_size)
        is_final = len(groups) == 1 and len(participants) <= effective_match_size

    effective_advance_count = (
        1
        if payload.format == TournamentFormat.BRACKET and not is_final
        else None
        if payload.format
        in {
            TournamentFormat.ROUND_ROBIN,
            TournamentFormat.SWISS,
            TournamentFormat.PAGE_PLAYOFF,
        }
        else payload.advance_count
    )
    if (
        effective_advance_count
        and payload.format != TournamentFormat.DOUBLE_ELIMINATION
    ):
        advancement_kind = AdvancementKind.MATCH_TOP_N
        if payload.format == TournamentFormat.GROUP_POINTS:
            advancement_kind = AdvancementKind.STANDINGS_TOP_N
        rule = AdvancementRule(
            stage=stage,
            name="Primary advancement",
            kind=advancement_kind.value,
            apply_after_round=1,
            config={"top_n": effective_advance_count},
        )
        db.add(rule)

    initial_round = Round(
        stage=stage,
        name=round_name,
        number=1,
        order_index=1,
        status=RoundStatus.ACTIVE.value,
        is_final=is_final,
        settings={
            "expected_match_count": len(groups),
            **(
                {
                    "bracket_kind": DOUBLE_ELIMINATION_WINNERS,
                    "bracket_round": 1,
                }
                if payload.format == TournamentFormat.DOUBLE_ELIMINATION
                else {}
            ),
            **(
                {"page_round_kind": PAGE_PLAYOFF_OPENING}
                if payload.format == TournamentFormat.PAGE_PLAYOFF
                else {}
            ),
        },
    )
    db.add(initial_round)

    for index, group in enumerate(groups, start=1):
        match_name = (
            bracket_match_name(round_name, index, len(groups))
            if payload.format == TournamentFormat.BRACKET
            else (
                double_elimination_match_name(round_name, index, len(groups))
                if payload.format == TournamentFormat.DOUBLE_ELIMINATION
                else (
                    "Qualifier"
                    if payload.format == TournamentFormat.PAGE_PLAYOFF and index == 1
                    else (
                        "Eliminator"
                        if payload.format == TournamentFormat.PAGE_PLAYOFF
                        and index == 2
                        else (
                            f"Match {chr(64 + index)}"
                            if len(groups) > 1
                            else round_name
                        )
                    )
                )
            )
        )
        match = Match(
            round=initial_round,
            name=match_name,
            sequence=index,
            status=(
                MatchStatus.COMPLETED.value
                if payload.format in {TournamentFormat.BRACKET, TournamentFormat.SWISS}
                and len(group) == 1
                else MatchStatus.SCHEDULED.value
            ),
            settings={
                "group_size": len(group),
                **(
                    {
                        "page_match_kind": (
                            PAGE_PLAYOFF_QUALIFIER
                            if index == 1
                            else PAGE_PLAYOFF_ELIMINATOR
                        )
                    }
                    if payload.format == TournamentFormat.PAGE_PLAYOFF
                    else {}
                ),
            },
        )
        db.add(match)
        for slot_index, participant in enumerate(group, start=1):
            db.add(
                MatchParticipant(
                    match=match,
                    participant=participant,
                    slot_number=slot_index,
                    seed_number=participant.seed_number,
                )
            )
        if (
            payload.format in {TournamentFormat.BRACKET, TournamentFormat.SWISS}
            and len(group) == 1
        ):
            db.add(
                MatchResult(
                    match=match,
                    participant=group[0],
                    rank=1,
                    points_awarded=int(points_mapping.get("1", 0)),
                )
            )

    if all(len(group) == 1 for group in groups):
        initial_round.status = RoundStatus.COMPLETED.value

    db.commit()
    return (
        db.scalar(select(Tournament).where(Tournament.id == tournament.id))
        or tournament
    )


def update_tournament(
    db: Session, tournament: Tournament, payload: TournamentUpdateRequest
) -> Tournament:
    if payload.name is not None:
        tournament.name = payload.name
    if payload.description is not None:
        tournament.description = payload.description
    if payload.status is not None:
        tournament.status = payload.status.value
    if payload.is_public is not None:
        tournament.is_public = payload.is_public
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


def add_participant(
    db: Session, tournament: Tournament, payload: ParticipantCreateRequest
) -> Participant:
    display_name = payload.display_name.strip()
    metadata_json: dict = {}

    if payload.directory_entry_id:
        if tournament.participant_type == ParticipantKind.TEAM.value:
            team_entry = load_directory_team(db, payload.directory_entry_id)
            if not team_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Directory team not found",
                )
            display_name = team_entry.name
            metadata_json["directory_entry_id"] = team_entry.id
            metadata_json["members"] = team_directory_member_names(team_entry)
        else:
            players = load_directory_players_by_ids(db, [payload.directory_entry_id])
            player = players[0] if players else None
            if not player:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Directory player not found",
                )
            display_name = player.name
            metadata_json["directory_entry_id"] = player.id
    elif (
        tournament.participant_type == ParticipantKind.TEAM.value
        and payload.team_members
    ):
        metadata_json["members"] = [
            member.strip() for member in payload.team_members if member.strip()
        ]

    ensure_unique_participant_names(
        [participant.display_name for participant in tournament.participants]
        + [display_name]
    )
    stage = sorted(tournament.stages, key=lambda item: item.order_index)[0]
    existing_rounds = sorted(stage.rounds, key=lambda item: item.number)
    if any(
        match.participants
        for round_item in existing_rounds
        for match in round_item.matches
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add participants after match generation in this MVP",
        )
    seed_number = payload.seed_number or len(tournament.participants) + 1
    participant = Participant(
        tournament=tournament,
        display_name=display_name,
        kind=tournament.participant_type,
        seed_number=seed_number,
        metadata_json=metadata_json,
    )
    if tournament.participant_type == ParticipantKind.TEAM.value:
        participant.team = Team(
            tournament=tournament, name=display_name, seed_number=seed_number
        )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def expected_round_count(
    total_participants: int, match_size: int, top_n: int | None
) -> int:
    if not top_n or total_participants <= match_size:
        return 1
    rounds = 1
    current = total_participants
    while current > match_size:
        current = ceil(current / match_size) * top_n
        rounds += 1
    return rounds
