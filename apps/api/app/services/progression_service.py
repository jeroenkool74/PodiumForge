from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import AdvancementKind, MatchStatus, RoundStatus, TournamentFormat
from app.core.scoring import score_sort_value
from app.models import (
    AdvancementRule,
    Match,
    MatchParticipant,
    MatchResult,
    Participant,
    Round,
    Tournament,
)
from app.services.tournament_status_service import refresh_tournament_status

DOUBLE_ELIMINATION_WINNERS = "WINNERS"
DOUBLE_ELIMINATION_LOSERS = "LOSERS"
DOUBLE_ELIMINATION_GRAND_FINAL = "GRAND_FINAL"
DOUBLE_ELIMINATION_GRAND_FINAL_RESET = "GRAND_FINAL_RESET"
PAGE_PLAYOFF_OPENING = "OPENING"
PAGE_PLAYOFF_QUALIFIER = "QUALIFIER"
PAGE_PLAYOFF_ELIMINATOR = "ELIMINATOR"
PAGE_PLAYOFF_PRELIMINARY_FINAL = "PRELIMINARY_FINAL"
PAGE_PLAYOFF_GRAND_FINAL = "GRAND_FINAL"


def get_stage_match_size(round_item: Round) -> int:
    return int(round_item.stage.settings.get("match_size", 5))


def get_round_rule(round_item: Round) -> AdvancementRule | None:
    rules = sorted(
        round_item.stage.advancement_rules, key=lambda item: item.apply_after_round
    )
    applicable_rules = [
        rule for rule in rules if rule.apply_after_round <= round_item.number
    ]
    return applicable_rules[-1] if applicable_rules else None


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
    if kind == DOUBLE_ELIMINATION_GRAND_FINAL_RESET:
        return "Grand Final Reset"
    return "Grand Final"


def double_elimination_match_name(
    round_name: str, match_index: int, total_matches: int
) -> str:
    if total_matches == 1:
        return round_name
    return f"{round_name} {match_index}"


def is_double_elimination_stage(stage) -> bool:
    return stage.settings.get("format") == TournamentFormat.DOUBLE_ELIMINATION.value


def is_round_robin_stage(stage) -> bool:
    return stage.settings.get("format") == TournamentFormat.ROUND_ROBIN.value


def is_leaderboard_series_stage(stage) -> bool:
    return stage.settings.get("format") == TournamentFormat.LEADERBOARD_SERIES.value


def is_swiss_stage(stage) -> bool:
    return stage.settings.get("format") == TournamentFormat.SWISS.value


def is_page_playoff_stage(stage) -> bool:
    return stage.settings.get("format") == TournamentFormat.PAGE_PLAYOFF.value


def main_stage(tournament: Tournament):
    return sorted(tournament.stages, key=lambda item: item.order_index)[0]


def ordered_stage_rounds(stage) -> list[Round]:
    return sorted(stage.rounds, key=lambda item: item.number)


def ordered_matches(round_item: Round) -> list[Match]:
    return sorted(round_item.matches, key=lambda item: item.sequence)


def get_round_by_bracket_meta(stage, kind: str, bracket_round: int) -> Round | None:
    return next(
        (
            round_item
            for round_item in ordered_stage_rounds(stage)
            if round_item.settings.get("bracket_kind") == kind
            and int(round_item.settings.get("bracket_round", 0)) == bracket_round
        ),
        None,
    )


def get_round_by_page_playoff_kind(stage, kind: str) -> Round | None:
    return next(
        (
            round_item
            for round_item in ordered_stage_rounds(stage)
            if round_item.settings.get("page_round_kind") == kind
        ),
        None,
    )


def get_match_by_page_playoff_kind(round_item: Round, kind: str) -> Match | None:
    return next(
        (
            match
            for match in ordered_matches(round_item)
            if match.settings.get("page_match_kind") == kind
        ),
        None,
    )


def match_winner(match: Match) -> Participant:
    winner = next(
        (result.participant for result in match.results if result.rank == 1), None
    )
    if not winner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine winner for a completed bracket match",
        )
    return winner


def match_loser(match: Match) -> Participant | None:
    ordered_results = sorted(match.results, key=lambda item: item.rank)
    if len(ordered_results) < 2:
        return None
    return ordered_results[-1].participant


def pair_head_to_head(participants: list[Participant]) -> list[list[Participant]]:
    if len(participants) % 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bracket generation requires an even number of advancing participants",
        )
    return [participants[index : index + 2] for index in range(0, len(participants), 2)]


def round_robin_total_rounds(stage) -> int:
    configured = int(stage.settings.get("round_robin_total_rounds", 0) or 0)
    if configured:
        return configured

    participant_count = len(stage.tournament.participants)
    if participant_count <= 1:
        return 0
    return participant_count - 1 if participant_count % 2 == 0 else participant_count


def swiss_total_rounds(stage) -> int:
    configured = int(stage.settings.get("swiss_total_rounds", 0) or 0)
    if configured:
        return configured

    participant_count = len(stage.tournament.participants)
    if participant_count <= 1:
        return 0
    return (participant_count - 1).bit_length()


def leaderboard_series_total_rounds(stage) -> int:
    configured = int(stage.settings.get("round_count", 0) or 0)
    return configured or 1


def resolve_seeded_groups(stage) -> list[list[Participant]]:
    participants = sorted(
        stage.tournament.participants,
        key=lambda item: (item.seed_number or 9999, item.display_name.lower()),
    )
    match_size = max(2, int(stage.settings.get("match_size", 5) or 5))
    return [
        participants[index : index + match_size]
        for index in range(0, len(participants), match_size)
    ]


def resolve_round_robin_groups(stage, round_number: int) -> list[list[Participant]]:
    if round_number < 1:
        return []

    participants = sorted(
        stage.tournament.participants,
        key=lambda item: (item.seed_number or 9999, item.display_name.lower()),
    )
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


def swiss_pair_history(stage) -> tuple[set[frozenset[str]], set[str]]:
    previous_pairs: set[frozenset[str]] = set()
    bye_recipient_ids: set[str] = set()

    for round_item in ordered_stage_rounds(stage):
        for match in ordered_matches(round_item):
            participant_ids = [slot.participant_id for slot in match.participants]
            if len(participant_ids) == 1:
                bye_recipient_ids.add(participant_ids[0])
                continue
            if len(participant_ids) == 2:
                previous_pairs.add(frozenset(participant_ids))

    return previous_pairs, bye_recipient_ids


def choose_swiss_bye(
    ordered_participants: list[Participant], bye_recipient_ids: set[str]
) -> Participant:
    for participant in reversed(ordered_participants):
        if participant.id not in bye_recipient_ids:
            return participant
    return ordered_participants[-1]


def pair_swiss_participants(
    ordered_participants: list[Participant],
    previous_pairs: set[frozenset[str]],
    allow_repeats: bool = False,
) -> list[list[Participant]] | None:
    if not ordered_participants:
        return []

    first = ordered_participants[0]
    for index in range(1, len(ordered_participants)):
        opponent = ordered_participants[index]
        pair_key = frozenset({first.id, opponent.id})
        if not allow_repeats and pair_key in previous_pairs:
            continue

        remaining = ordered_participants[1:index] + ordered_participants[index + 1 :]
        tail = pair_swiss_participants(remaining, previous_pairs, allow_repeats)
        if tail is not None:
            return [[first, opponent], *tail]

    return None


def resolve_swiss_groups(stage) -> list[list[Participant]]:
    from app.services.standings_service import calculate_points_leaderboard

    leaderboard = calculate_points_leaderboard(stage.tournament)
    participant_lookup = {
        participant.id: participant for participant in stage.tournament.participants
    }
    ordered_participants = [
        participant_lookup[entry["participant_id"]]
        for entry in leaderboard
        if entry["participant_id"] in participant_lookup
    ]
    previous_pairs, bye_recipient_ids = swiss_pair_history(stage)
    bye_group: list[list[Participant]] = []

    if len(ordered_participants) % 2 == 1:
        bye_participant = choose_swiss_bye(ordered_participants, bye_recipient_ids)
        ordered_participants = [
            participant
            for participant in ordered_participants
            if participant.id != bye_participant.id
        ]
        bye_group = [[bye_participant]]

    groups = pair_swiss_participants(ordered_participants, previous_pairs)
    if groups is None:
        groups = pair_swiss_participants(
            ordered_participants, previous_pairs, allow_repeats=True
        )
    if groups is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create Swiss pairings for the next round",
        )

    return groups + bye_group


def double_elimination_sequence(field_size: int) -> list[tuple[str, int]]:
    total_winners_rounds = field_size.bit_length() - 1
    sequence: list[tuple[str, int]] = [(DOUBLE_ELIMINATION_WINNERS, 1)]
    for winners_round in range(2, total_winners_rounds + 1):
        if winners_round == 2:
            sequence.append((DOUBLE_ELIMINATION_LOSERS, 1))
        else:
            sequence.append((DOUBLE_ELIMINATION_LOSERS, 2 * winners_round - 4))
            sequence.append((DOUBLE_ELIMINATION_LOSERS, 2 * winners_round - 3))
        sequence.append((DOUBLE_ELIMINATION_WINNERS, winners_round))
    sequence.append((DOUBLE_ELIMINATION_LOSERS, 2 * total_winners_rounds - 2))
    sequence.append((DOUBLE_ELIMINATION_GRAND_FINAL, 1))
    return sequence


def resolve_double_elimination_groups(
    stage, kind: str, bracket_round: int, field_size: int
) -> list[list[Participant]]:
    total_winners_rounds = field_size.bit_length() - 1

    if kind == DOUBLE_ELIMINATION_WINNERS:
        previous_round = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_WINNERS, bracket_round - 1
        )
        if not previous_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Previous winners bracket round is missing",
            )
        return pair_head_to_head(
            [match_winner(match) for match in ordered_matches(previous_round)]
        )

    if kind == DOUBLE_ELIMINATION_LOSERS and bracket_round == 1:
        first_winners_round = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_WINNERS, 1
        )
        if not first_winners_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Opening winners bracket round is missing",
            )
        losers = [
            loser
            for loser in (
                match_loser(match) for match in ordered_matches(first_winners_round)
            )
            if loser is not None
        ]
        return pair_head_to_head(losers)

    if kind == DOUBLE_ELIMINATION_LOSERS and bracket_round % 2 == 0:
        previous_losers_round = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_LOSERS, bracket_round - 1
        )
        source_winners_round = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_WINNERS, bracket_round // 2 + 1
        )
        if not previous_losers_round or not source_winners_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Required source rounds for the losers bracket are missing",
            )
        lower_bracket_winners = [
            match_winner(match) for match in ordered_matches(previous_losers_round)
        ]
        fresh_losers = [
            loser
            for loser in (
                match_loser(match) for match in ordered_matches(source_winners_round)
            )
            if loser is not None
        ]
        if len(lower_bracket_winners) != len(fresh_losers):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Losers bracket sources do not line up for the next round",
            )
        return [
            [lower_bracket_winners[index], fresh_losers[index]]
            for index in range(len(fresh_losers))
        ]

    if kind == DOUBLE_ELIMINATION_LOSERS:
        previous_losers_round = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_LOSERS, bracket_round - 1
        )
        if not previous_losers_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Previous losers bracket round is missing",
            )
        return pair_head_to_head(
            [match_winner(match) for match in ordered_matches(previous_losers_round)]
        )

    if kind == DOUBLE_ELIMINATION_GRAND_FINAL:
        winners_final = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_WINNERS, total_winners_rounds
        )
        losers_final = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_LOSERS, 2 * total_winners_rounds - 2
        )
        if not winners_final or not losers_final:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bracket finals are not ready yet",
            )
        return [
            [
                match_winner(ordered_matches(winners_final)[0]),
                match_winner(ordered_matches(losers_final)[0]),
            ]
        ]

    if kind == DOUBLE_ELIMINATION_GRAND_FINAL_RESET:
        first_final = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_GRAND_FINAL, 1
        )
        if not first_final:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Grand final is not ready for a reset match",
            )
        final_match = ordered_matches(first_final)[0]
        return [
            [
                slot.participant
                for slot in sorted(
                    final_match.participants, key=lambda item: item.slot_number
                )
            ]
        ]

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported double-elimination round type",
    )


def double_elimination_needs_reset(stage) -> bool:
    grand_final = get_round_by_bracket_meta(stage, DOUBLE_ELIMINATION_GRAND_FINAL, 1)
    if not grand_final or any(
        match.status != MatchStatus.COMPLETED.value for match in grand_final.matches
    ):
        return False
    final_match = ordered_matches(grand_final)[0]
    participants = sorted(final_match.participants, key=lambda item: item.slot_number)
    if len(participants) != 2:
        return False
    return match_winner(final_match).id == participants[1].participant_id


def next_double_elimination_round_spec(stage) -> dict | None:
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        return None

    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return None

    field_size = int(stage.settings.get("field_size", 0))
    sequence = double_elimination_sequence(field_size)
    if len(rounds) < len(sequence):
        kind, bracket_round = sequence[len(rounds)]
        groups = resolve_double_elimination_groups(
            stage, kind, bracket_round, field_size
        )
        return {
            "kind": kind,
            "bracket_round": bracket_round,
            "name": double_elimination_round_name(kind, bracket_round, field_size),
            "groups": groups,
            "is_final": kind == DOUBLE_ELIMINATION_GRAND_FINAL,
        }

    if (
        latest.settings.get("bracket_kind") == DOUBLE_ELIMINATION_GRAND_FINAL
        and not get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_GRAND_FINAL_RESET, 2
        )
        and double_elimination_needs_reset(stage)
    ):
        return {
            "kind": DOUBLE_ELIMINATION_GRAND_FINAL_RESET,
            "bracket_round": 2,
            "name": double_elimination_round_name(
                DOUBLE_ELIMINATION_GRAND_FINAL_RESET, 2, field_size
            ),
            "groups": resolve_double_elimination_groups(
                stage, DOUBLE_ELIMINATION_GRAND_FINAL_RESET, 2, field_size
            ),
            "is_final": True,
        }

    return None


def can_generate_double_elimination_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    return next_double_elimination_round_spec(stage) is not None


def create_double_elimination_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    latest = rounds[-1]
    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    spec = next_double_elimination_round_spec(stage)
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No double-elimination round is ready to generate",
        )

    if spec["kind"] == DOUBLE_ELIMINATION_GRAND_FINAL_RESET:
        previous_final = get_round_by_bracket_meta(
            stage, DOUBLE_ELIMINATION_GRAND_FINAL, 1
        )
        if previous_final:
            previous_final.is_final = False
            db.add(previous_final)

    next_number = len(rounds) + 1
    next_round = Round(
        stage=stage,
        name=spec["name"],
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=spec["is_final"],
        settings={
            "generated_from_round": latest.number,
            "bracket_kind": spec["kind"],
            "bracket_round": spec["bracket_round"],
        },
    )
    db.add(next_round)

    for match_index, group in enumerate(spec["groups"], start=1):
        match = Match(
            round=next_round,
            name=double_elimination_match_name(
                spec["name"], match_index, len(spec["groups"])
            ),
            sequence=match_index,
            status=MatchStatus.SCHEDULED.value,
            settings={"group_size": len(group)},
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

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round


def sort_results_for_advancement(
    round_item: Round, results: list[MatchResult], top_n: int
) -> list[MatchResult]:
    score_direction = round_item.stage.settings.get("score_direction")
    ranked = sorted(
        results,
        key=lambda item: (
            item.rank,
            score_sort_value(item.score, score_direction),
            item.participant.display_name.lower(),
        ),
    )
    if len(ranked) <= top_n:
        return ranked
    cutoff_rank = ranked[top_n - 1].rank
    boundary_group = [result for result in ranked if result.rank == cutoff_rank]
    if len(boundary_group) == 1:
        return ranked
    scores = [result.score for result in boundary_group]
    if any(score is None for score in scores) or len(
        {score for score in scores}
    ) != len(boundary_group):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tie on the advancement boundary requires manual resolution or distinct scores",
        )
    return sorted(
        ranked,
        key=lambda item: (
            item.rank,
            score_sort_value(item.score, score_direction),
            item.participant.display_name.lower(),
        ),
    )


def get_advancing_participants(round_item: Round) -> list[Participant]:
    rule = get_round_rule(round_item)
    if not rule:
        return []
    top_n = int(rule.config.get("top_n", 0))
    advancing: list[Participant] = []

    if rule.kind == AdvancementKind.MATCH_TOP_N.value:
        for match in sorted(round_item.matches, key=lambda item: item.sequence):
            ordered_results = sort_results_for_advancement(
                round_item, list(match.results), top_n
            )
            advancing.extend(result.participant for result in ordered_results[:top_n])
        return advancing

    if rule.kind == AdvancementKind.STANDINGS_TOP_N.value:
        from app.services.standings_service import calculate_leaderboard

        leaderboard = calculate_leaderboard(round_item.stage.tournament)
        advancing_ids = [entry["participant_id"] for entry in leaderboard[:top_n]]
        lookup = {
            participant.id: participant
            for participant in round_item.stage.tournament.participants
        }
        return [
            lookup[participant_id]
            for participant_id in advancing_ids
            if participant_id in lookup
        ]

    return advancing


def can_generate_round_robin_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        return False

    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return False

    return latest.number < round_robin_total_rounds(stage)


def create_round_robin_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament has no rounds"
        )

    latest = rounds[-1]
    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish the current round first",
        )

    total_rounds = round_robin_total_rounds(stage)
    if latest.number >= total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is already at the final round",
        )

    next_number = latest.number + 1
    if any(round_item.number == next_number for round_item in rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Next round already exists"
        )

    groups = resolve_round_robin_groups(stage, next_number)
    next_round = Round(
        stage=stage,
        name=f"Round {next_number}",
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=next_number == total_rounds,
        settings={"generated_from_round": latest.number},
    )
    db.add(next_round)

    for match_index, group in enumerate(groups, start=1):
        match_name = (
            f"Match {chr(64 + match_index)}" if len(groups) > 1 else next_round.name
        )
        match = Match(
            round=next_round,
            name=match_name,
            sequence=match_index,
            status=MatchStatus.SCHEDULED.value,
            settings={"group_size": len(group)},
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

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round


def can_generate_leaderboard_series_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        return False

    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return False

    return latest.number < leaderboard_series_total_rounds(stage)


def create_leaderboard_series_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament has no rounds"
        )

    latest = rounds[-1]
    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish the current round first",
        )

    total_rounds = leaderboard_series_total_rounds(stage)
    if latest.number >= total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is already at the final round",
        )

    next_number = latest.number + 1
    if any(round_item.number == next_number for round_item in rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Next round already exists",
        )

    groups = resolve_seeded_groups(stage)
    next_round = Round(
        stage=stage,
        name=f"Round {next_number}",
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=next_number == total_rounds,
        settings={"generated_from_round": latest.number},
    )
    db.add(next_round)

    for match_index, group in enumerate(groups, start=1):
        match_name = (
            f"Match {chr(64 + match_index)}" if len(groups) > 1 else next_round.name
        )
        match = Match(
            round=next_round,
            name=match_name,
            sequence=match_index,
            status=MatchStatus.SCHEDULED.value,
            settings={"group_size": len(group)},
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

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round


def can_generate_swiss_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        return False

    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return False

    return latest.number < swiss_total_rounds(stage)


def create_swiss_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament has no rounds"
        )

    latest = rounds[-1]
    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish the current round first",
        )

    total_rounds = swiss_total_rounds(stage)
    if latest.number >= total_rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is already at the final round",
        )

    next_number = latest.number + 1
    if any(round_item.number == next_number for round_item in rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Next round already exists"
        )

    groups = resolve_swiss_groups(stage)
    next_round = Round(
        stage=stage,
        name=f"Round {next_number}",
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=next_number == total_rounds,
        settings={"generated_from_round": latest.number},
    )
    db.add(next_round)

    points_for_win = (
        int(stage.points_scheme.placements.get("1", 0)) if stage.points_scheme else 0
    )

    for match_index, group in enumerate(groups, start=1):
        match_name = (
            f"Match {chr(64 + match_index)}" if len(groups) > 1 else next_round.name
        )
        is_bye = len(group) == 1
        match = Match(
            round=next_round,
            name=match_name,
            sequence=match_index,
            status=MatchStatus.COMPLETED.value
            if is_bye
            else MatchStatus.SCHEDULED.value,
            settings={"group_size": len(group)},
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
        if is_bye:
            db.add(
                MatchResult(
                    match=match,
                    participant=group[0],
                    rank=1,
                    points_awarded=points_for_win,
                )
            )

    if all(len(group) == 1 for group in groups):
        next_round.status = RoundStatus.COMPLETED.value

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round


def can_generate_page_playoff_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        return False

    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return False

    return latest.settings.get("page_round_kind") in {
        PAGE_PLAYOFF_OPENING,
        PAGE_PLAYOFF_PRELIMINARY_FINAL,
    }


def create_page_playoff_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    rounds = ordered_stage_rounds(stage)
    if not rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament has no rounds"
        )

    latest = rounds[-1]
    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish the current round first",
        )

    next_number = latest.number + 1
    if any(round_item.number == next_number for round_item in rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Next round already exists"
        )

    latest_kind = latest.settings.get("page_round_kind")
    if latest_kind == PAGE_PLAYOFF_OPENING:
        qualifier_match = get_match_by_page_playoff_kind(latest, PAGE_PLAYOFF_QUALIFIER)
        eliminator_match = get_match_by_page_playoff_kind(
            latest, PAGE_PLAYOFF_ELIMINATOR
        )
        if not qualifier_match or not eliminator_match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Opening Page playoff matches are missing",
            )
        qualifier_loser = match_loser(qualifier_match)
        eliminator_winner = match_winner(eliminator_match)
        if qualifier_loser is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Qualifier loser is required for the preliminary final",
            )
        next_round_kind = PAGE_PLAYOFF_PRELIMINARY_FINAL
        next_round_name = "Preliminary Final"
        next_groups = [[qualifier_loser, eliminator_winner]]
        next_match_kind = PAGE_PLAYOFF_PRELIMINARY_FINAL
        is_final = False
    elif latest_kind == PAGE_PLAYOFF_PRELIMINARY_FINAL:
        opening_round = get_round_by_page_playoff_kind(stage, PAGE_PLAYOFF_OPENING)
        qualifier_match = (
            get_match_by_page_playoff_kind(opening_round, PAGE_PLAYOFF_QUALIFIER)
            if opening_round
            else None
        )
        preliminary_match = get_match_by_page_playoff_kind(
            latest, PAGE_PLAYOFF_PRELIMINARY_FINAL
        ) or (ordered_matches(latest)[0] if ordered_matches(latest) else None)
        if not qualifier_match or not preliminary_match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Required Page playoff source matches are missing",
            )
        next_round_kind = PAGE_PLAYOFF_GRAND_FINAL
        next_round_name = "Grand Final"
        next_groups = [
            [
                match_winner(qualifier_match),
                match_winner(preliminary_match),
            ]
        ]
        next_match_kind = PAGE_PLAYOFF_GRAND_FINAL
        is_final = True
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is already at the final round",
        )

    next_round = Round(
        stage=stage,
        name=next_round_name,
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=is_final,
        settings={
            "generated_from_round": latest.number,
            "page_round_kind": next_round_kind,
        },
    )
    db.add(next_round)

    for match_index, group in enumerate(next_groups, start=1):
        match = Match(
            round=next_round,
            name=next_round_name,
            sequence=match_index,
            status=MatchStatus.SCHEDULED.value,
            settings={
                "group_size": len(group),
                "page_match_kind": next_match_kind,
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

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round


def special_round_handler(stage):
    handlers = (
        (
            is_double_elimination_stage,
            can_generate_double_elimination_round,
            create_double_elimination_round,
        ),
        (
            is_leaderboard_series_stage,
            can_generate_leaderboard_series_round,
            create_leaderboard_series_round,
        ),
        (
            is_round_robin_stage,
            can_generate_round_robin_round,
            create_round_robin_round,
        ),
        (is_swiss_stage, can_generate_swiss_round, create_swiss_round),
        (
            is_page_playoff_stage,
            can_generate_page_playoff_round,
            create_page_playoff_round,
        ),
    )
    return next(
        (
            (can_generate, create_round)
            for predicate, can_generate, create_round in handlers
            if predicate(stage)
        ),
        None,
    )


def can_generate_next_round(tournament: Tournament) -> bool:
    stage = main_stage(tournament)
    handler = special_round_handler(stage)
    if handler:
        can_generate, _create_round = handler
        return can_generate(tournament)

    rounds = sorted(stage.rounds, key=lambda item: item.number)
    if not rounds:
        return False
    latest = rounds[-1]
    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        return False
    if latest.is_final:
        return False
    return get_round_rule(latest) is not None


def generate_next_round(db: Session, tournament: Tournament) -> Round:
    stage = main_stage(tournament)
    handler = special_round_handler(stage)
    if handler:
        _can_generate, create_round = handler
        return create_round(db, tournament)

    rounds = sorted(stage.rounds, key=lambda item: item.number)
    if not rounds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tournament has no rounds"
        )

    latest = rounds[-1]

    if latest.settings.get("generated_from_round") and not any(
        match.status == MatchStatus.COMPLETED.value or match.results
        for match in latest.matches
    ):
        return latest

    if any(match.status != MatchStatus.COMPLETED.value for match in latest.matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish the current round first",
        )
    if latest.is_final:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament is already at the final round",
        )
    if any(round_item.number == latest.number + 1 for round_item in rounds):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Next round already exists"
        )

    qualifiers = get_advancing_participants(latest)
    if len(qualifiers) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough qualified participants for another round",
        )

    match_size = get_stage_match_size(latest)
    groups = [
        qualifiers[index : index + match_size]
        for index in range(0, len(qualifiers), match_size)
    ]
    next_number = latest.number + 1
    is_final = len(groups) == 1 and len(qualifiers) <= match_size
    stage_format = latest.stage.settings.get("format")
    round_name = (
        bracket_round_name(len(qualifiers))
        if stage_format == TournamentFormat.BRACKET.value
        else ("Final" if is_final else f"Round {next_number}")
    )
    next_round = Round(
        stage=stage,
        name=round_name,
        number=next_number,
        order_index=next_number,
        status=RoundStatus.ACTIVE.value,
        is_final=is_final,
        settings={"generated_from_round": latest.number},
    )
    db.add(next_round)

    for match_index, group in enumerate(groups, start=1):
        match_name = (
            bracket_match_name(round_name, match_index, len(groups))
            if stage_format == TournamentFormat.BRACKET.value
            else (
                f"Match {chr(64 + match_index)}" if len(groups) > 1 else next_round.name
            )
        )
        match = Match(
            round=next_round,
            name=match_name,
            sequence=match_index,
            status=MatchStatus.SCHEDULED.value,
            settings={"group_size": len(group)},
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

    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(next_round)
    return next_round
