from __future__ import annotations

import json
from typing import Any


def parse_score_history(score_history_json: str | None) -> list[dict[str, Any]]:
    if not score_history_json:
        return []
    try:
        parsed = json.loads(score_history_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def append_lifecycle_snapshot(score_history_json: str | None, snapshot: dict[str, Any], limit: int = 120) -> str:
    history = parse_score_history(score_history_json)
    history.append(snapshot)
    return json.dumps(history[-limit:], ensure_ascii=False, allow_nan=False)
