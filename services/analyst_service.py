from __future__ import annotations

from typing import Any, Dict


def extract_analyst_targets(info: Dict[str, Any]) -> Dict[str, float]:
    return {
        "high": float(info.get("targetHighPrice") or 0.0),
        "average": float(info.get("targetMeanPrice") or 0.0),
        "low": float(info.get("targetLowPrice") or 0.0),
        "buy": float(info.get("recommendationKey") == "buy"),
        "hold": float(info.get("recommendationKey") == "hold"),
        "sell": float(info.get("recommendationKey") == "sell"),
    }
