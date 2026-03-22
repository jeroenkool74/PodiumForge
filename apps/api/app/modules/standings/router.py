from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.enums import RoleName
from app.repositories.tournaments import get_tournament_by_identifier
from app.schemas.tournament import StandingEntryRead
from app.services.standings_service import calculate_standings

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("/tournaments/{tournament_id}", response_model=list[StandingEntryRead])
def review_standings(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> list[StandingEntryRead]:
    tournament = get_tournament_by_identifier(db, tournament_id, public_only=False)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )
    return [StandingEntryRead(**entry) for entry in calculate_standings(tournament)]
