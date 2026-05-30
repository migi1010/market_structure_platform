from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Iterable, Literal, Mapping

from alpha_engine.scoring import bounded_score, confidence_label

FactorCategory = Literal[
    "momentum",
    "quality",
    "valuation",
    "volatility",
    "liquidity",
    "macro",
    "regime",
    "theme",
    "smart_money",
    "earnings_quality",
]
FactorStatus = Literal["live", "stale", "partial_data", "unavailable", "disabled", "error"]
LifecycleState = Literal["cold_start", "warming", "partial_live", "live", "degraded", "recovery"]
FactorFreshness = Literal["live", "stale", "partial"]

FactorCompute = Callable[["FactorContext"], "FactorResult"]


@dataclass(frozen=True)
class FactorContext:
    symbol: str | None = None
    quote: Mapping[str, Any] = field(default_factory=dict)
    history: Any = None
    benchmark_history: Any = None
    sector_rows: Iterable[Mapping[str, Any]] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    lifecycle_state: LifecycleState = "partial_live"


@dataclass(frozen=True)
class FactorResult:
    factor_id: str
    score: float | None
    confidence: float
    status: FactorStatus
    source: str
    freshness: FactorFreshness
    explanation: str
    lifecycle_state: LifecycleState

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "score": self.score,
            "confidence": self.confidence,
            "status": self.status,
            "source": self.source,
            "freshness": self.freshness,
            "explanation": self.explanation,
            "lifecycle_state": self.lifecycle_state,
        }


@dataclass(frozen=True)
class FactorDefinition:
    id: str
    name: str
    category: FactorCategory
    description: str
    dependencies: tuple[str, ...]
    compute: FactorCompute
    cache_ttl: int
    lifecycle_state: LifecycleState = "partial_live"
    confidence: float = 0.0
    lightweight: bool = True
    heavy: bool = False
    enabled: bool = True
    render_safe: bool = True
    weight: float = 1.0
    env_flag: str | None = None

    def is_enabled(self, include_heavy: bool = False) -> bool:
        if not self.enabled:
            return False
        if self.heavy and not include_heavy:
            return False
        if self.env_flag and not _env_enabled(self.env_flag):
            return False
        if not self.render_safe and not include_heavy:
            return False
        return True


@dataclass(frozen=True)
class FactorPipelineResult:
    factors: list[FactorResult]
    score: float | None
    confidence: float
    status: FactorStatus
    lifecycle_state: LifecycleState
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "confidence": self.confidence,
            "confidence_label": confidence_label(self.confidence),
            "status": self.status,
            "lifecycle_state": self.lifecycle_state,
            "explanation": self.explanation,
            "factors": [factor.to_dict() for factor in self.factors],
        }


class FactorRegistry:
    def __init__(self, definitions: Iterable[FactorDefinition] | None = None) -> None:
        self._definitions: dict[str, FactorDefinition] = {}
        for definition in definitions or ():
            self.register(definition)

    def register(self, definition: FactorDefinition) -> None:
        if definition.id in self._definitions:
            raise ValueError(f"duplicate factor id: {definition.id}")
        self._definitions[definition.id] = definition

    def get(self, factor_id: str) -> FactorDefinition | None:
        return self._definitions.get(factor_id)

    def all(self) -> list[FactorDefinition]:
        return list(self._definitions.values())

    def enabled(self, include_heavy: bool = False) -> list[FactorDefinition]:
        return [definition for definition in self.all() if definition.is_enabled(include_heavy=include_heavy)]


class FactorPipeline:
    def __init__(self, registry: FactorRegistry, max_concurrency: int = 1, include_heavy: bool = False) -> None:
        self.registry = registry
        self.max_concurrency = max(1, int(max_concurrency))
        self.include_heavy = include_heavy

    def run(self, context: FactorContext, factor_ids: Iterable[str] | None = None) -> FactorPipelineResult:
        definitions = self._resolve_definitions(factor_ids)
        if not definitions:
            return FactorPipelineResult([], None, 0.0, "unavailable", "warming", "No enabled factors available.")

        results = self._compute(definitions, context)
        scored = [result for result in results if result.score is not None and math.isfinite(float(result.score))]
        if not scored:
            status: FactorStatus = "partial_data" if results else "unavailable"
            lifecycle: LifecycleState = "partial_live" if results else "warming"
            return FactorPipelineResult(results, None, _average_confidence(results), status, lifecycle, "No finite factor scores available.")

        weight_by_id = {definition.id: max(definition.weight, 0.0) for definition in definitions}
        total_weight = sum(weight_by_id[result.factor_id] for result in scored) or 1.0
        score = sum(float(result.score) * weight_by_id[result.factor_id] for result in scored) / total_weight
        confidence = _average_confidence(scored)
        lifecycle = _aggregate_lifecycle(results)
        status = "live" if lifecycle == "live" else "partial_data"
        return FactorPipelineResult(
            factors=results,
            score=bounded_score(score),
            confidence=bounded_score(confidence),
            status=status,
            lifecycle_state=lifecycle,
            explanation=f"{len(scored)} of {len(results)} factors produced finite scores.",
        )

    def _resolve_definitions(self, factor_ids: Iterable[str] | None) -> list[FactorDefinition]:
        enabled = self.registry.enabled(include_heavy=self.include_heavy)
        if factor_ids is None:
            requested = enabled
        else:
            enabled_by_id = {definition.id: definition for definition in enabled}
            requested = [enabled_by_id[factor_id] for factor_id in factor_ids if factor_id in enabled_by_id]
        resolved: list[FactorDefinition] = []
        available: set[str] = set()
        pending = list(requested)
        while pending:
            progressed = False
            for definition in list(pending):
                if all(dependency in available for dependency in definition.dependencies):
                    resolved.append(definition)
                    available.add(definition.id)
                    pending.remove(definition)
                    progressed = True
            if not progressed:
                break
        return resolved

    def _compute(self, definitions: list[FactorDefinition], context: FactorContext) -> list[FactorResult]:
        return [_safe_compute(definition, context) for definition in definitions]


def build_default_factor_registry() -> FactorRegistry:
    registry = FactorRegistry()
    for definition in (
        FactorDefinition(
            id="simple_momentum",
            name="Simple Momentum",
            category="momentum",
            description="1-month and 3-month price momentum from cached OHLCV history.",
            dependencies=(),
            compute=_simple_momentum_factor,
            cache_ttl=900,
            confidence=55.0,
            weight=1.0,
        ),
        FactorDefinition(
            id="relative_strength",
            name="Relative Strength",
            category="momentum",
            description="Symbol return relative to benchmark return.",
            dependencies=(),
            compute=_relative_strength_factor,
            cache_ttl=900,
            confidence=55.0,
            weight=1.0,
        ),
        FactorDefinition(
            id="volatility_snapshot",
            name="Volatility Snapshot",
            category="volatility",
            description="Annualized realized volatility transformed into a stability score.",
            dependencies=(),
            compute=_volatility_factor,
            cache_ttl=900,
            confidence=50.0,
            weight=0.7,
        ),
        FactorDefinition(
            id="volume_anomaly",
            name="Volume Anomaly",
            category="liquidity",
            description="Latest volume compared with the recent rolling average.",
            dependencies=(),
            compute=_volume_anomaly_factor,
            cache_ttl=900,
            confidence=50.0,
            weight=0.8,
        ),
        FactorDefinition(
            id="smart_money_partial",
            name="Smart Money Partial Proxy",
            category="smart_money",
            description="Lightweight price-volume proxy while institutional flow models are calibrating.",
            dependencies=(),
            compute=_smart_money_partial_factor,
            cache_ttl=900,
            confidence=35.0,
            weight=0.6,
        ),
        FactorDefinition(
            id="earnings_quality_partial",
            name="Earnings Quality Partial",
            category="earnings_quality",
            description="Placeholder factor that withholds score until statement-derived quality is available.",
            dependencies=(),
            compute=_earnings_quality_partial_factor,
            cache_ttl=21600,
            confidence=0.0,
            weight=0.0,
        ),
        FactorDefinition(
            id="simple_sector_leadership",
            name="Simple Sector Leadership",
            category="theme",
            description="Uses existing sector rotation rows when supplied by the caller.",
            dependencies=(),
            compute=_simple_sector_leadership_factor,
            cache_ttl=900,
            confidence=40.0,
            weight=0.7,
        ),
        FactorDefinition(
            id="heavy_alpha158_candidate",
            name="Alpha158 Candidate Hook",
            category="quality",
            description="Future heavy Alpha158-style factor hook; disabled unless MIJI_ENABLE_HEAVY_ALPHA=true.",
            dependencies=(),
            compute=lambda context: _disabled_heavy_factor(context, "heavy_alpha158_candidate"),
            cache_ttl=1800,
            lightweight=False,
            heavy=True,
            enabled=True,
            render_safe=False,
            env_flag="MIJI_ENABLE_HEAVY_ALPHA",
            weight=0.0,
        ),
        FactorDefinition(
            id="heavy_hmm_regime_candidate",
            name="HMM Regime Candidate Hook",
            category="regime",
            description="Future HMM regime factor hook; disabled unless MIJI_ENABLE_HEAVY_REGIME=true.",
            dependencies=(),
            compute=lambda context: _disabled_heavy_factor(context, "heavy_hmm_regime_candidate"),
            cache_ttl=900,
            lightweight=False,
            heavy=True,
            enabled=True,
            render_safe=False,
            env_flag="MIJI_ENABLE_HEAVY_REGIME",
            weight=0.0,
        ),
    ):
        registry.register(definition)
    return registry


@lru_cache(maxsize=1)
def get_default_factor_registry() -> FactorRegistry:
    return build_default_factor_registry()


def _safe_compute(definition: FactorDefinition, context: FactorContext) -> FactorResult:
    if not definition.is_enabled(include_heavy=True):
        return FactorResult(
            factor_id=definition.id,
            score=None,
            confidence=0.0,
            status="disabled",
            source="factor_registry",
            freshness="partial",
            explanation=f"{definition.name} is disabled by configuration.",
            lifecycle_state="partial_live",
        )
    try:
        result = definition.compute(context)
        return _normalize_result(result, definition)
    except Exception as exc:
        return FactorResult(
            factor_id=definition.id,
            score=None,
            confidence=0.0,
            status="error",
            source="factor_registry",
            freshness="partial",
            explanation=f"{definition.name} failed safely: {exc}",
            lifecycle_state="degraded",
        )


def _normalize_result(result: FactorResult, definition: FactorDefinition) -> FactorResult:
    score = result.score
    if score is not None:
        score = bounded_score(score)
    return FactorResult(
        factor_id=result.factor_id or definition.id,
        score=score,
        confidence=bounded_score(result.confidence),
        status=result.status,
        source=result.source,
        freshness=result.freshness,
        explanation=result.explanation,
        lifecycle_state=result.lifecycle_state,
    )


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _average_confidence(results: Iterable[FactorResult]) -> float:
    values = [result.confidence for result in results]
    if not values:
        return 0.0
    return bounded_score(sum(values) / len(values))


def _aggregate_lifecycle(results: Iterable[FactorResult]) -> LifecycleState:
    states = {result.lifecycle_state for result in results}
    if not states:
        return "warming"
    if "degraded" in states:
        return "degraded"
    if "warming" in states or "partial_live" in states:
        return "partial_live"
    if states == {"live"}:
        return "live"
    return "partial_live"


def _close_values(history: Any) -> list[float]:
    if history is None or getattr(history, "empty", True) or "Close" not in history:
        return []
    values: list[float] = []
    for value in history["Close"].dropna().astype(float).tolist():
        if math.isfinite(float(value)) and float(value) > 0:
            values.append(float(value))
    return values


def _volume_values(history: Any) -> list[float]:
    if history is None or getattr(history, "empty", True) or "Volume" not in history:
        return []
    values: list[float] = []
    for value in history["Volume"].dropna().astype(float).tolist():
        if math.isfinite(float(value)) and float(value) > 0:
            values.append(float(value))
    return values


def _returns(closes: list[float]) -> list[float]:
    return [(closes[index] / closes[index - 1]) - 1.0 for index in range(1, len(closes)) if closes[index - 1] > 0]


def _period_return(closes: list[float], periods: int) -> float | None:
    if len(closes) <= periods or closes[-periods - 1] <= 0:
        return None
    return closes[-1] / closes[-periods - 1] - 1.0


def _partial_result(factor_id: str, explanation: str, confidence: float = 0.0) -> FactorResult:
    return FactorResult(
        factor_id=factor_id,
        score=None,
        confidence=confidence,
        status="partial_data",
        source="factor_registry",
        freshness="partial",
        explanation=explanation,
        lifecycle_state="partial_live",
    )


def _simple_momentum_factor(context: FactorContext) -> FactorResult:
    closes = _close_values(context.history)
    ret_1m = _period_return(closes, 21)
    ret_3m = _period_return(closes, 63)
    if ret_1m is None and ret_3m is None:
        return _partial_result("simple_momentum", "Momentum unavailable until enough history is cached.")
    score = 50.0 + (ret_1m or 0.0) * 120.0 + (ret_3m or 0.0) * 80.0
    confidence = 65.0 if len(closes) >= 64 else 42.0
    return FactorResult("simple_momentum", score, confidence, "live", "cached_history", "live", "Momentum computed from cached close history.", "live")


def _relative_strength_factor(context: FactorContext) -> FactorResult:
    closes = _close_values(context.history)
    benchmark = _close_values(context.benchmark_history)
    ret = _period_return(closes, 63)
    bench_ret = _period_return(benchmark, 63)
    if ret is None or bench_ret is None:
        return _partial_result("relative_strength", "Relative strength unavailable until symbol and benchmark history are cached.")
    score = 50.0 + (ret - bench_ret) * 150.0
    return FactorResult("relative_strength", score, 62.0, "live", "cached_history", "live", "Relative return measured versus benchmark history.", "live")


def _volatility_factor(context: FactorContext) -> FactorResult:
    closes = _close_values(context.history)
    returns = _returns(closes)
    if len(returns) < 20:
        return _partial_result("volatility_snapshot", "Volatility unavailable until enough daily returns are cached.")
    mean = sum(returns[-63:]) / len(returns[-63:])
    variance = sum((value - mean) ** 2 for value in returns[-63:]) / max(len(returns[-63:]) - 1, 1)
    annualized = math.sqrt(variance) * math.sqrt(252.0)
    score = 100.0 - annualized * 160.0
    return FactorResult("volatility_snapshot", score, 58.0, "live", "cached_history", "live", "Realized volatility converted to a stability score.", "live")


def _volume_anomaly_factor(context: FactorContext) -> FactorResult:
    volumes = _volume_values(context.history)
    if len(volumes) < 21:
        return _partial_result("volume_anomaly", "Volume anomaly unavailable until enough volume history is cached.")
    recent_avg = sum(volumes[-20:]) / 20.0
    relative_volume = volumes[-1] / max(recent_avg, 1.0)
    score = 50.0 + (relative_volume - 1.0) * 25.0
    return FactorResult("volume_anomaly", score, 55.0, "live", "cached_history", "live", "Latest volume compared with 20-day average volume.", "live")


def _smart_money_partial_factor(context: FactorContext) -> FactorResult:
    closes = _close_values(context.history)
    volumes = _volume_values(context.history)
    ret_1m = _period_return(closes, 21)
    if ret_1m is None or len(volumes) < 21:
        return _partial_result("smart_money_partial", "Smart money proxy is partial until price-volume history is available.", 20.0)
    recent_avg = sum(volumes[-20:]) / 20.0
    relative_volume = volumes[-1] / max(recent_avg, 1.0)
    score = 50.0 + ret_1m * 100.0 + (relative_volume - 1.0) * 18.0
    return FactorResult("smart_money_partial", score, 38.0, "partial_data", "lightweight_proxy", "partial", "Lightweight price-volume accumulation proxy; not institutional flow confirmation.", "partial_live")


def _earnings_quality_partial_factor(context: FactorContext) -> FactorResult:
    return _partial_result("earnings_quality_partial", "Earnings quality requires statement-derived factors and withholds a score in the lightweight registry.", 0.0)


def _simple_sector_leadership_factor(context: FactorContext) -> FactorResult:
    sector = str(context.metadata.get("sector") or "").strip().lower()
    if not sector:
        return _partial_result("simple_sector_leadership", "Sector leadership unavailable without sector metadata.", 0.0)
    for row in context.sector_rows:
        name = str(row.get("sector") or "").strip().lower()
        if name and (name == sector or name in sector or sector in name):
            score = row.get("score") or row.get("relative_strength")
            try:
                parsed = float(score)
            except (TypeError, ValueError):
                parsed = math.nan
            if math.isfinite(parsed):
                return FactorResult("simple_sector_leadership", parsed, 45.0, "partial_data", "sector_rotation_cache", "partial", "Sector leadership inherited from existing sector rotation output.", "partial_live")
    return _partial_result("simple_sector_leadership", "No matching sector rotation row supplied to factor context.", 0.0)


def _disabled_heavy_factor(context: FactorContext, factor_id: str) -> FactorResult:
    return _partial_result(factor_id, "Heavy factor hook is present but not executed in Phase 4.1.", 0.0)
