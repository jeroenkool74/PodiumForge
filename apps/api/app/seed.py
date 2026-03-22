from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.enums import RoleName
from app.core.security import get_password_hash
from app.models import Role, Tournament, User
from app.services.tournament_status_service import repair_tournament_statuses

LEGACY_DEMO_SLUGS = {
    "friday-lan-ffa",
    "tabletop-showcase",
    "points-race-showcase",
    "city-cup-bracket",
}


def ensure_roles(db: Session) -> None:
    for role_name, description in {
        RoleName.ADMIN.value: "Full system administrator",
        RoleName.TOURNAMENT_EDITOR.value: "Tournament operations editor",
    }.items():
        if not db.query(Role).filter(Role.name == role_name).first():
            db.add(Role(name=role_name, description=description))
    db.commit()


def ensure_admin(db: Session) -> User:
    settings = get_settings()
    admin = db.query(User).filter(User.email == settings.seeded_admin_email).first()
    admin_role = db.query(Role).filter(Role.name == RoleName.ADMIN.value).first()
    editor_role = (
        db.query(Role).filter(Role.name == RoleName.TOURNAMENT_EDITOR.value).first()
    )
    if admin:
        return admin

    admin = User(
        username=settings.seeded_admin_username,
        email=settings.seeded_admin_email,
        password_hash=get_password_hash(settings.seeded_admin_password),
        roles=[role for role in [admin_role, editor_role] if role],
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def delete_legacy_demo_tournaments(db: Session) -> None:
    legacy_tournaments = list(
        db.scalars(
            select(Tournament).where(Tournament.slug.in_(LEGACY_DEMO_SLUGS))
        ).all()
    )
    if not legacy_tournaments:
        return

    for tournament in legacy_tournaments:
        db.delete(tournament)
    db.commit()


def seed() -> None:
    db = SessionLocal()
    try:
        ensure_roles(db)
        ensure_admin(db)
        delete_legacy_demo_tournaments(db)
        repair_tournament_statuses(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
