from __future__ import annotations

from app.core.enums import LeaderboardMetric, ScoreDirection

DEFAULT_LEADERBOARD_METRIC = LeaderboardMetric.POINTS.value
DEFAULT_SCORE_DIRECTION = ScoreDirection.HIGHER_IS_BETTER.value
DEFAULT_SCORE_LABEL = "Score"


def normalize_leaderboard_metric(value: str | None) -> str:
    if value == LeaderboardMetric.SCORE.value:
        return LeaderboardMetric.SCORE.value
    return LeaderboardMetric.POINTS.value


def normalize_score_direction(value: str | None) -> str:
    if value == ScoreDirection.LOWER_IS_BETTER.value:
        return ScoreDirection.LOWER_IS_BETTER.value
    return ScoreDirection.HIGHER_IS_BETTER.value


def normalize_score_label(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or DEFAULT_SCORE_LABEL


def score_sort_value(score: float | None, direction: str | None) -> float:
    value = score or 0
    return (
        value
        if normalize_score_direction(direction) == ScoreDirection.LOWER_IS_BETTER.value
        else -value
    )


def score_label_for_settings(settings: dict | None) -> str:
    return normalize_score_label((settings or {}).get("score_label"))


def score_direction_for_settings(settings: dict | None) -> str:
    return normalize_score_direction((settings or {}).get("score_direction"))


def leaderboard_metric_for_settings(settings: dict | None) -> str:
    return normalize_leaderboard_metric((settings or {}).get("leaderboard_metric"))
