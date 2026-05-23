from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from quant_engine.data_pipeline import safe_float

from .theme_rotation import build_theme_snapshot


def get_theme_capital_flow(limit: int = 20) -> Dict[str, Any]:
    themes = build_theme_snapshot()
    flows = sorted(themes, key=lambda item: safe_float(item.get("theme_capital_flow_score")), reverse=True)[:limit]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capital_flow": [
            {
                "theme": item.get("theme"),
                "category": item.get("category"),
                "theme_capital_flow_score": item.get("theme_capital_flow_score"),
                "institutional_accumulation": item.get("institutional_accumulation"),
                "smart_money_accumulation": item.get("smart_money_accumulation"),
                "volume_expansion": item.get("volume_expansion"),
                "breadth_participation": item.get("breadth_participation"),
                "relative_strength_vs_spy": item.get("relative_strength_vs_spy"),
                "leaders": item.get("leaders", []),
            }
            for item in flows
        ],
        "summary": _flow_summary(flows),
    }


def _flow_summary(flows: list[Dict[str, Any]]) -> str:
    if not flows:
        return "Capital flow engine is warming up live market data."
    leaders = ", ".join(str(item.get("theme")) for item in flows[:3])
    return f"Institutional capital flow proxy is strongest in {leaders}, driven by relative volume, breadth and ETF leadership."
