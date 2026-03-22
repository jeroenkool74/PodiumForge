from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.enums import RoleName
from app.repositories.tournaments import get_match_with_context
from app.schemas.match import MatchResultsUpsertRequest, MatchScheduleUpdateRequest
from app.schemas.tournament import MatchRead
from app.services.match_service import clear_match_results, upsert_match_results
from app.services.standings_service import serialize_match

router = APIRouter(prefix="/matches", tags=["matches"])


def _load_match(db: Session, match_id: str):
    match = get_match_with_context(db, match_id)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return match


@router.get("/{match_id}", response_model=MatchRead)
def get_match_endpoint(
    match_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> MatchRead:
    return MatchRead(**serialize_match(_load_match(db, match_id)))


@router.post("/{match_id}/results", response_model=MatchRead)
def save_match_results(
    match_id: str,
    payload: MatchResultsUpsertRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> MatchRead:
    match = _load_match(db, match_id)
    upsert_match_results(db, match, payload)
    refreshed = _load_match(db, match_id)
    return MatchRead(**serialize_match(refreshed))


@router.delete("/{match_id}/results", response_model=MatchRead)
def clear_match_results_endpoint(
    match_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> MatchRead:
    match = _load_match(db, match_id)
    clear_match_results(db, match)
    return MatchRead(**serialize_match(_load_match(db, match_id)))


@router.patch("/{match_id}/schedule", response_model=MatchRead)
def update_match_schedule_endpoint(
    match_id: str,
    payload: MatchScheduleUpdateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> MatchRead:
    match = _load_match(db, match_id)
    if payload.scheduled_at:
        try:
            match.scheduled_at = datetime.fromisoformat(
                payload.scheduled_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ISO 8601 date/time",
            ) from exc
    else:
        match.scheduled_at = None
    db.add(match)
    db.commit()
    db.refresh(match)
    return MatchRead(**serialize_match(match))
