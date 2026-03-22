from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("login", "password")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty")
        return normalized


class AuthUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserRead


class MessageResponse(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if (
            not normalized
            or " " in normalized
            or "@" not in normalized
            or normalized.startswith("@")
            or normalized.endswith("@")
            or normalized.partition("@")[2].startswith(".")
            or normalized.partition("@")[2].endswith(".")
            or "." not in normalized.partition("@")[2]
        ):
            raise ValueError("Enter a valid email address")
        return normalized


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=1024)
    password: str = Field(min_length=8, max_length=255)

    @field_validator("token", "password")
    @classmethod
    def validate_non_blank_field(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be empty")
        return normalized
