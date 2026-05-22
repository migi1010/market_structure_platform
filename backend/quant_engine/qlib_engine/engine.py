from __future__ import annotations

from typing import Any, Dict

from qlib_engine.pipeline import run_alpha_pipeline


def run_alpha_ranking(universe: str = "sp500") -> Dict[str, Any]:
    normalized = "nasdaq100" if universe.lower() == "nasdaq100" else "sp500"
    return run_alpha_pipeline(normalized)
