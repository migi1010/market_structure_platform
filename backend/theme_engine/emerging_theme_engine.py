from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from quant_engine.data_pipeline import safe_float

from .theme_rotation import build_theme_snapshot


def get_emerging_themes(limit: int = 12) -> Dict[str, Any]:
    themes = build_theme_snapshot()
    emerging = sorted(
        themes,
        key=lambda item: (
            safe_float(item.get("emerging_score")),
            safe_float(item.get("narrative_acceleration")),
            safe_float(item.get("supply_chain_acceleration")),
        ),
        reverse=True,
    )[:limit]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "emerging_themes": emerging,
        "summary": _summary(emerging),
    }


def _summary(emerging: list[Dict[str, Any]]) -> str:
    if not emerging:
        return "No emerging theme has enough evidence yet."
    names = ", ".join(str(item.get("theme")) for item in emerging[:3])
    return f"{names} show the strongest early acceleration across capital flow, supply chain and narrative factors."
