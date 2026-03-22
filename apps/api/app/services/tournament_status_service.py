from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import MatchStatus, TournamentStatus
from app.models import Tournament
from app.repositories.tournaments import list_tournaments_for_management


def refresh_tournament_status(tournament: Tournament) -> str:
    rounds = [round_item for stage in tournament.stages for round_item in stage.rounds]
    matches = [match for round_item in rounds for match in round_item.matches]

    if not matches:
        tournament.status = TournamentStatus.DRAFT.value
    else:
        has_incomplete_match = any(
            match.status != MatchStatus.COMPLETED.value for match in matches
        )
        if has_incomplete_match:
            tournament.status = TournamentStatus.LIVE.value
        else:
            from app.services.progression_service import can_generate_next_round

            tournament.status = (
                TournamentStatus.LIVE.value
                if can_generate_next_round(tournament)
                else TournamentStatus.COMPLETED.value
            )

    return tournament.status


def repair_tournament_statuses(db: Session) -> None:
    tournaments = list_tournaments_for_management(db)
    for tournament in tournaments:
        refresh_tournament_status(tournament)
        db.add(tournament)
    db.commit()
