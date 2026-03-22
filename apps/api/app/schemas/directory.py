from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Value cannot be empty")
    return normalized


class DirectoryPlayerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DirectoryPlayerUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DirectoryPlayerRead(BaseModel):
    id: str
    name: str


class DirectoryTeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    player_ids: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DirectoryTeamUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    player_ids: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_name(value)


class DirectoryTeamRead(BaseModel):
    id: str
    name: str
    members: list[DirectoryPlayerRead] = Field(default_factory=list)
