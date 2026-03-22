from __future__ import annotations

from pydantic import BaseModel, Field


class MatchResultInput(BaseModel):
    participant_id: str
    rank: int = Field(ge=1)
    score: float | None = None
    tie_group: int | None = Field(default=None, ge=1)
    notes: str = Field(default="", max_length=500)


class MatchResultsUpsertRequest(BaseModel):
    results: list[MatchResultInput] = Field(min_length=1, max_length=128)


class MatchScheduleUpdateRequest(BaseModel):
    scheduled_at: str | None = None
