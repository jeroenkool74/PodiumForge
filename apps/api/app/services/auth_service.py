from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.repositories import users as user_repository
from app.schemas.auth import AuthUserRead, TokenResponse
from app.schemas.user import UserCreateRequest, UserRead, UserRolesUpdateRequest


def user_to_read_model(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        roles=sorted(role.name for role in user.roles),
    )


def auth_user_to_read_model(user: User) -> AuthUserRead:
    return AuthUserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=sorted(role.name for role in user.roles),
    )


def authenticate(db: Session, login: str, password: str) -> TokenResponse:
    normalized = login.strip().lower()
    user = user_repository.get_user_by_login(db, normalized)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=auth_user_to_read_model(user))


def create_user(db: Session, payload: UserCreateRequest) -> UserRead:
    if user_repository.get_user_by_email(db, payload.email.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )
    if user_repository.get_user_by_username(db, payload.username.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    role_names = [role.value for role in payload.roles]
    roles = user_repository.get_roles_by_names(db, role_names)
    if len(roles) != len(role_names):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role selection"
        )

    user = User(
        username=payload.username.lower(),
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        roles=roles,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_read_model(user)


def set_user_password(db: Session, user: User, password: str) -> None:
    user.password_hash = get_password_hash(password)
    user.password_reset_token_hash = None
    user.password_reset_sent_at = None
    user.password_reset_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)


def delete_user_account(db: Session, user: User, actor: User) -> None:
    if user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete the account you are currently using",
        )
    db.delete(user)
    db.commit()


def update_user_roles(
    db: Session, user: User, actor: User, payload: UserRolesUpdateRequest
) -> UserRead:
    role_names = [role.value for role in payload.roles]
    if user.id == actor.id and "ADMIN" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove your own admin role",
        )

    roles = user_repository.get_roles_by_names(db, role_names)
    if len(roles) != len(role_names):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role selection"
        )

    user.roles = roles
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_read_model(user)
