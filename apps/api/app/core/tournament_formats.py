from __future__ import annotations

from app.core.enums import TournamentFormat


BRACKET_STYLE_FORMATS = {
    TournamentFormat.BRACKET.value,
    TournamentFormat.DOUBLE_ELIMINATION.value,
    TournamentFormat.PAGE_PLAYOFF.value,
}

FIXED_HEAD_TO_HEAD_MATCH_FORMATS = {
    TournamentFormat.ROUND_ROBIN.value,
    TournamentFormat.SWISS.value,
    *BRACKET_STYLE_FORMATS,
}

TABLE_STANDINGS_FORMATS = {
    TournamentFormat.ROUND_ROBIN.value,
    TournamentFormat.SWISS.value,
}

AUTO_ADVANCEMENT_FORMATS = {
    TournamentFormat.STANDALONE_MATCH.value,
    TournamentFormat.ROUND_ROBIN.value,
    TournamentFormat.SWISS.value,
    TournamentFormat.PAGE_PLAYOFF.value,
    TournamentFormat.BRACKET.value,
    TournamentFormat.DOUBLE_ELIMINATION.value,
}


def _format_value(format_value: TournamentFormat | str) -> str:
    return (
        format_value.value
        if isinstance(format_value, TournamentFormat)
        else format_value
    )


def is_bracket_style_format(format_value: TournamentFormat | str) -> bool:
    return _format_value(format_value) in BRACKET_STYLE_FORMATS


def uses_fixed_head_to_head_matches(format_value: TournamentFormat | str) -> bool:
    return _format_value(format_value) in FIXED_HEAD_TO_HEAD_MATCH_FORMATS


def uses_table_standings(format_value: TournamentFormat | str) -> bool:
    return _format_value(format_value) in TABLE_STANDINGS_FORMATS


def requires_manual_advance_count(format_value: TournamentFormat | str) -> bool:
    return _format_value(format_value) not in AUTO_ADVANCEMENT_FORMATS
