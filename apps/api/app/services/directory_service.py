from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    PlayerDirectoryEntry,
    TeamDirectoryEntry,
    TeamDirectoryMember,
)
from app.schemas.directory import DirectoryPlayerRead, DirectoryTeamRead


def normalize_directory_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required"
        )
    return normalized


def serialize_directory_player(player: PlayerDirectoryEntry) -> DirectoryPlayerRead:
    return DirectoryPlayerRead(id=player.id, name=player.name)


def serialize_directory_team(team: TeamDirectoryEntry) -> DirectoryTeamRead:
    members = sorted(
        [member.player for member in team.members if member.player is not None],
        key=lambda item: item.name.lower(),
    )
    return DirectoryTeamRead(
        id=team.id,
        name=team.name,
        members=[serialize_directory_player(member) for member in members],
    )


def load_directory_player(db: Session, player_id: str) -> PlayerDirectoryEntry | None:
    return db.scalar(
        select(PlayerDirectoryEntry).where(PlayerDirectoryEntry.id == player_id)
    )


def load_directory_team(db: Session, team_id: str) -> TeamDirectoryEntry | None:
    return db.scalar(
        select(TeamDirectoryEntry)
        .options(
            selectinload(TeamDirectoryEntry.members).selectinload(
                TeamDirectoryMember.player
            )
        )
        .where(TeamDirectoryEntry.id == team_id)
    )


def list_directory_players(db: Session) -> list[PlayerDirectoryEntry]:
    return list(
        db.scalars(
            select(PlayerDirectoryEntry).order_by(func.lower(PlayerDirectoryEntry.name))
        ).all()
    )


def list_directory_teams(db: Session) -> list[TeamDirectoryEntry]:
    statement = (
        select(TeamDirectoryEntry)
        .options(
            selectinload(TeamDirectoryEntry.members).selectinload(
                TeamDirectoryMember.player
            )
        )
        .order_by(func.lower(TeamDirectoryEntry.name))
    )
    return list(db.scalars(statement).unique().all())


def ensure_unique_player_name(
    db: Session, name: str, *, exclude_player_id: str | None = None
) -> None:
    statement = select(PlayerDirectoryEntry).where(
        func.lower(PlayerDirectoryEntry.name) == name.lower()
    )
    if exclude_player_id is not None:
        statement = statement.where(PlayerDirectoryEntry.id != exclude_player_id)
    if db.scalar(statement):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player name already exists",
        )


def ensure_unique_team_name(
    db: Session, name: str, *, exclude_team_id: str | None = None
) -> None:
    statement = select(TeamDirectoryEntry).where(
        func.lower(TeamDirectoryEntry.name) == name.lower()
    )
    if exclude_team_id is not None:
        statement = statement.where(TeamDirectoryEntry.id != exclude_team_id)
    if db.scalar(statement):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name already exists",
        )


def load_directory_players_by_ids(
    db: Session, player_ids: list[str]
) -> list[PlayerDirectoryEntry]:
    unique_ids = list(dict.fromkeys(player_ids))
    if not unique_ids:
        return []
    players = list(
        db.scalars(
            select(PlayerDirectoryEntry).where(PlayerDirectoryEntry.id.in_(unique_ids))
        ).all()
    )
    by_id = {player.id: player for player in players}
    missing = [player_id for player_id in unique_ids if player_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown player ids: {', '.join(missing)}",
        )
    return [by_id[player_id] for player_id in unique_ids]


def load_directory_teams_by_ids(
    db: Session, team_ids: list[str]
) -> list[TeamDirectoryEntry]:
    unique_ids = list(dict.fromkeys(team_ids))
    if not unique_ids:
        return []
    statement = select(TeamDirectoryEntry).options(
        selectinload(TeamDirectoryEntry.members).selectinload(
            TeamDirectoryMember.player
        )
    )
    teams = list(
        db.scalars(statement.where(TeamDirectoryEntry.id.in_(unique_ids)))
        .unique()
        .all()
    )
    by_id = {team.id: team for team in teams}
    missing = [team_id for team_id in unique_ids if team_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown team ids: {', '.join(missing)}",
        )
    return [by_id[team_id] for team_id in unique_ids]


def find_directory_player_by_name(
    db: Session, name: str
) -> PlayerDirectoryEntry | None:
    normalized = name.strip().lower()
    if not normalized:
        return None
    return db.scalar(
        select(PlayerDirectoryEntry).where(
            func.lower(PlayerDirectoryEntry.name) == normalized
        )
    )


def find_directory_team_by_name(db: Session, name: str) -> TeamDirectoryEntry | None:
    normalized = name.strip().lower()
    if not normalized:
        return None
    statement = select(TeamDirectoryEntry).options(
        selectinload(TeamDirectoryEntry.members).selectinload(
            TeamDirectoryMember.player
        )
    )
    return db.scalar(statement.where(func.lower(TeamDirectoryEntry.name) == normalized))


def team_directory_member_names(team: TeamDirectoryEntry) -> list[str]:
    return [
        member.player.name
        for member in sorted(
            team.members,
            key=lambda item: item.player.name.lower() if item.player else "",
        )
        if member.player is not None
    ]
