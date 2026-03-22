from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PointsScheme(TimestampMixin, Base):
    __tablename__ = "points_schemes"

    tournament_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tournaments.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    placements: Mapped[dict] = mapped_column(JSON, default=dict)

    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="points_schemes"
    )
    stages: Mapped[list["Stage"]] = relationship(
        "Stage", back_populates="points_scheme"
    )


class TieBreakRule(TimestampMixin, Base):
    __tablename__ = "tie_break_rules"

    tournament_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tournaments.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rules: Mapped[list] = mapped_column(JSON, default=list)

    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="tie_break_rules"
    )
    stages: Mapped[list["Stage"]] = relationship(
        "Stage", back_populates="tie_break_rule"
    )


class PlayerDirectoryEntry(TimestampMixin, Base):
    __tablename__ = "player_directory_entries"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    team_memberships: Mapped[list["TeamDirectoryMember"]] = relationship(
        "TeamDirectoryMember",
        back_populates="player",
        cascade="all, delete-orphan",
    )


class TeamDirectoryEntry(TimestampMixin, Base):
    __tablename__ = "team_directory_entries"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    members: Mapped[list["TeamDirectoryMember"]] = relationship(
        "TeamDirectoryMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )


class TeamDirectoryMember(TimestampMixin, Base):
    __tablename__ = "team_directory_members"
    __table_args__ = (
        UniqueConstraint("team_id", "player_id", name="uq_team_directory_member"),
    )

    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("team_directory_entries.id", ondelete="CASCADE")
    )
    player_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("player_directory_entries.id", ondelete="CASCADE")
    )

    team: Mapped[TeamDirectoryEntry] = relationship(
        TeamDirectoryEntry, back_populates="members"
    )
    player: Mapped[PlayerDirectoryEntry] = relationship(
        PlayerDirectoryEntry, back_populates="team_memberships"
    )


class Tournament(TimestampMixin, Base):
    __tablename__ = "tournaments"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    description: Mapped[str] = mapped_column(Text, default="")
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    created_by: Mapped["User | None"] = relationship(
        "User", back_populates="created_tournaments"
    )
    stages: Mapped[list["Stage"]] = relationship(
        "Stage", back_populates="tournament", cascade="all, delete-orphan"
    )
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", back_populates="tournament", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship(
        "Team", back_populates="tournament", cascade="all, delete-orphan"
    )
    points_schemes: Mapped[list[PointsScheme]] = relationship(
        PointsScheme, back_populates="tournament", cascade="all, delete-orphan"
    )
    tie_break_rules: Mapped[list[TieBreakRule]] = relationship(
        TieBreakRule, back_populates="tournament", cascade="all, delete-orphan"
    )


class Stage(TimestampMixin, Base):
    __tablename__ = "stages"

    tournament_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    points_scheme_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("points_schemes.id", ondelete="SET NULL")
    )
    tie_break_rule_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tie_break_rules.id", ondelete="SET NULL")
    )

    tournament: Mapped[Tournament] = relationship(Tournament, back_populates="stages")
    points_scheme: Mapped[PointsScheme | None] = relationship(
        PointsScheme, back_populates="stages"
    )
    tie_break_rule: Mapped[TieBreakRule | None] = relationship(
        TieBreakRule, back_populates="stages"
    )
    rounds: Mapped[list["Round"]] = relationship(
        "Round", back_populates="stage", cascade="all, delete-orphan"
    )
    advancement_rules: Mapped[list["AdvancementRule"]] = relationship(
        "AdvancementRule", back_populates="stage", cascade="all, delete-orphan"
    )


class AdvancementRule(TimestampMixin, Base):
    __tablename__ = "advancement_rules"

    stage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    apply_after_round: Mapped[int] = mapped_column(Integer, default=1)
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    stage: Mapped[Stage] = relationship(Stage, back_populates="advancement_rules")


class Round(TimestampMixin, Base):
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint("stage_id", "number", name="uq_rounds_stage_id_number"),
    )

    stage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stages.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    stage: Mapped[Stage] = relationship(Stage, back_populates="rounds")
    matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="round", cascade="all, delete-orphan"
    )


class Team(TimestampMixin, Base):
    __tablename__ = "teams"

    tournament_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seed_number: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")

    tournament: Mapped[Tournament] = relationship(Tournament, back_populates="teams")
    participants: Mapped[list["Participant"]] = relationship(
        "Participant", back_populates="team"
    )


class Participant(TimestampMixin, Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id",
            "display_name",
            name="uq_participants_tournament_id_display_name",
        ),
    )

    tournament_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    seed_number: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    tournament: Mapped[Tournament] = relationship(
        Tournament, back_populates="participants"
    )
    team: Mapped[Team | None] = relationship(Team, back_populates="participants")
    match_slots: Mapped[list["MatchParticipant"]] = relationship(
        "MatchParticipant", back_populates="participant", cascade="all, delete-orphan"
    )
    match_results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="participant", cascade="all, delete-orphan"
    )


class Match(TimestampMixin, Base):
    __tablename__ = "matches"

    round_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rounds.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, default="")
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    round: Mapped[Round] = relationship(Round, back_populates="matches")
    participants: Mapped[list["MatchParticipant"]] = relationship(
        "MatchParticipant", back_populates="match", cascade="all, delete-orphan"
    )
    results: Mapped[list["MatchResult"]] = relationship(
        "MatchResult", back_populates="match", cascade="all, delete-orphan"
    )


class MatchParticipant(TimestampMixin, Base):
    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "participant_id",
            name="uq_match_participants_match_id_participant_id",
        ),
    )

    match_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    slot_number: Mapped[int] = mapped_column(Integer, default=1)
    seed_number: Mapped[int | None] = mapped_column(Integer)

    match: Mapped[Match] = relationship(Match, back_populates="participants")
    participant: Mapped[Participant] = relationship(
        Participant, back_populates="match_slots"
    )


class MatchResult(TimestampMixin, Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "participant_id",
            name="uq_match_results_match_id_participant_id",
        ),
    )

    match_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    participant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("participants.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float | None] = mapped_column(nullable=True)
    tie_group: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    match: Mapped[Match] = relationship(Match, back_populates="results")
    participant: Mapped[Participant] = relationship(
        Participant, back_populates="match_results"
    )
