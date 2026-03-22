from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.enums import RoleName
from app.models import User
from app.repositories import users as user_repository
from app.schemas.user import (
    UserCreateRequest,
    UserPasswordChangeRequest,
    UserRead,
    UserRolesUpdateRequest,
)
from app.services.auth_service import (
    create_user,
    delete_user_account,
    set_user_password,
    update_user_roles,
    user_to_read_model,
)

router = APIRouter(prefix="/users", tags=["users"])


def get_managed_user(db: Session, user_id: str) -> User:
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN)),
) -> list[UserRead]:
    return [user_to_read_model(user) for user in user_repository.list_users(db)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_account(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN)),
) -> UserRead:
    return create_user(db, payload)


@router.put("/{user_id}/roles", response_model=UserRead)
def update_user_roles_endpoint(
    user_id: str,
    payload: UserRolesUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
) -> UserRead:
    return update_user_roles(db, get_managed_user(db, user_id), current_user, payload)


@router.post(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def change_user_password(
    user_id: str,
    payload: UserPasswordChangeRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_roles(RoleName.ADMIN)),
) -> None:
    set_user_password(db, get_managed_user(db, user_id), payload.password)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def delete_user_endpoint(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
) -> None:
    delete_user_account(db, get_managed_user(db, user_id), current_user)
