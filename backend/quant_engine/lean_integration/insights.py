from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

ForecastHorizon = Literal["1w", "1m", "3m"]
HORIZON_DAYS = {"1w": 7, "1m": 30, "3m": 90}


class LeanInsightAdapter:
    def to_insight(self, forecast: dict[str, Any]) -> dict[str, Any]:
        score = forecast.get("forecast_score")
        direction = "Up" if isinstance(score, (int, float)) and score >= 55 else "Down" if isinstance(score, (int, float)) and score <= 45 else "Flat"
        horizon = str(forecast.get("forecast_horizon") or "1m")
        return {
            "type": "Price",
            "symbol": forecast.get("theme"),
            "source_model": "MIJI.ThemeForecastAI",
            "direction": direction,
            "period_days": HORIZON_DAYS.get(horizon, 30),
            "magnitude": forecast.get("expected_excess_return"),
            "confidence": forecast.get("confidence"),
            "generated_time_utc": datetime.now(timezone.utc).isoformat(),
            "weight": _weight(score),
            "metadata": {
                "forecast_label": forecast.get("forecast_label"),
                "risk_state": forecast.get("risk_state"),
                "crowding_state": forecast.get("crowding_state"),
                "top_positive_drivers": forecast.get("top_positive_drivers") or [],
                "top_negative_drivers": forecast.get("top_negative_drivers") or [],
                "live_brokerage_execution": False,
            },
        }


class LeanSignalExporter:
    def export(self, forecasts: list[dict[str, Any]]) -> dict[str, Any]:
        adapter = LeanInsightAdapter()
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "live" if forecasts else "partial_data",
            "live_brokerage_execution": False,
            "insights": [adapter.to_insight(forecast) for forecast in forecasts],
        }


class LeanBacktestRunner:
    def build_command(self, project: str = "MijiThemeForecast") -> list[str]:
        return ["lean", "backtest", project]

    def run(self, project: str = "MijiThemeForecast") -> dict[str, Any]:
        return {
            "status": "not_started",
            "live_brokerage_execution": False,
            "command": self.build_command(project),
            "message": "LEAN backtest boundary prepared. Run manually in local_full mode.",
        }


def _weight(score: Any) -> float | None:
    if not isinstance(score, (int, float)):
        return None
    centered = (float(score) - 50.0) / 50.0
    return max(-1.0, min(1.0, centered))
