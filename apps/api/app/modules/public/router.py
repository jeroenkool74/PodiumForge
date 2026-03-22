from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.tournaments import (
    get_match_with_context,
    get_tournament_by_identifier,
    list_public_tournaments,
)
from app.schemas.tournament import (
    DashboardRead,
    MatchRead,
    PublicTeamsRead,
    RoundRead,
    StandingEntryRead,
    TournamentCardRead,
    TournamentDetailRead,
)
from app.services.standings_service import (
    calculate_standings,
    serialize_dashboard,
    serialize_match,
    serialize_tournament_card,
    serialize_tournament_detail,
)

router = APIRouter(prefix="/public", tags=["public"])


def _public_tournament(db: Session, identifier: str):
    tournament = get_tournament_by_identifier(db, identifier, public_only=True)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )
    return tournament


@router.get("/tournaments", response_model=list[TournamentCardRead])
def public_tournaments(db: Session = Depends(get_db)) -> list[TournamentCardRead]:
    return [
        TournamentCardRead(**serialize_tournament_card(item))
        for item in list_public_tournaments(db)
    ]


@router.get("/tournaments/{identifier}", response_model=TournamentDetailRead)
def public_tournament_detail(
    identifier: str, db: Session = Depends(get_db)
) -> TournamentDetailRead:
    return TournamentDetailRead(
        **serialize_tournament_detail(_public_tournament(db, identifier))
    )


@router.get(
    "/tournaments/{identifier}/standings", response_model=list[StandingEntryRead]
)
def public_standings(
    identifier: str, db: Session = Depends(get_db)
) -> list[StandingEntryRead]:
    return [
        StandingEntryRead(**entry)
        for entry in calculate_standings(_public_tournament(db, identifier))
    ]


@router.get("/tournaments/{identifier}/rounds/{round_id}", response_model=RoundRead)
def public_round(
    identifier: str, round_id: str, db: Session = Depends(get_db)
) -> RoundRead:
    tournament = _public_tournament(db, identifier)
    detail = serialize_tournament_detail(tournament)
    for stage in detail["stages"]:
        for round_item in stage["rounds"]:
            if round_item["id"] == round_id:
                return RoundRead(**round_item)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Round not found")


@router.get("/matches/{match_id}", response_model=MatchRead)
def public_match(match_id: str, db: Session = Depends(get_db)) -> MatchRead:
    match = get_match_with_context(db, match_id)
    if not match or not match.round.stage.tournament.is_public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return MatchRead(**serialize_match(match))


@router.get("/tournaments/{identifier}/dashboard", response_model=DashboardRead)
def public_dashboard(identifier: str, db: Session = Depends(get_db)) -> DashboardRead:
    return DashboardRead(**serialize_dashboard(_public_tournament(db, identifier)))


@router.get("/tournaments/{identifier}/teams", response_model=PublicTeamsRead)
def public_teams(identifier: str, db: Session = Depends(get_db)) -> PublicTeamsRead:
    tournament = _public_tournament(db, identifier)
    teams = [
        {
            "id": participant.id,
            "name": participant.display_name,
            "members": list(participant.metadata_json.get("members", [])),
        }
        for participant in sorted(
            tournament.participants,
            key=lambda item: (item.seed_number or 9999, item.display_name.lower()),
        )
        if participant.kind == "TEAM"
    ]
    return PublicTeamsRead(
        tournament_id=tournament.id,
        tournament_name=tournament.name,
        participant_type=tournament.participant_type,
        teams=teams,
    )
