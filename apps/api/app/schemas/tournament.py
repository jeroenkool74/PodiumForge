from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.enums import TournamentFormat, TournamentParticipantType, TournamentStatus
from app.core.tournament_formats import requires_manual_advance_count


class PlacementPointsInput(BaseModel):
    placement: int = Field(ge=1)
    points: int = Field(ge=0)


class TournamentCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    format: TournamentFormat
    participant_type: TournamentParticipantType
    match_size: int = Field(default=5, ge=2, le=64)
    participants: list[str] = Field(default_factory=list, max_length=256)
    directory_player_ids: list[str] = Field(default_factory=list, max_length=256)
    directory_team_ids: list[str] = Field(default_factory=list, max_length=256)
    points_scheme: list[PlacementPointsInput] = Field(default_factory=list)
    advance_count: int | None = Field(default=None, ge=1, le=64)
    is_public: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Name must be at least 3 characters")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        return value.strip()

    @field_validator("participants")
    @classmethod
    def validate_participants(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if values and not normalized:
            raise ValueError("At least two participant names are required")
        return normalized

    @model_validator(mode="after")
    def validate_advancement(self) -> "TournamentCreateRequest":
        if (
            requires_manual_advance_count(self.format)
            and (
                len(self.participants)
                + len(self.directory_player_ids)
                + len(self.directory_team_ids)
            )
            > self.match_size
            and self.advance_count is None
        ):
            raise ValueError("Advance count is required for multi-match formats")

        participant_count = len(self.participants) + (
            len(self.directory_team_ids)
            if self.participant_type == TournamentParticipantType.TEAM
            else len(self.directory_player_ids)
        )
        if participant_count < 2:
            raise ValueError(
                "Add at least two participants before creating the tournament"
            )

        if (
            self.format == TournamentFormat.FFA_ELIMINATION
            and self.advance_count is not None
            and self.advance_count >= self.match_size
        ):
            raise ValueError("Advance count must be smaller than the match size")

        if self.format == TournamentFormat.DOUBLE_ELIMINATION:
            participant_count = len(self.participants)
            if participant_count < 4:
                raise ValueError(
                    "Double-elimination brackets require at least 4 participants"
                )
            if participant_count & (participant_count - 1):
                raise ValueError(
                    "Double-elimination brackets currently require a power-of-two participant count"
                )

        if self.format == TournamentFormat.PAGE_PLAYOFF and len(self.participants) != 4:
            raise ValueError("Page playoff requires exactly 4 participants")

        return self


class TournamentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: TournamentStatus | None = None
    is_public: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Name must be at least 3 characters")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class ParticipantCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    directory_entry_id: str | None = Field(default=None, min_length=1, max_length=36)
    seed_number: int | None = Field(default=None, ge=1, le=512)
    team_members: list[str] = Field(default_factory=list, max_length=64)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be empty")
        return normalized


class TournamentCardRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    format: str
    participant_type: str
    status: str
    is_public: bool
    participant_count: int
    current_round_name: str | None
    match_size: int | None


class ParticipantRead(BaseModel):
    id: str
    display_name: str
    kind: str
    seed_number: int | None
    members: list[str] = Field(default_factory=list)


class MatchParticipantRead(BaseModel):
    participant_id: str
    display_name: str
    slot_number: int
    seed_number: int | None = None
    rank: int | None = None
    points_awarded: int | None = None
    score: float | None = None
    tie_group: int | None = None


class MatchRead(BaseModel):
    id: str
    name: str
    sequence: int
    status: str
    scheduled_at: datetime | None
    notes: str
    tournament_id: str
    tournament_name: str
    tournament_slug: str
    round_id: str
    round_name: str
    is_bye: bool = False
    results_locked: bool = False
    entrants: list[MatchParticipantRead]


class RoundRead(BaseModel):
    id: str
    name: str
    number: int
    status: str
    is_final: bool
    bracket_kind: str | None = None
    matches: list[MatchRead]


class StageRead(BaseModel):
    id: str
    name: str
    order_index: int
    match_size: int | None
    advancement_kind: str | None = None
    advance_count: int | None = None
    points_scheme: list[PlacementPointsInput] = Field(default_factory=list)
    tie_break_rules: list[str] = Field(default_factory=list)
    rounds: list[RoundRead]
    advancement_summary: str | None


class StandingEntryRead(BaseModel):
    participant_id: str
    display_name: str
    total_points: int
    matches_played: int
    best_rank: int | None
    average_rank: float | None
    current_status: str
    latest_round_name: str | None
    latest_rank: int | None
    final_placement: int | None


class TournamentDetailRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    format: str
    participant_type: str
    status: str
    is_public: bool
    participants: list[ParticipantRead]
    stages: list[StageRead]
    standings: list[StandingEntryRead]
    qualified: list[str]
    eliminated: list[str]
    can_generate_next_round: bool


class DashboardRead(BaseModel):
    tournament_name: str
    tournament_slug: str
    tournament_format: str
    participant_type: str
    participant_count: int
    tournament_status: str
    current_round_name: str | None
    rounds: list[RoundRead]
    upcoming_matches: list[MatchRead]
    standings: list[StandingEntryRead]
    qualified: list[str]
    eliminated: list[str]
    podium: list[StandingEntryRead]
    auto_refresh_seconds: int = 10


class AdminDashboardRead(BaseModel):
    tournaments: int
    live_tournaments: int
    users: int
    completed_matches: int


class MatchScheduleUpdateRequest(BaseModel):
    scheduled_at: datetime | None = None


class PointsSchemeUpdateRequest(BaseModel):
    points_scheme: list[PlacementPointsInput] = Field(default_factory=list)


class TieBreakRuleConfigInput(BaseModel):
    rule_type: str = Field(min_length=1, max_length=64)


class TieBreakRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    order_index: int = Field(ge=0)
    config: TieBreakRuleConfigInput


class TieBreakRuleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    order_index: int | None = Field(default=None, ge=0)
    config: TieBreakRuleConfigInput | None = None


class TieBreakRuleItemRead(BaseModel):
    id: str
    name: str
    order_index: int
    config: dict


class TournamentConfigParticipantInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    members: list[str] = Field(default_factory=list, max_length=64)


class TournamentConfigExportRead(BaseModel):
    name: str
    description: str
    format: str
    participant_type: str
    match_size: int
    advance_count: int | None = None
    is_public: bool
    points_scheme: list[PlacementPointsInput] = Field(default_factory=list)
    tie_break_rules: list[TieBreakRuleItemRead] = Field(default_factory=list)
    participants: list[TournamentConfigParticipantInput] = Field(default_factory=list)


class TournamentConfigImportRequest(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    format: TournamentFormat
    participant_type: TournamentParticipantType
    match_size: int = Field(default=5, ge=2, le=64)
    advance_count: int | None = Field(default=None, ge=1, le=64)
    is_public: bool = True
    points_scheme: list[PlacementPointsInput] = Field(default_factory=list)
    tie_break_rules: list[TieBreakRuleItemRead] = Field(default_factory=list)
    participants: list[TournamentConfigParticipantInput] = Field(default_factory=list)


class PublicTeamRead(BaseModel):
    id: str
    name: str
    members: list[str] = Field(default_factory=list)


class PublicTeamsRead(BaseModel):
    tournament_id: str
    tournament_name: str
    participant_type: str
    teams: list[PublicTeamRead] = Field(default_factory=list)
