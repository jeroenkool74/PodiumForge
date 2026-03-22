from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.enums import RoleName


def normalize_non_blank(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Value cannot be empty")
    return normalized


def normalize_email(value: str) -> str:
    normalized = normalize_non_blank(value).lower()
    if " " in normalized:
        raise ValueError("Enter a valid email address")
    local_part, separator, domain = normalized.partition("@")
    if (
        not separator
        or not local_part
        or not domain
        or domain.startswith(".")
        or domain.endswith(".")
    ):
        raise ValueError("Enter a valid email address")
    if "." not in domain:
        raise ValueError("Enter a valid email address")
    return normalized


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)
    roles: list[RoleName] = Field(default_factory=lambda: [RoleName.TOURNAMENT_EDITOR])

    @field_validator("username", "password")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        return normalize_non_blank(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[RoleName]) -> list[RoleName]:
        if not value:
            raise ValueError("Select at least one role")
        return value


class UserRead(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    roles: list[str]


class UserPasswordChangeRequest(BaseModel):
    password: str = Field(min_length=8, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return normalize_non_blank(value)


class UserRolesUpdateRequest(BaseModel):
    roles: list[RoleName] = Field(default_factory=list)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[RoleName]) -> list[RoleName]:
        if not value:
            raise ValueError("Select at least one role")
        return value
