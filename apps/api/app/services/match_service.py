from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import MatchStatus, RoundStatus
from app.core.tournament_formats import uses_fixed_head_to_head_matches
from app.models import Match, MatchResult
from app.schemas.match import MatchResultsUpsertRequest
from app.services.tournament_status_service import refresh_tournament_status


def points_for_rank(match: Match, rank: int) -> int:
    points_scheme = match.round.stage.points_scheme
    if not points_scheme and match.round.stage.tournament.points_schemes:
        points_scheme = match.round.stage.tournament.points_schemes[0]
    if not points_scheme:
        return 0
    return int(points_scheme.placements.get(str(rank), 0))


def _validate_boundary_ties(match: Match, payload: MatchResultsUpsertRequest) -> None:
    from app.services.progression_service import get_round_rule

    rule = get_round_rule(match.round)
    if not rule or rule.kind != "MATCH_TOP_N":
        return
    top_n = int(rule.config.get("top_n", 0))
    ordered = sorted(
        payload.results,
        key=lambda item: (item.rank, -(item.score or 0), item.participant_id),
    )
    if len(ordered) <= top_n or top_n <= 0:
        return
    cutoff_rank = ordered[top_n - 1].rank
    boundary = [result for result in ordered if result.rank == cutoff_rank]
    if len(boundary) <= 1:
        return
    scores = [result.score for result in boundary]
    if any(score is None for score in scores) or len(
        {score for score in scores}
    ) != len(boundary):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tie at the qualification line requires manual resolution or distinct scores",
        )


def _validate_result_shape(payload: MatchResultsUpsertRequest) -> None:
    grouped_by_rank: dict[int, list] = {}
    tie_groups_seen: set[int] = set()

    for result in payload.results:
        grouped_by_rank.setdefault(result.rank, []).append(result)

    expected_rank = 1
    for rank in sorted(grouped_by_rank):
        group = grouped_by_rank[rank]
        if rank != expected_rank:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finishing places must stay contiguous; reuse the same place number only for ties",
            )

        tie_groups = {item.tie_group for item in group if item.tie_group is not None}
        if len(group) == 1:
            if tie_groups:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tie group should be blank unless multiple entrants share the same place",
                )
        else:
            tie_group_values = [item.tie_group for item in group]
            if (
                len(tie_groups) != 1
                or any(value is None for value in tie_group_values)
                or len(set(tie_group_values)) != 1
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entrants tied on the same place must share one tie group",
                )
            tie_group = next(iter(tie_groups))
            if tie_group in tie_groups_seen:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each tie group can only be used for one tied place",
                )
            tie_groups_seen.add(tie_group)

        expected_rank += len(group)


def _validate_head_to_head_bracket_results(
    match: Match, payload: MatchResultsUpsertRequest
) -> None:
    stage_format = match.round.stage.settings.get("format")
    if not uses_fixed_head_to_head_matches(stage_format):
        return
    if len(match.participants) != 2:
        return
    if len({result.rank for result in payload.results}) != len(payload.results) or any(
        result.tie_group is not None for result in payload.results
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Head-to-head scheduled matches require a decisive winner",
        )


def _ensure_results_are_editable(match: Match) -> None:
    if any(
        round_item.number > match.round.number
        for round_item in match.round.stage.rounds
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This match is locked because a later round already exists",
        )


def upsert_match_results(
    db: Session, match: Match, payload: MatchResultsUpsertRequest
) -> Match:
    if len(match.participants) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automatic bye matches do not accept manual result entry",
        )

    _ensure_results_are_editable(match)

    expected_ids = {slot.participant_id for slot in match.participants}
    submitted_ids = [result.participant_id for result in payload.results]
    if set(submitted_ids) != expected_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Results must include every participant in the match",
        )
    if len(set(submitted_ids)) != len(submitted_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate participant result submitted",
        )

    _validate_result_shape(payload)
    _validate_head_to_head_bracket_results(match, payload)
    _validate_boundary_ties(match, payload)

    match.results.clear()
    for result in payload.results:
        match.results.append(
            MatchResult(
                participant_id=result.participant_id,
                rank=result.rank,
                points_awarded=points_for_rank(match, result.rank),
                score=result.score,
                tie_group=result.tie_group,
                notes=result.notes,
            )
        )

    match.status = MatchStatus.COMPLETED.value
    if all(
        item.status == MatchStatus.COMPLETED.value or item is match
        for item in match.round.matches
    ):
        match.round.status = RoundStatus.COMPLETED.value
    else:
        match.round.status = RoundStatus.ACTIVE.value

    tournament = match.round.stage.tournament
    db.add(match)
    db.flush()
    refresh_tournament_status(tournament)

    db.commit()
    db.refresh(match)
    return match


def clear_match_results(db: Session, match: Match) -> Match:
    if len(match.participants) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automatic bye matches do not store manual results",
        )

    _ensure_results_are_editable(match)
    match.results.clear()
    match.status = MatchStatus.SCHEDULED.value
    if any(item.results for item in match.round.matches):
        match.round.status = RoundStatus.ACTIVE.value
    else:
        match.round.status = RoundStatus.SCHEDULED.value

    tournament = match.round.stage.tournament
    db.add(match)
    db.flush()
    refresh_tournament_status(tournament)
    db.commit()
    db.refresh(match)
    return match
