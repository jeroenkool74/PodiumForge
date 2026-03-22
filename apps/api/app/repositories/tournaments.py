from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Match, MatchParticipant, MatchResult, Round, Stage, Tournament


def tournament_load_options() -> tuple:
    return (
        selectinload(Tournament.participants),
        selectinload(Tournament.points_schemes),
        selectinload(Tournament.tie_break_rules),
        selectinload(Tournament.stages).selectinload(Stage.points_scheme),
        selectinload(Tournament.stages).selectinload(Stage.tie_break_rule),
        selectinload(Tournament.stages).selectinload(Stage.advancement_rules),
        selectinload(Tournament.stages)
        .selectinload(Stage.rounds)
        .selectinload(Round.matches)
        .selectinload(Match.participants)
        .selectinload(MatchParticipant.participant),
        selectinload(Tournament.stages)
        .selectinload(Stage.rounds)
        .selectinload(Round.matches)
        .selectinload(Match.results)
        .selectinload(MatchResult.participant),
    )


def list_public_tournaments(db: Session) -> list[Tournament]:
    statement = (
        select(Tournament)
        .options(*tournament_load_options())
        .where(Tournament.is_public.is_(True))
    )
    return list(
        db.scalars(statement.order_by(Tournament.created_at.desc())).unique().all()
    )


def get_tournament_by_identifier(
    db: Session, identifier: str, public_only: bool = False
) -> Tournament | None:
    statement = select(Tournament).options(*tournament_load_options())
    if public_only:
        statement = statement.where(Tournament.is_public.is_(True))
    if len(identifier) == 36 and identifier.count("-") == 4:
        statement = statement.where(Tournament.id == identifier)
    else:
        statement = statement.where(Tournament.slug == identifier)
    return db.scalar(statement)


def get_match_with_context(db: Session, match_id: str) -> Match | None:
    statement = (
        select(Match)
        .options(
            selectinload(Match.participants).selectinload(MatchParticipant.participant),
            selectinload(Match.results).selectinload(MatchResult.participant),
            selectinload(Match.round)
            .selectinload(Round.stage)
            .selectinload(Stage.tournament),
            selectinload(Match.round)
            .selectinload(Round.stage)
            .selectinload(Stage.points_scheme),
            selectinload(Match.round)
            .selectinload(Round.stage)
            .selectinload(Stage.advancement_rules),
            selectinload(Match.round)
            .selectinload(Round.stage)
            .selectinload(Stage.rounds)
            .selectinload(Round.matches),
        )
        .where(Match.id == match_id)
    )
    return db.scalar(statement)


def list_tournaments_for_management(db: Session) -> list[Tournament]:
    statement = (
        select(Tournament)
        .options(*tournament_load_options())
        .order_by(Tournament.created_at.desc())
    )
    return list(db.scalars(statement).unique().all())
