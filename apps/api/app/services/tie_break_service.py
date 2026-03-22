from __future__ import annotations

from uuid import uuid4

RULE_TYPE_LABELS = {
    "HEAD_TO_HEAD": "Head-to-head",
    "TOTAL_POINTS": "Total points",
    "BEST_RANK": "Best rank",
    "SCORE_TOTAL": "Score total",
    "MATCHES_PLAYED": "Matches played",
    "AVERAGE_RANK": "Average rank",
    "DISPLAY_NAME": "Display name",
}

RULE_TYPE_ALIASES = {
    "head_to_head": "HEAD_TO_HEAD",
    "total_points": "TOTAL_POINTS",
    "best_rank": "BEST_RANK",
    "score_total": "SCORE_TOTAL",
    "points_differential": "SCORE_TOTAL",
    "matches_played": "MATCHES_PLAYED",
    "average_rank": "AVERAGE_RANK",
    "display_name": "DISPLAY_NAME",
    "best_rank_asc": "BEST_RANK",
    "average_rank_asc": "AVERAGE_RANK",
    "display_name_asc": "DISPLAY_NAME",
}

CLIENT_RULE_TYPE_MAP = {
    value: key
    for key, value in RULE_TYPE_ALIASES.items()
    if key
    in {
        "head_to_head",
        "total_points",
        "best_rank",
        "score_total",
        "matches_played",
        "average_rank",
        "display_name",
    }
}

DEFAULT_TIE_BREAK_RULES = [
    {"id": "best-rank", "name": "Best rank", "rule_type": "BEST_RANK"},
    {"id": "average-rank", "name": "Average rank", "rule_type": "AVERAGE_RANK"},
    {"id": "display-name", "name": "Display name", "rule_type": "DISPLAY_NAME"},
]


def coerce_rule_type(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Tie-break rule type is required")
    candidate = RULE_TYPE_ALIASES.get(normalized.lower(), normalized.upper())
    if candidate not in RULE_TYPE_LABELS:
        raise ValueError(f"Unsupported tie-break rule type: {value}")
    return candidate


def build_rule_item(
    rule_type: str, *, name: str | None = None, rule_id: str | None = None
) -> dict:
    coerced = coerce_rule_type(rule_type)
    return {
        "id": rule_id or str(uuid4()),
        "name": (name or RULE_TYPE_LABELS[coerced]).strip(),
        "rule_type": coerced,
    }


def normalize_tie_break_rules(raw_rules: list | None) -> list[dict]:
    if not raw_rules:
        return [dict(rule) for rule in DEFAULT_TIE_BREAK_RULES]

    normalized_rules: list[dict] = []
    for index, raw_rule in enumerate(raw_rules, start=1):
        if isinstance(raw_rule, str):
            normalized_rules.append(
                build_rule_item(raw_rule, rule_id=f"legacy-{index}")
            )
            continue

        if isinstance(raw_rule, dict):
            rule_type = (
                raw_rule.get("rule_type")
                or raw_rule.get("type")
                or raw_rule.get("value")
            )
            if not isinstance(rule_type, str):
                continue
            name = raw_rule.get("name")
            rule_id = raw_rule.get("id")
            normalized_rules.append(
                build_rule_item(
                    rule_type,
                    name=name if isinstance(name, str) else None,
                    rule_id=rule_id if isinstance(rule_id, str) else None,
                )
            )

    return normalized_rules or [dict(rule) for rule in DEFAULT_TIE_BREAK_RULES]


def serialize_tie_break_rule_items(raw_rules: list | None) -> list[dict]:
    items = normalize_tie_break_rules(raw_rules)
    serialized: list[dict] = []
    for index, item in enumerate(items):
        rule_type = item["rule_type"]
        serialized.append(
            {
                "id": item["id"],
                "name": item["name"],
                "order_index": index,
                "config": {
                    "rule_type": CLIENT_RULE_TYPE_MAP.get(rule_type, rule_type.lower())
                },
            }
        )
    return serialized


def tie_break_rule_labels(raw_rules: list | None) -> list[str]:
    return [item["name"] for item in normalize_tie_break_rules(raw_rules)]
