from __future__ import annotations

from collections import defaultdict

from app.core.enums import (
    AdvancementKind,
    MatchStatus,
    StandingStatus,
    TournamentFormat,
    TournamentStatus,
)
from app.core.tournament_formats import uses_table_standings
from app.models import Match, MatchResult, Round, Tournament
from app.services.tie_break_service import (
    normalize_tie_break_rules,
    tie_break_rule_labels,
)


def sorted_rounds(tournament: Tournament) -> list[Round]:
    rounds = []
    for stage in sorted(tournament.stages, key=lambda item: item.order_index):
        rounds.extend(
            sorted(stage.rounds, key=lambda item: (item.number, item.order_index))
        )
    return rounds


def current_round(tournament: Tournament) -> Round | None:
    rounds = sorted_rounds(tournament)
    for round_item in rounds:
        if any(
            match.status != MatchStatus.COMPLETED.value for match in round_item.matches
        ):
            return round_item
    return rounds[-1] if rounds else None


def latest_completed_round(tournament: Tournament) -> Round | None:
    completed = [
        round_item
        for round_item in sorted_rounds(tournament)
        if round_item.matches
        and all(
            match.status == MatchStatus.COMPLETED.value for match in round_item.matches
        )
    ]
    return completed[-1] if completed else None


def participant_results(
    tournament: Tournament,
) -> dict[str, list[tuple[Round, Match, MatchResult]]]:
    results: dict[str, list[tuple[Round, Match, MatchResult]]] = defaultdict(list)
    for round_item in sorted_rounds(tournament):
        for match in round_item.matches:
            if match.status != MatchStatus.COMPLETED.value:
                continue
            for result in match.results:
                results[result.participant_id].append((round_item, match, result))
    return results


def completed_match_winner_id(match: Match) -> str | None:
    if match.status != MatchStatus.COMPLETED.value:
        return None
    winner = next(
        (result.participant_id for result in match.results if result.rank == 1), None
    )
    return winner


def completed_match_loser_id(match: Match) -> str | None:
    if match.status != MatchStatus.COMPLETED.value:
        return None
    ordered_results = sorted(match.results, key=lambda item: item.rank)
    if len(ordered_results) < 2:
        return None
    return ordered_results[-1].participant_id


def page_playoff_active_participant_ids(tournament: Tournament) -> set[str]:
    if tournament.status == TournamentStatus.COMPLETED.value:
        return set()

    rounds = sorted_rounds(tournament)
    if not rounds:
        return {participant.id for participant in tournament.participants}

    opening_round = rounds[0]
    qualifier_match = next(
        (
            match
            for match in opening_round.matches
            if match.settings.get("page_match_kind") == "QUALIFIER"
        ),
        None,
    )
    eliminator_match = next(
        (
            match
            for match in opening_round.matches
            if match.settings.get("page_match_kind") == "ELIMINATOR"
        ),
        None,
    )
    if not qualifier_match or not eliminator_match:
        return {participant.id for participant in tournament.participants}

    if any(
        match.status != MatchStatus.COMPLETED.value for match in opening_round.matches
    ):
        return {
            slot.participant_id
            for match in opening_round.matches
            for slot in match.participants
        }

    qualifier_winner = completed_match_winner_id(qualifier_match)
    qualifier_loser = completed_match_loser_id(qualifier_match)
    eliminator_winner = completed_match_winner_id(eliminator_match)

    if len(rounds) == 1:
        return {
            participant_id
            for participant_id in {
                qualifier_winner,
                qualifier_loser,
                eliminator_winner,
            }
            if participant_id is not None
        }

    preliminary_round = rounds[1]
    if any(
        match.status != MatchStatus.COMPLETED.value
        for match in preliminary_round.matches
    ):
        active = {
            slot.participant_id
            for match in preliminary_round.matches
            for slot in match.participants
        }
        if qualifier_winner is not None:
            active.add(qualifier_winner)
        return active

    preliminary_match = (
        preliminary_round.matches[0] if preliminary_round.matches else None
    )
    preliminary_winner = (
        completed_match_winner_id(preliminary_match) if preliminary_match else None
    )

    if len(rounds) == 2:
        return {
            participant_id
            for participant_id in {qualifier_winner, preliminary_winner}
            if participant_id is not None
        }

    grand_final_round = rounds[2]
    if any(
        match.status != MatchStatus.COMPLETED.value
        for match in grand_final_round.matches
    ):
        return {
            slot.participant_id
            for match in grand_final_round.matches
            for slot in match.participants
        }

    return set()


def active_participant_ids(tournament: Tournament) -> set[str]:
    if tournament.format == TournamentFormat.DOUBLE_ELIMINATION.value:
        if tournament.status == TournamentStatus.COMPLETED.value:
            return set()
        loss_counts: dict[str, int] = defaultdict(int)
        for result_rows in participant_results(tournament).values():
            for _round_item, _match, result in result_rows:
                if result.rank > 1:
                    loss_counts[result.participant_id] += 1
        return {
            participant.id
            for participant in tournament.participants
            if loss_counts.get(participant.id, 0) < 2
        }

    if tournament.format == TournamentFormat.PAGE_PLAYOFF.value:
        return page_playoff_active_participant_ids(tournament)

    if uses_table_standings(tournament.format):
        return (
            set()
            if tournament.status == TournamentStatus.COMPLETED.value
            else {participant.id for participant in tournament.participants}
        )

    round_item = current_round(tournament)
    if round_item and any(
        match.status != MatchStatus.COMPLETED.value for match in round_item.matches
    ):
        return {
            slot.participant_id
            for match in round_item.matches
            for slot in match.participants
        }
    if (
        round_item
        and round_item.is_final
        and all(
            match.status == MatchStatus.COMPLETED.value for match in round_item.matches
        )
    ):
        return set()

    latest_round = latest_completed_round(tournament)
    if not latest_round:
        return {participant.id for participant in tournament.participants}

    from app.services.progression_service import get_advancing_participants

    advancing = get_advancing_participants(latest_round)
    return {participant.id for participant in advancing}


def calculate_final_placements(tournament: Tournament) -> dict[str, int]:
    rounds = sorted_rounds(tournament)
    if not rounds:
        return {}

    if uses_table_standings(tournament.format):
        if tournament.status != TournamentStatus.COMPLETED.value:
            return {}
        leaderboard = calculate_points_leaderboard(tournament)
        return {
            entry["participant_id"]: index
            for index, entry in enumerate(leaderboard, start=1)
        }

    active_ids = active_participant_ids(tournament)
    completed_rounds = [
        round_item
        for round_item in rounds
        if all(
            match.status == MatchStatus.COMPLETED.value for match in round_item.matches
        )
    ]
    if not completed_rounds:
        return {}

    placement_map: dict[str, int] = {}
    deepest_results: dict[str, tuple[int, int, int, float | None, str]] = {}

    final_completed_round = next(
        (
            round_item
            for round_item in reversed(completed_rounds)
            if round_item.is_final
            and all(
                match.status == MatchStatus.COMPLETED.value
                for match in round_item.matches
            )
        ),
        None,
    )

    if final_completed_round:
        finalists = sorted(
            [
                result
                for match in final_completed_round.matches
                for result in match.results
            ],
            key=lambda item: (
                item.rank,
                -(item.score or 0),
                item.participant.display_name.lower(),
            ),
        )
        for result in finalists:
            placement_map[result.participant_id] = result.rank

    for round_item in completed_rounds:
        for match in round_item.matches:
            ordered = sorted(
                match.results,
                key=lambda item: (
                    item.rank,
                    -(item.score or 0),
                    item.participant.display_name.lower(),
                ),
            )
            for index, result in enumerate(ordered, start=1):
                existing = deepest_results.get(result.participant_id)
                candidate = (
                    round_item.number,
                    result.rank,
                    index,
                    result.score,
                    result.participant.display_name,
                )
                if not existing or candidate[0] >= existing[0]:
                    deepest_results[result.participant_id] = candidate

    reserved_slots = len(active_ids)
    start_placement = (
        (len(placement_map) + 1)
        if placement_map
        else (reserved_slots + 1 if active_ids else 1)
    )

    ordered_eliminated = sorted(
        [
            (participant_id, data)
            for participant_id, data in deepest_results.items()
            if participant_id not in placement_map and participant_id not in active_ids
        ],
        key=lambda item: (
            -item[1][0],
            item[1][1],
            item[1][2],
            -(item[1][3] or 0),
            item[1][4].lower(),
        ),
    )
    placement_cursor = start_placement
    for participant_id, _ in ordered_eliminated:
        placement_map[participant_id] = placement_cursor
        placement_cursor += 1

    if not active_ids and not placement_map and completed_rounds:
        standalone_results = sorted(
            [
                result
                for match in completed_rounds[-1].matches
                for result in match.results
            ],
            key=lambda item: (
                item.rank,
                -(item.score or 0),
                item.participant.display_name.lower(),
            ),
        )
        for index, result in enumerate(standalone_results, start=1):
            placement_map[result.participant_id] = index
    return placement_map


def summarize_standings_rows(tournament: Tournament) -> list[dict]:
    per_participant = participant_results(tournament)
    entries: list[dict] = []

    for participant in sorted(
        tournament.participants,
        key=lambda item: (item.seed_number or 9999, item.display_name.lower()),
    ):
        result_rows = per_participant.get(participant.id, [])
        ranks = [result.rank for _, _, result in result_rows]
        points = [result.points_awarded for _, _, result in result_rows]
        scores = [result.score or 0 for _, _, result in result_rows]
        latest_row = result_rows[-1] if result_rows else None
        entries.append(
            {
                "participant_id": participant.id,
                "display_name": participant.display_name,
                "total_points": sum(points),
                "score_total": round(sum(scores), 2),
                "matches_played": len(result_rows),
                "best_rank": min(ranks) if ranks else None,
                "average_rank": round(sum(ranks) / len(ranks), 2) if ranks else None,
                "latest_round_name": latest_row[0].name if latest_row else None,
                "latest_rank": latest_row[2].rank if latest_row else None,
            }
        )

    return entries


def _head_to_head_scores(
    tournament: Tournament, participant_ids: set[str]
) -> dict[str, int]:
    scores = {participant_id: 0 for participant_id in participant_ids}
    if len(participant_ids) < 2:
        return scores

    for round_item in sorted_rounds(tournament):
        for match in round_item.matches:
            if match.status != MatchStatus.COMPLETED.value:
                continue
            relevant = [
                result
                for result in sorted(match.results, key=lambda item: item.rank)
                if result.participant_id in participant_ids
            ]
            if len(relevant) < 2:
                continue
            for index, result in enumerate(relevant):
                scores[result.participant_id] += len(relevant) - index - 1
    return scores


def _tie_break_sort_values(
    item: dict, rule_types: list[str], head_to_head_scores: dict[str, int]
) -> tuple:
    values = []
    for rule_type in rule_types:
        if rule_type == "HEAD_TO_HEAD":
            values.append(-head_to_head_scores.get(item["participant_id"], 0))
        elif rule_type == "BEST_RANK":
            values.append(item["best_rank"] if item["best_rank"] is not None else 9999)
        elif rule_type == "POINTS_DIFFERENTIAL":
            values.append(-item.get("score_total", 0))
        elif rule_type == "MATCHES_PLAYED":
            values.append(-item["matches_played"])
        elif rule_type == "AVERAGE_RANK":
            values.append(
                item["average_rank"] if item["average_rank"] is not None else 9999
            )
        elif rule_type == "DISPLAY_NAME":
            values.append(item["display_name"].lower())
    values.append(item["display_name"].lower())
    return tuple(values)


def _sorted_with_tie_breaks(entries: list[dict], tournament: Tournament) -> list[dict]:
    normalized_rules = normalize_tie_break_rules(
        tournament.tie_break_rules[0].rules if tournament.tie_break_rules else None
    )
    rule_types = [rule["rule_type"] for rule in normalized_rules]

    grouped_by_points: dict[int, list[dict]] = defaultdict(list)
    for entry in entries:
        grouped_by_points[entry["total_points"]].append(entry)

    ordered_entries: list[dict] = []
    for total_points in sorted(grouped_by_points.keys(), reverse=True):
        tied_entries = grouped_by_points[total_points]
        head_to_head_scores = _head_to_head_scores(
            tournament, {entry["participant_id"] for entry in tied_entries}
        )
        ordered_entries.extend(
            sorted(
                tied_entries,
                key=lambda item: _tie_break_sort_values(
                    item, rule_types, head_to_head_scores
                ),
            )
        )

    return ordered_entries


def calculate_points_leaderboard(tournament: Tournament) -> list[dict]:
    entries = summarize_standings_rows(tournament)
    return _sorted_with_tie_breaks(entries, tournament)


def calculate_standings(tournament: Tournament) -> list[dict]:
    per_participant = participant_results(tournament)
    alive_ids = active_participant_ids(tournament)
    provisional_placements = calculate_final_placements(tournament)
    entries = summarize_standings_rows(tournament)

    for entry in entries:
        result_rows = per_participant.get(entry["participant_id"], [])
        status = StandingStatus.ACTIVE.value
        if tournament.status == TournamentStatus.COMPLETED.value:
            status = StandingStatus.FINALIZED.value
        elif uses_table_standings(tournament.format):
            status = StandingStatus.ACTIVE.value
        elif entry["participant_id"] in alive_ids:
            status = (
                StandingStatus.QUALIFIED.value
                if latest_completed_round(tournament)
                else StandingStatus.ACTIVE.value
            )
        elif result_rows:
            status = (
                StandingStatus.FINALIZED.value
                if tournament.status == TournamentStatus.COMPLETED.value
                else StandingStatus.ELIMINATED.value
            )
        entry["current_status"] = status
        entry["final_placement"] = provisional_placements.get(entry["participant_id"])

    ordered = _sorted_with_tie_breaks(entries, tournament)
    if alive_ids:
        alive_entries = [
            entry for entry in ordered if entry["participant_id"] in alive_ids
        ]
        eliminated_entries = [
            entry for entry in ordered if entry["participant_id"] not in alive_ids
        ]
        eliminated_entries.sort(
            key=lambda item: (
                item["final_placement"]
                if item["final_placement"] is not None
                else 9999,
                item["display_name"].lower(),
            )
        )
        return alive_entries + eliminated_entries

    ordered.sort(
        key=lambda item: (
            item["final_placement"] if item["final_placement"] is not None else 9999,
            item["display_name"].lower(),
        )
    )
    return ordered


def serialize_match(match: Match) -> dict:
    tournament = match.round.stage.tournament
    results_locked = tournament.status == TournamentStatus.COMPLETED.value or any(
        round_item.number > match.round.number
        for round_item in match.round.stage.rounds
    )
    result_lookup = {result.participant_id: result for result in match.results}
    entrants = []
    for slot in sorted(match.participants, key=lambda item: item.slot_number):
        result = result_lookup.get(slot.participant_id)
        entrants.append(
            {
                "participant_id": slot.participant_id,
                "display_name": slot.participant.display_name,
                "slot_number": slot.slot_number,
                "seed_number": slot.seed_number,
                "rank": result.rank if result else None,
                "points_awarded": result.points_awarded if result else None,
                "score": result.score if result else None,
                "tie_group": result.tie_group if result else None,
            }
        )
    return {
        "id": match.id,
        "name": match.name,
        "sequence": match.sequence,
        "status": match.status,
        "scheduled_at": match.scheduled_at,
        "notes": match.notes,
        "tournament_id": tournament.id,
        "tournament_name": tournament.name,
        "tournament_slug": tournament.slug,
        "round_id": match.round.id,
        "round_name": match.round.name,
        "is_bye": len(entrants) == 1,
        "results_locked": results_locked,
        "entrants": entrants,
    }


def serialize_tournament_card(tournament: Tournament) -> dict:
    round_item = current_round(tournament)
    stage = (
        sorted(tournament.stages, key=lambda item: item.order_index)[0]
        if tournament.stages
        else None
    )
    return {
        "id": tournament.id,
        "name": tournament.name,
        "slug": tournament.slug,
        "description": tournament.description,
        "format": tournament.format,
        "participant_type": tournament.participant_type,
        "status": tournament.status,
        "is_public": tournament.is_public,
        "participant_count": len(tournament.participants),
        "current_round_name": round_item.name if round_item else None,
        "match_size": stage.settings.get("match_size") if stage else None,
    }


def serialize_stage_points(stage) -> list[dict]:
    points_scheme = stage.points_scheme
    if not points_scheme and stage.tournament.points_schemes:
        points_scheme = stage.tournament.points_schemes[0]
    if not points_scheme:
        return []
    return [
        {"placement": int(placement), "points": int(points)}
        for placement, points in sorted(
            points_scheme.placements.items(), key=lambda item: int(item[0])
        )
    ]


def describe_advancement_rule(stage, advancement_rule) -> str | None:
    stage_format = stage.settings.get("format")
    if stage_format == TournamentFormat.ROUND_ROBIN.value:
        return "Each entrant plays every other entrant once, and the final table decides the champion."
    if stage_format == TournamentFormat.SWISS.value:
        return "Entrants play a fixed number of score-based pairings, and the final table decides the champion."
    if stage_format == TournamentFormat.PAGE_PLAYOFF.value:
        return "Seeds 1 and 2 meet in the qualifier, seeds 3 and 4 fight through the eliminator, and the qualifier winner waits in the grand final."

    if (
        not advancement_rule
        and stage_format == TournamentFormat.DOUBLE_ELIMINATION.value
    ):
        return "Players drop into the lower bracket after one loss and are eliminated after the second."

    if not advancement_rule:
        return None

    top_n = advancement_rule.config.get("top_n")
    if advancement_rule.kind == AdvancementKind.MATCH_TOP_N.value and top_n:
        if stage_format == TournamentFormat.BRACKET.value:
            return "Winners advance from each bracket match until a champion remains."
        return f"Top {top_n} from each match advance to the next round."
    if advancement_rule.kind == AdvancementKind.STANDINGS_TOP_N.value and top_n:
        return f"Top {top_n} overall on points advance after each round."
    return advancement_rule.kind


def serialize_tournament_detail(tournament: Tournament) -> dict:
    from app.services.progression_service import can_generate_next_round

    standings = calculate_standings(tournament)
    alive_ids = active_participant_ids(tournament)
    qualified_names = [
        participant.display_name
        for participant in tournament.participants
        if participant.id in alive_ids
    ]
    eliminated_names = [
        participant.display_name
        for participant in tournament.participants
        if participant.id not in alive_ids
        and any(
            entry["participant_id"] == participant.id and entry["matches_played"] > 0
            for entry in standings
        )
    ]
    stages = []
    for stage in sorted(tournament.stages, key=lambda item: item.order_index):
        rounds = []
        for round_item in sorted(stage.rounds, key=lambda item: item.number):
            rounds.append(
                {
                    "id": round_item.id,
                    "name": round_item.name,
                    "number": round_item.number,
                    "status": round_item.status,
                    "is_final": round_item.is_final,
                    "bracket_kind": round_item.settings.get("bracket_kind"),
                    "matches": [
                        serialize_match(match)
                        for match in sorted(
                            round_item.matches, key=lambda item: item.sequence
                        )
                    ],
                }
            )
        advancement_rule = (
            sorted(stage.advancement_rules, key=lambda item: item.apply_after_round)[0]
            if stage.advancement_rules
            else None
        )
        advancement_summary = describe_advancement_rule(stage, advancement_rule)
        stages.append(
            {
                "id": stage.id,
                "name": stage.name,
                "order_index": stage.order_index,
                "match_size": stage.settings.get("match_size"),
                "advancement_kind": advancement_rule.kind if advancement_rule else None,
                "advance_count": (
                    int(advancement_rule.config.get("top_n"))
                    if advancement_rule and advancement_rule.config.get("top_n")
                    else None
                ),
                "points_scheme": serialize_stage_points(stage),
                "tie_break_rules": tie_break_rule_labels(
                    stage.tie_break_rule.rules if stage.tie_break_rule else None
                ),
                "rounds": rounds,
                "advancement_summary": advancement_summary,
            }
        )
    return {
        "id": tournament.id,
        "name": tournament.name,
        "slug": tournament.slug,
        "description": tournament.description,
        "format": tournament.format,
        "participant_type": tournament.participant_type,
        "status": tournament.status,
        "is_public": tournament.is_public,
        "participants": [
            {
                "id": participant.id,
                "display_name": participant.display_name,
                "kind": participant.kind,
                "seed_number": participant.seed_number,
                "members": list(participant.metadata_json.get("members", [])),
            }
            for participant in sorted(
                tournament.participants,
                key=lambda item: (item.seed_number or 9999, item.display_name.lower()),
            )
        ],
        "stages": stages,
        "standings": standings,
        "qualified": sorted(qualified_names),
        "eliminated": sorted(eliminated_names),
        "can_generate_next_round": can_generate_next_round(tournament),
    }


def serialize_dashboard(tournament: Tournament) -> dict:
    detail = serialize_tournament_detail(tournament)
    standings = detail["standings"]
    rounds = detail["stages"][0]["rounds"] if detail["stages"] else []
    round_item = (
        None
        if tournament.status == TournamentStatus.COMPLETED.value
        else current_round(tournament)
    )
    upcoming_matches = []
    if round_item:
        upcoming_matches = [
            serialize_match(match)
            for match in sorted(round_item.matches, key=lambda item: item.sequence)
            if match.status != MatchStatus.COMPLETED.value
        ]
    podium = []
    if tournament.status == TournamentStatus.COMPLETED.value:
        podium = [entry for entry in standings if entry["final_placement"] in {1, 2, 3}]
    return {
        "tournament_name": tournament.name,
        "tournament_slug": tournament.slug,
        "tournament_format": tournament.format,
        "participant_type": tournament.participant_type,
        "participant_count": len(detail["participants"]),
        "tournament_status": tournament.status,
        "current_round_name": round_item.name if round_item else None,
        "rounds": rounds,
        "upcoming_matches": upcoming_matches,
        "standings": standings[:8],
        "qualified": detail["qualified"],
        "eliminated": detail["eliminated"],
        "podium": podium,
        "auto_refresh_seconds": 10,
    }
