from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    ADMIN = "ADMIN"
    TOURNAMENT_EDITOR = "TOURNAMENT_EDITOR"


class TournamentFormat(str, Enum):
    FFA_ELIMINATION = "FFA_ELIMINATION"
    GROUP_POINTS = "GROUP_POINTS"
    ROUND_ROBIN = "ROUND_ROBIN"
    SWISS = "SWISS"
    PAGE_PLAYOFF = "PAGE_PLAYOFF"
    STANDALONE_MATCH = "STANDALONE_MATCH"
    BRACKET = "BRACKET"
    DOUBLE_ELIMINATION = "DOUBLE_ELIMINATION"


class TournamentParticipantType(str, Enum):
    PLAYER = "PLAYER"
    TEAM = "TEAM"


class TournamentStatus(str, Enum):
    DRAFT = "DRAFT"
    LIVE = "LIVE"
    COMPLETED = "COMPLETED"


class RoundStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class ParticipantKind(str, Enum):
    PLAYER = "PLAYER"
    TEAM = "TEAM"


class AdvancementKind(str, Enum):
    MATCH_TOP_N = "MATCH_TOP_N"
    STANDINGS_TOP_N = "STANDINGS_TOP_N"


class StandingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    QUALIFIED = "QUALIFIED"
    ELIMINATED = "ELIMINATED"
    FINALIZED = "FINALIZED"
