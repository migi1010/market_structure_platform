from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.regime_engine import detect_market_regime
from quant_engine.research_store import LocalFeatureStore, ThemeFeatureRow, ThemeForecastRecord
from settings import get_settings

ForecastHorizon = Literal["1w", "1m", "3m"]
HORIZON_MULTIPLIER: dict[str, float] = {"1w": 0.35, "1m": 1.0, "3m": 2.2}


def forecast_theme_leadership(horizon: ForecastHorizon = "1m", limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    if not (settings.miji_runtime_mode == "local_full" or settings.miji_enable_theme_forecast):
        return {
            "available": False,
            "status": "disabled",
            "lifecycle_state": "warming",
            "horizon": horizon,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecasts": [],
            "message": "Theme Forecast AI is disabled. Set MIJI_RUNTIME_MODE=local_full or MIJI_ENABLE_THEME_FORECAST=true.",
        }
    store = LocalFeatureStore()
    features = store.build_theme_features(limit=limit)
    regime = _safe_regime()
    forecasts = [_forecast_row(row, horizon, regime) for row in features]
    forecasts.sort(key=lambda item: item.forecast_score if item.forecast_score is not None else -1.0, reverse=True)
    payload = [item.to_dict() for item in forecasts]
    return {
        "available": bool(payload),
        "status": "live" if payload else "partial_data",
        "lifecycle_state": "live" if any(item["lifecycle_state"] == "live" for item in payload) else "partial_live",
        "horizon": horizon,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "regime_context": regime,
        "top_future_themes": payload[:5],
        "emerging_themes": [item for item in payload if item["forecast_label"] in {"Emerging", "Accelerating"}][:5],
        "weakening_themes": [item for item in payload if item["forecast_label"] == "Weakening"][:5],
        "crowded_themes": [item for item in payload if item["crowding_state"] == "crowded"][:5],
        "defensive_rotation": [item for item in payload if item["forecast_label"] == "Defensive"][:5],
        "forecasts": payload,
    }


def forecast_status() -> dict[str, Any]:
    settings = get_settings()
    store = LocalFeatureStore()
    return {
        "runtime_mode": settings.miji_runtime_mode,
        "theme_forecast_enabled": settings.miji_enable_theme_forecast or settings.miji_runtime_mode == "local_full",
        "feature_store_enabled": settings.miji_enable_feature_store or settings.miji_runtime_mode == "local_full",
        "lean_enabled": settings.miji_enable_lean,
        "heavy_alpha_enabled": settings.miji_enable_heavy_alpha,
        "heavy_regime_enabled": settings.miji_enable_heavy_regime,
        "feature_store": store.status().to_dict(),
        "live_brokerage_execution": False,
    }


def _forecast_row(row: ThemeFeatureRow, horizon: ForecastHorizon, regime: dict[str, Any]) -> ThemeForecastRecord:
    drivers = _driver_scores(row, regime)
    score = bounded_score(50.0 + sum(drivers.values()))
    multiplier = HORIZON_MULTIPLIER[horizon]
    expected = _expected_excess_return(row, score, multiplier)
    probability = bounded_score(50.0 + (score - 50.0) * 0.72) / 100.0
    confidence = _confidence(row)
    risk_state = _risk_state(row)
    crowding_state = _crowding_state(row)
    label = _forecast_label(score, row, regime)
    positive = [key for key, _ in sorted(drivers.items(), key=lambda item: item[1], reverse=True) if _ > 0][:5]
    negative = [key for key, _ in sorted(drivers.items(), key=lambda item: item[1]) if _ < 0][:5]
    explanation = _explain(row.theme, label, positive, negative, regime)
    return ThemeForecastRecord(
        theme=row.theme,
        forecast_horizon=horizon,
        forecast_score=round(score, 2),
        expected_excess_return=round(expected, 4) if expected is not None else None,
        outperformance_probability=round(probability, 4),
        confidence=round(confidence, 2),
        lifecycle_state=row.lifecycle_state,
        risk_state=risk_state,
        crowding_state=crowding_state,
        forecast_label=label,
        explanation=explanation,
        top_positive_drivers=positive,
        top_negative_drivers=negative,
        regime_context=regime,
        feature_snapshot=row.to_dict(),
    )


def _driver_scores(row: ThemeFeatureRow, regime: dict[str, Any]) -> dict[str, float]:
    return {
        "relative_strength_spy": _scale(row.relative_strength_spy, 120.0),
        "relative_strength_qqq": _scale(row.relative_strength_qqq, 80.0),
        "momentum_20d": _scale(row.return_20d, 90.0),
        "momentum_60d": _scale(row.return_60d, 70.0),
        "acceleration": _scale(row.acceleration, 110.0),
        "breadth_20ma": _center(row.breadth_20ma, 12.0),
        "breadth_50ma": _center(row.breadth_50ma, 8.0),
        "volume_participation": _center(row.participation * 50.0 if row.participation is not None else None, 5.0),
        "regime_risk_on": _scale(row.regime_risk_on, 40.0),
        "growth_leadership": _scale(row.regime_growth_leadership, 45.0),
        "crowding": -_center(row.crowding_risk, 10.0),
        "drawdown": _scale(row.drawdown, 65.0),
        "volatility": -_scale(row.realized_volatility, 12.0),
        "hmm_regime": 5.0 if str(regime.get("name", "")).lower().startswith(("risk-on", "bull")) else -3.0 if "risk" in str(regime.get("name", "")).lower() else 0.0,
    }


def _expected_excess_return(row: ThemeFeatureRow, score: float, multiplier: float) -> float | None:
    base = row.relative_strength_spy if row.relative_strength_spy is not None else row.return_20d
    if base is None:
        base = (score - 50.0) / 1000.0
    return base * multiplier + (score - 50.0) / 1000.0


def _confidence(row: ThemeFeatureRow) -> float:
    observed = min(row.observations / 60.0, 1.0) * 35.0
    breadth = 20.0 if row.breadth_20ma is not None else 0.0
    rs = 20.0 if row.relative_strength_spy is not None else 0.0
    risk = 15.0 if row.realized_volatility is not None else 0.0
    drivers = 10.0 if row.acceleration is not None else 0.0
    return bounded_score(observed + breadth + rs + risk + drivers)


def _forecast_label(score: float, row: ThemeFeatureRow, regime: dict[str, Any]) -> str:
    if (row.crowding_risk or 0.0) >= 75.0 and score >= 58.0:
        return "Crowded"
    if "Defensive" in str(regime.get("name") or "") and score >= 52.0:
        return "Defensive"
    if score >= 72.0:
        return "Leadership"
    if score >= 62.0 and (row.acceleration or 0.0) > 0:
        return "Accelerating"
    if score >= 57.0:
        return "Emerging"
    if score <= 42.0:
        return "Weakening"
    return "Neutral"


def _risk_state(row: ThemeFeatureRow) -> str:
    vol = row.realized_volatility or 0.0
    drawdown = row.drawdown or 0.0
    if vol >= 0.45 or drawdown <= -0.18:
        return "elevated"
    if vol <= 0.22 and drawdown > -0.06:
        return "contained"
    return "balanced"


def _crowding_state(row: ThemeFeatureRow) -> str:
    risk = row.crowding_risk or 0.0
    if risk >= 75.0:
        return "crowded"
    if risk <= 35.0:
        return "uncrowded"
    return "moderate"


def _explain(theme: str, label: str, positive: list[str], negative: list[str], regime: dict[str, Any]) -> str:
    regime_name = regime.get("name") or "unconfirmed regime"
    positive_text = ", ".join(positive[:3]) if positive else "limited positive confirmation"
    negative_text = ", ".join(negative[:2]) if negative else "no major negative driver"
    return f"{theme} is classified as {label} with {positive_text} supporting the forecast, {negative_text} as the main risk, under {regime_name}."


def _safe_regime() -> dict[str, Any]:
    try:
        return detect_market_regime()
    except Exception:
        return {"name": "Regime Unavailable", "confidence": 0.0}


def _scale(value: float | None, multiplier: float) -> float:
    return 0.0 if value is None else max(-18.0, min(18.0, value * multiplier))


def _center(value: float | None, multiplier: float) -> float:
    if value is None:
        return 0.0
    return max(-18.0, min(18.0, (value - 50.0) / 50.0 * multiplier))
