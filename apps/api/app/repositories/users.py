from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Role, User


def get_user_by_login(db: Session, login: str) -> User | None:
    statement = (
        select(User)
        .options(selectinload(User.roles))
        .where((User.email == login.lower()) | (User.username == login.lower()))
    )
    return db.scalar(statement)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == email.lower())
    )


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.username == username.lower())
    )


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )


def get_user_by_password_reset_token_hash(db: Session, token_hash: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.password_reset_token_hash == token_hash)
    )


def list_users(db: Session) -> list[User]:
    statement = (
        select(User).options(selectinload(User.roles)).order_by(User.username.asc())
    )
    return list(db.scalars(statement).unique().all())


def get_roles_by_names(db: Session, names: list[str]) -> list[Role]:
    if not names:
        return []
    statement = select(Role).where(Role.name.in_(names)).order_by(Role.name.asc())
    return list(db.scalars(statement).all())
