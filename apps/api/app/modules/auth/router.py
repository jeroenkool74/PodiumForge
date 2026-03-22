from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.auth import (
    AuthUserRead,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TokenResponse,
)
from app.services.auth_service import auth_user_to_read_model, authenticate
from app.services.password_reset_service import (
    issue_password_reset,
    reset_password_with_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return authenticate(db, payload.login, payload.password)


@router.get("/me", response_model=AuthUserRead)
def me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    return auth_user_to_read_model(current_user)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    issue_password_reset(db, payload.email)
    return MessageResponse(
        message="If that email exists, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    reset_password_with_token(db, payload.token, payload.password)
    return MessageResponse(
        message="Password updated. You can now sign in with your new password."
    )
