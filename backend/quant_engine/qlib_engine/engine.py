from __future__ import annotations

import os
from typing import Any, Dict

from qlib_engine.pipeline import run_alpha_pipeline

try:
    if os.getenv("DISABLE_QLIB", "").strip().lower() in {"1", "true", "yes", "on"}:
        raise RuntimeError("qlib disabled by environment")
    import qlib  # type: ignore

    QLIB_AVAILABLE = True
except Exception:
    qlib = None  # type: ignore[assignment]
    QLIB_AVAILABLE = False


def run_alpha_ranking(universe: str = "sp500") -> Dict[str, Any]:
    normalized = universe.lower().strip().replace(" ", "_").replace("/", "_").replace("-", "_")
    result = run_alpha_pipeline(normalized, qlib_available=QLIB_AVAILABLE)
    result["qlib_engine"] = {
        **(result.get("qlib_engine") or {}),
        "available": QLIB_AVAILABLE,
        "mode": "qlib" if QLIB_AVAILABLE else "fallback",
    }
    return result
