from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from quant_engine.narrative_engine import build_cross_theme_ranking, build_narrative_signal
from quant_engine.ranking_engine import build_universe_ranking

from .theme_detector import ThemeDefinition, get_theme_definitions


def analyze_theme_narrative(theme: ThemeDefinition, news_limit_per_symbol: int = 3) -> Dict[str, Any]:
    from .theme_rotation import _fallback_theme_row, get_cached_theme_snapshot

    normalized = theme.name.strip().lower()
    snapshot = get_cached_theme_snapshot() or []
    row = next((item for item in snapshot if str(item.get("theme") or "").strip().lower() == normalized), None)
    signal = build_narrative_signal(row or _fallback_theme_row(theme))
    return {**signal, "generated_at": datetime.now(timezone.utc).isoformat(), "keywords": list(theme.narrative_keywords)}


def analyze_all_narratives(limit: int = 12) -> Dict[str, Any]:
    from .theme_rotation import _fallback_theme_row, get_cached_theme_snapshot

    snapshot = get_cached_theme_snapshot()
    if not snapshot:
        definitions = get_theme_definitions()[:limit]
        snapshot = [_fallback_theme_row(theme) for theme in definitions]
    ranking = build_cross_theme_ranking(snapshot, limit=limit)
    universe = build_universe_ranking(snapshot, entity_type="theme", limit=limit)
    return {
        **ranking,
        "universe_ranking": universe,
        "summary": ranking.get("summary") or "Narrative acceleration engine is ranking lightweight theme leadership inputs.",
    }


def _narrative_summary(theme_name: str, strength: float, acceleration: float, saturation: float) -> str:
    if acceleration >= 75 and saturation < 75:
        return f"{theme_name} narrative is accelerating without broad saturation, a constructive early-theme profile."
    if saturation >= 80:
        return f"{theme_name} narrative is widely saturated; monitor bubble risk and crowding."
    if strength >= 65:
        return f"{theme_name} narrative remains institutionally relevant with steady market attention."
    return f"{theme_name} narrative is present but not yet dominant in available market news."
