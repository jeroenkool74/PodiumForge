from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories import users as user_repository
from app.services.auth_service import set_user_password
from app.services.email_service import send_email


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def build_password_reset_link(token: str) -> str:
    settings = get_settings()
    parsed = urlparse(settings.password_reset_url_base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["token"] = token
    return urlunparse(parsed._replace(query=urlencode(query)))


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_password_reset_email(
    recipient: str, username: str, reset_link: str, expires_at: datetime
) -> None:
    expiry_label = as_utc(expires_at).strftime("%Y-%m-%d %H:%M UTC")
    text_body = (
        f"Hello {username},\n\n"
        "A password reset was requested for your PodiumForge account. "
        "Use the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires on {expiry_label}. If you did not request this change, you can ignore this email.\n"
    )
    html_body = (
        f"<p>Hello {username},</p>"
        "<p>A password reset was requested for your PodiumForge account. "
        "Use the link below to choose a new password:</p>"
        f'<p><a href="{reset_link}">Reset password</a></p>'
        f"<p>This link expires on {expiry_label}. If you did not request this change, you can ignore this email.</p>"
    )
    send_email(
        recipient=recipient,
        subject="PodiumForge password reset",
        text_body=text_body,
        html_body=html_body,
    )


def issue_password_reset(db: Session, email: str) -> None:
    user = user_repository.get_user_by_email(db, email.lower())
    if not user or not user.is_active:
        return

    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    user.password_reset_token_hash = hash_password_reset_token(token)
    user.password_reset_sent_at = now
    user.password_reset_expires_at = now + timedelta(
        minutes=settings.password_reset_expire_minutes
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        send_password_reset_email(
            recipient=user.email,
            username=user.username,
            reset_link=build_password_reset_link(token),
            expires_at=user.password_reset_expires_at,
        )
    except Exception:
        user.password_reset_token_hash = None
        user.password_reset_sent_at = None
        user.password_reset_expires_at = None
        db.add(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send password reset email right now",
        )


def reset_password_with_token(db: Session, token: str, password: str) -> None:
    user = user_repository.get_user_by_password_reset_token_hash(
        db, hash_password_reset_token(token)
    )
    if (
        not user
        or not user.password_reset_expires_at
        or as_utc(user.password_reset_expires_at) < datetime.now(timezone.utc)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or has expired",
        )

    set_user_password(db, user, password)
