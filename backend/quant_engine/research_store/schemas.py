from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

LifecycleState = Literal["cold_start", "warming", "partial_live", "live", "degraded", "recovery"]
ForecastHorizon = Literal["1w", "1m", "3m"]


@dataclass(frozen=True)
class FeatureStoreStatus:
    available: bool
    status: str
    lifecycle_state: LifecycleState
    feature_store_dir: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeFeatureRow:
    theme: str
    category: str
    etf_proxy: str
    representative_symbols: list[str]
    return_5d: float | None
    return_20d: float | None
    return_60d: float | None
    return_120d: float | None
    relative_strength_spy: float | None
    relative_strength_qqq: float | None
    ma_slope: float | None
    breakout_distance: float | None
    trend_consistency: float | None
    price_above_ma20_pct: float | None
    price_above_ma50_pct: float | None
    volume_z_score: float | None
    participation: float | None
    accumulation: float | None
    realized_volatility: float | None
    downside_volatility: float | None
    drawdown: float | None
    volatility_compression: float | None
    breadth_20ma: float | None
    breadth_50ma: float | None
    constituent_participation: float | None
    average_constituent_alpha: float | None
    overextension: float | None
    acceleration: float | None
    crowding_risk: float | None
    regime_risk_on: float | None
    regime_growth_leadership: float | None
    observations: int
    lifecycle_state: LifecycleState = "partial_live"
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeForecastRecord:
    theme: str
    forecast_horizon: ForecastHorizon
    forecast_score: float | None
    expected_excess_return: float | None
    outperformance_probability: float | None
    confidence: float
    lifecycle_state: LifecycleState
    risk_state: str
    crowding_state: str
    forecast_label: str
    explanation: str
    top_positive_drivers: list[str] = field(default_factory=list)
    top_negative_drivers: list[str] = field(default_factory=list)
    regime_context: dict[str, Any] = field(default_factory=dict)
    feature_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationSummary:
    horizon: ForecastHorizon
    status: str
    lifecycle_state: LifecycleState
    observations: int
    hit_rate: float | None
    precision_at_5: float | None
    information_ratio: float | None
    max_drawdown: float | None
    calibration_quality: float | None
    turnover: float | None
    excess_return_stability: float | None
    confusion_matrix: dict[str, dict[str, int]]
    walk_forward: dict[str, Any]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
