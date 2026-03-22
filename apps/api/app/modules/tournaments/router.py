from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.enums import MatchStatus, RoleName, TournamentStatus
from app.models import Match, Participant, TieBreakRule, Tournament, User
from app.repositories.tournaments import (
    get_tournament_by_identifier,
    list_tournaments_for_management,
)
from app.schemas.tournament import (
    AdminDashboardRead,
    ParticipantCreateRequest,
    ParticipantRead,
    PointsSchemeUpdateRequest,
    RoundRead,
    TieBreakRuleCreateRequest,
    TieBreakRuleItemRead,
    TieBreakRuleUpdateRequest,
    TournamentCardRead,
    TournamentCreateRequest,
    TournamentDetailRead,
    TournamentUpdateRequest,
)
from app.services.match_service import points_for_rank
from app.services.progression_service import generate_next_round
from app.services.standings_service import (
    serialize_tournament_card,
    serialize_tournament_detail,
)
from app.services.tie_break_service import (
    DEFAULT_TIE_BREAK_RULES,
    build_rule_item,
    normalize_tie_break_rules,
    serialize_tie_break_rule_items,
)
from app.services.tournament_builder import (
    add_participant,
    build_points_mapping,
    create_tournament,
    update_tournament,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def get_managed_tournament(db: Session, tournament_id: str) -> Tournament:
    tournament = get_tournament_by_identifier(db, tournament_id, public_only=False)
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        )
    return tournament


def _primary_points_scheme(tournament: Tournament):
    if tournament.points_schemes:
        return tournament.points_schemes[0]
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tournament has no points scheme configured",
    )


def _primary_tie_break_rule(db: Session, tournament: Tournament) -> TieBreakRule:
    if tournament.tie_break_rules:
        return tournament.tie_break_rules[0]

    rule = TieBreakRule(
        tournament=tournament,
        name="Default tie-breaks",
        rules=[dict(item) for item in DEFAULT_TIE_BREAK_RULES],
    )
    if tournament.stages and tournament.stages[0].tie_break_rule is None:
        tournament.stages[0].tie_break_rule = rule
    db.add(rule)
    db.flush()
    return rule


@router.get("", response_model=list[TournamentCardRead])
def list_managed_tournaments(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> list[TournamentCardRead]:
    return [
        TournamentCardRead(**serialize_tournament_card(item))
        for item in list_tournaments_for_management(db)
    ]


@router.get("/dashboard", response_model=AdminDashboardRead)
def admin_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> AdminDashboardRead:
    tournaments = db.scalar(select(func.count(Tournament.id))) or 0
    live_tournaments = (
        db.scalar(
            select(func.count(Tournament.id)).where(
                Tournament.status == TournamentStatus.LIVE.value
            )
        )
        or 0
    )
    users = db.scalar(select(func.count(User.id))) or 0
    completed_matches = (
        db.scalar(
            select(func.count(Match.id)).where(
                Match.status == MatchStatus.COMPLETED.value
            )
        )
        or 0
    )
    return AdminDashboardRead(
        tournaments=int(tournaments),
        live_tournaments=int(live_tournaments),
        users=int(users),
        completed_matches=int(completed_matches),
    )


@router.post(
    "", response_model=TournamentDetailRead, status_code=status.HTTP_201_CREATED
)
def create_tournament_endpoint(
    payload: TournamentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)
    ),
) -> TournamentDetailRead:
    tournament = create_tournament(db, payload, current_user)
    full = get_managed_tournament(db, tournament.id)
    return TournamentDetailRead(**serialize_tournament_detail(full))


@router.get("/{tournament_id}", response_model=TournamentDetailRead)
def get_tournament_endpoint(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> TournamentDetailRead:
    return TournamentDetailRead(
        **serialize_tournament_detail(get_managed_tournament(db, tournament_id))
    )


@router.patch("/{tournament_id}", response_model=TournamentDetailRead)
def update_tournament_endpoint(
    tournament_id: str,
    payload: TournamentUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> TournamentDetailRead:
    tournament = get_managed_tournament(db, tournament_id)
    update_tournament(db, tournament, payload)
    return TournamentDetailRead(
        **serialize_tournament_detail(get_managed_tournament(db, tournament_id))
    )


@router.patch("/{tournament_id}/points-scheme", response_model=TournamentDetailRead)
def update_points_scheme_endpoint(
    tournament_id: str,
    payload: PointsSchemeUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> TournamentDetailRead:
    tournament = get_managed_tournament(db, tournament_id)
    points_scheme = _primary_points_scheme(tournament)
    points_scheme.placements = build_points_mapping(payload.points_scheme)
    db.add(points_scheme)
    db.commit()
    return TournamentDetailRead(
        **serialize_tournament_detail(get_managed_tournament(db, tournament_id))
    )


@router.post("/{tournament_id}/recalculate-points")
def recalculate_points_endpoint(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> dict:
    tournament = get_managed_tournament(db, tournament_id)
    updated_count = 0
    total_results = 0

    for stage in tournament.stages:
        for round_item in stage.rounds:
            for match in round_item.matches:
                for result in match.results:
                    total_results += 1
                    new_points = points_for_rank(match, result.rank)
                    if result.points_awarded != new_points:
                        result.points_awarded = new_points
                        db.add(result)
                        updated_count += 1

    db.commit()
    return {
        "recalculated": updated_count,
        "total_results": total_results,
        "message": f"Recalculated points for {updated_count} result(s).",
    }


@router.post(
    "/{tournament_id}/participants",
    response_model=ParticipantRead,
    status_code=status.HTTP_201_CREATED,
)
def add_participant_endpoint(
    tournament_id: str,
    payload: ParticipantCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> ParticipantRead:
    participant = add_participant(
        db, get_managed_tournament(db, tournament_id), payload
    )
    return ParticipantRead(
        id=participant.id,
        display_name=participant.display_name,
        kind=participant.kind,
        seed_number=participant.seed_number,
        members=list(participant.metadata_json.get("members", [])),
    )


@router.get(
    "/{tournament_id}/tie-break-rules", response_model=list[TieBreakRuleItemRead]
)
def list_tie_break_rules_endpoint(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> list[TieBreakRuleItemRead]:
    tournament = get_managed_tournament(db, tournament_id)
    return [
        TieBreakRuleItemRead(**item)
        for item in serialize_tie_break_rule_items(
            _primary_tie_break_rule(db, tournament).rules
        )
    ]


@router.post(
    "/{tournament_id}/tie-break-rules",
    response_model=TieBreakRuleItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_tie_break_rule_endpoint(
    tournament_id: str,
    payload: TieBreakRuleCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> TieBreakRuleItemRead:
    tournament = get_managed_tournament(db, tournament_id)
    rule = _primary_tie_break_rule(db, tournament)
    items = normalize_tie_break_rules(rule.rules)
    insert_at = min(payload.order_index, len(items))
    items.insert(
        insert_at,
        build_rule_item(payload.config.rule_type, name=payload.name),
    )
    rule.rules = items
    db.add(rule)
    db.commit()
    return TieBreakRuleItemRead(**serialize_tie_break_rule_items(rule.rules)[insert_at])


@router.patch(
    "/{tournament_id}/tie-break-rules/{rule_id}", response_model=TieBreakRuleItemRead
)
def update_tie_break_rule_endpoint(
    tournament_id: str,
    rule_id: str,
    payload: TieBreakRuleUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> TieBreakRuleItemRead:
    tournament = get_managed_tournament(db, tournament_id)
    rule = _primary_tie_break_rule(db, tournament)
    items = normalize_tie_break_rules(rule.rules)
    current_index = next(
        (index for index, item in enumerate(items) if item["id"] == rule_id), None
    )
    if current_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tie-break rule not found",
        )

    item = items.pop(current_index)
    if payload.name is not None:
        item["name"] = payload.name.strip()
    if payload.config is not None:
        item["rule_type"] = build_rule_item(
            payload.config.rule_type,
            name=item.get("name"),
            rule_id=item["id"],
        )["rule_type"]
    next_index = (
        payload.order_index if payload.order_index is not None else current_index
    )
    next_index = min(max(next_index, 0), len(items))
    items.insert(next_index, item)
    rule.rules = items
    db.add(rule)
    db.commit()
    return TieBreakRuleItemRead(
        **serialize_tie_break_rule_items(rule.rules)[next_index]
    )


@router.delete("/{tournament_id}/tie-break-rules/{rule_id}")
def delete_tie_break_rule_endpoint(
    tournament_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> dict:
    tournament = get_managed_tournament(db, tournament_id)
    rule = _primary_tie_break_rule(db, tournament)
    items = normalize_tie_break_rules(rule.rules)
    next_items = [item for item in items if item["id"] != rule_id]
    if len(next_items) == len(items):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tie-break rule not found",
        )
    rule.rules = next_items
    db.add(rule)
    db.commit()
    return {"deleted": True, "rule_id": rule_id}


@router.post("/{tournament_id}/rounds/next", response_model=RoundRead)
def generate_next_round_endpoint(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN, RoleName.TOURNAMENT_EDITOR)),
) -> RoundRead:
    next_round = generate_next_round(db, get_managed_tournament(db, tournament_id))
    refreshed_detail = serialize_tournament_detail(
        get_managed_tournament(db, tournament_id)
    )
    for stage in refreshed_detail["stages"]:
        for round_item in stage["rounds"]:
            if round_item["id"] == next_round.id:
                return RoundRead(**round_item)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Round creation failed",
    )


@router.delete(
    "/{tournament_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_tournament_endpoint(
    tournament_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleName.ADMIN)),
) -> None:
    db.delete(get_managed_tournament(db, tournament_id))
    db.commit()
