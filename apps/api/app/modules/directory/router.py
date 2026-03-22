from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.enums import RoleName
from app.models import PlayerDirectoryEntry, TeamDirectoryEntry, TeamDirectoryMember
from app.schemas.directory import (
    DirectoryPlayerCreateRequest,
    DirectoryPlayerRead,
    DirectoryPlayerUpdateRequest,
    DirectoryTeamCreateRequest,
    DirectoryTeamRead,
    DirectoryTeamUpdateRequest,
)
from app.services.directory_service import (
    ensure_unique_player_name,
    ensure_unique_team_name,
    list_directory_players,
    list_directory_teams,
    load_directory_player,
    load_directory_players_by_ids,
    load_directory_team,
    normalize_directory_name,
    serialize_directory_player,
    serialize_directory_team,
)

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("/players", response_model=list[DirectoryPlayerRead])
def list_players_endpoint(
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> list[DirectoryPlayerRead]:
    return [serialize_directory_player(player) for player in list_directory_players(db)]


@router.post(
    "/players",
    response_model=DirectoryPlayerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_player_endpoint(
    payload: DirectoryPlayerCreateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> DirectoryPlayerRead:
    name = normalize_directory_name(payload.name)
    ensure_unique_player_name(db, name)
    player = PlayerDirectoryEntry(name=name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return serialize_directory_player(player)


@router.put("/players/{player_id}", response_model=DirectoryPlayerRead)
def update_player_endpoint(
    player_id: str,
    payload: DirectoryPlayerUpdateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> DirectoryPlayerRead:
    player = load_directory_player(db, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )
    name = normalize_directory_name(payload.name)
    ensure_unique_player_name(db, name, exclude_player_id=player_id)
    player.name = name
    db.add(player)
    db.commit()
    db.refresh(player)
    return serialize_directory_player(player)


@router.delete("/players/{player_id}")
def delete_player_endpoint(
    player_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> dict:
    player = load_directory_player(db, player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Player not found"
        )
    db.query(TeamDirectoryMember).filter(
        TeamDirectoryMember.player_id == player_id
    ).delete()
    db.delete(player)
    db.commit()
    return {"deleted": True, "player_id": player_id}


@router.get("/teams", response_model=list[DirectoryTeamRead])
def list_teams_endpoint(
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> list[DirectoryTeamRead]:
    return [serialize_directory_team(team) for team in list_directory_teams(db)]


@router.post(
    "/teams",
    response_model=DirectoryTeamRead,
    status_code=status.HTTP_201_CREATED,
)
def create_team_endpoint(
    payload: DirectoryTeamCreateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> DirectoryTeamRead:
    name = normalize_directory_name(payload.name)
    ensure_unique_team_name(db, name)
    players = load_directory_players_by_ids(db, payload.player_ids)
    team = TeamDirectoryEntry(name=name)
    db.add(team)
    db.flush()
    for player in players:
        db.add(TeamDirectoryMember(team_id=team.id, player_id=player.id))
    db.commit()
    loaded = load_directory_team(db, team.id)
    if not loaded:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load created team",
        )
    return serialize_directory_team(loaded)


@router.put("/teams/{team_id}", response_model=DirectoryTeamRead)
def update_team_endpoint(
    team_id: str,
    payload: DirectoryTeamUpdateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> DirectoryTeamRead:
    team = load_directory_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    name = normalize_directory_name(payload.name)
    ensure_unique_team_name(db, name, exclude_team_id=team_id)
    team.name = name
    players = load_directory_players_by_ids(db, payload.player_ids)
    db.query(TeamDirectoryMember).filter(
        TeamDirectoryMember.team_id == team_id
    ).delete()
    db.flush()
    for player in players:
        db.add(TeamDirectoryMember(team_id=team_id, player_id=player.id))
    db.add(team)
    db.commit()
    loaded = load_directory_team(db, team_id)
    if not loaded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return serialize_directory_team(loaded)


@router.delete("/teams/{team_id}")
def delete_team_endpoint(
    team_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> dict:
    team = load_directory_team(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    db.delete(team)
    db.commit()
    return {"deleted": True, "team_id": team_id}
