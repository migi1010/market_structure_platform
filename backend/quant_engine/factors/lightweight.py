from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable, Mapping

from alpha_engine.scoring import bounded_score, confidence_label
from quant_engine.data_pipeline import get_history
from quant_engine.factors.factor_registry import FactorResult

MAX_HISTORY_PERIOD = "3mo"


@dataclass(frozen=True)
class LightweightSnapshot:
    symbol: str
    closes: tuple[float, ...]
    volumes: tuple[float, ...]

    @property
    def available(self) -> bool:
        return len(self.closes) >= 22


def score_symbol(symbol: str, spy: LightweightSnapshot | None = None, qqq: LightweightSnapshot | None = None) -> dict[str, Any]:
    normalized = symbol.strip().upper()
    snapshot = get_lightweight_snapshot(normalized)
    spy_snapshot = spy or get_lightweight_snapshot("SPY")
    qqq_snapshot = qqq or get_lightweight_snapshot("QQQ")
    factors = compute_lightweight_factors(snapshot, spy_snapshot, qqq_snapshot)
    finite = [factor for factor in factors if factor.score is not None]
    if not finite:
        return {
            "symbol": normalized,
            "available": False,
            "alpha_score": None,
            "confidence_score": 0.0,
            "confidence_label": "Unavailable",
            "lifecycle_state": "partial_live",
            "status": "partial_data",
            "factors": [factor.to_dict() for factor in factors],
            "explanation": "Lightweight factor score unavailable until recent history is cached.",
        }

    weights = {
        "momentum_20d": 0.15,
        "momentum_60d": 0.18,
        "relative_strength_spy": 0.16,
        "relative_strength_qqq": 0.12,
        "volatility_quality": 0.11,
        "volume_participation": 0.10,
        "drawdown_pressure": 0.09,
        "trend_consistency": 0.09,
    }
    total_weight = sum(weights.get(factor.factor_id, 0.0) for factor in finite) or 1.0
    alpha_score = bounded_score(sum(float(factor.score) * weights.get(factor.factor_id, 0.0) for factor in finite) / total_weight)
    completeness = total_weight / sum(weights.values())
    confidence = bounded_score(sum(factor.confidence for factor in finite) / len(finite) * completeness)
    return {
        "symbol": normalized,
        "available": True,
        "alpha_score": alpha_score,
        "momentum_20d": _factor_score(factors, "momentum_20d"),
        "momentum_60d": _factor_score(factors, "momentum_60d"),
        "momentum_strength": _factor_score(factors, "momentum_60d"),
        "relative_strength_spy": _factor_score(factors, "relative_strength_spy"),
        "relative_strength_qqq": _factor_score(factors, "relative_strength_qqq"),
        "volatility_quality": _factor_score(factors, "volatility_quality"),
        "volume_participation": _factor_score(factors, "volume_participation"),
        "drawdown_pressure": _factor_score(factors, "drawdown_pressure"),
        "trend_consistency": _factor_score(factors, "trend_consistency"),
        "confidence_score": confidence,
        "confidence_label": confidence_label(confidence),
        "lifecycle_state": "live" if confidence >= 62.0 else "partial_live",
        "status": "live" if confidence >= 62.0 else "partial_data",
        "factors": [factor.to_dict() for factor in factors],
        "explanation": _explain_score(normalized, alpha_score, factors),
    }


def score_symbols(symbols: Iterable[str], limit: int = 10) -> list[dict[str, Any]]:
    unique = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))[:limit]
    spy = get_lightweight_snapshot("SPY")
    qqq = get_lightweight_snapshot("QQQ")
    return [score_symbol(symbol, spy=spy, qqq=qqq) for symbol in unique]


def score_basket(symbols: Iterable[str], benchmark: str = "SPY", limit: int = 8) -> dict[str, Any]:
    rows = score_symbols(symbols, limit=limit)
    usable = [row for row in rows if row.get("alpha_score") is not None]
    if not usable:
        return {
            "available": False,
            "score": None,
            "confidence_score": 0.0,
            "participation_score": None,
            "relative_strength": None,
            "volume_participation": None,
            "volatility_quality": None,
            "leaders": rows,
        }
    positive = [row for row in usable if float(row.get("momentum_strength") or 0.0) >= 52.0]
    return {
        "available": True,
        "score": _average(row.get("alpha_score") for row in usable),
        "confidence_score": _average(row.get("confidence_score") for row in usable),
        "participation_score": bounded_score(len(positive) / max(len(usable), 1) * 100.0),
        "relative_strength": _average(row.get("relative_strength_spy" if benchmark == "SPY" else "relative_strength_qqq") for row in usable),
        "volume_participation": _average(row.get("volume_participation") for row in usable),
        "volatility_quality": _average(row.get("volatility_quality") for row in usable),
        "leaders": sorted(usable, key=lambda row: float(row.get("alpha_score") or -1.0), reverse=True),
    }


def compute_lightweight_factors(snapshot: LightweightSnapshot, spy: LightweightSnapshot, qqq: LightweightSnapshot) -> list[FactorResult]:
    return [
        _momentum_factor(snapshot, 20, "momentum_20d"),
        _momentum_factor(snapshot, 60, "momentum_60d"),
        _relative_strength_factor(snapshot, spy, "relative_strength_spy"),
        _relative_strength_factor(snapshot, qqq, "relative_strength_qqq"),
        _volatility_quality_factor(snapshot),
        _volume_participation_factor(snapshot),
        _drawdown_pressure_factor(snapshot),
        _trend_consistency_factor(snapshot),
    ]


@lru_cache(maxsize=256)
def get_lightweight_snapshot(symbol: str) -> LightweightSnapshot:
    normalized = symbol.strip().upper()
    try:
        history = get_history(normalized, MAX_HISTORY_PERIOD)
    except Exception:
        history = None
    closes: list[float] = []
    volumes: list[float] = []
    if history is not None and not getattr(history, "empty", True):
        if "Close" in history:
            closes = _finite_series(history["Close"].tail(65).tolist())
        if "Volume" in history:
            volumes = _finite_series(history["Volume"].tail(65).tolist(), positive_only=True)
    return LightweightSnapshot(normalized, tuple(closes), tuple(volumes))


def _momentum_factor(snapshot: LightweightSnapshot, periods: int, factor_id: str) -> FactorResult:
    ret = _period_return(snapshot.closes, periods)
    if ret is None:
        return _partial(factor_id, "Momentum unavailable until enough recent close history is cached.")
    score = bounded_score(50.0 + ret * (190.0 if periods <= 20 else 145.0))
    confidence = 70.0 if len(snapshot.closes) > periods else 45.0
    return _result(factor_id, score, confidence, "Recent price momentum from 3-month close history.")


def _relative_strength_factor(snapshot: LightweightSnapshot, benchmark: LightweightSnapshot, factor_id: str) -> FactorResult:
    ret = _period_return(snapshot.closes, 60)
    bench = _period_return(benchmark.closes, 60)
    if ret is None or bench is None:
        return _partial(factor_id, "Relative strength unavailable until symbol and benchmark history are cached.")
    score = bounded_score(50.0 + (ret - bench) * 180.0)
    return _result(factor_id, score, 64.0, f"60-day return spread versus {benchmark.symbol}.")


def _volatility_quality_factor(snapshot: LightweightSnapshot) -> FactorResult:
    returns = _returns(snapshot.closes)
    if len(returns) < 20:
        return _partial("volatility_quality", "Volatility quality unavailable until enough daily returns are cached.")
    window = returns[-60:]
    mean = sum(window) / len(window)
    variance = sum((value - mean) ** 2 for value in window) / max(len(window) - 1, 1)
    annualized = math.sqrt(max(variance, 0.0)) * math.sqrt(252.0)
    score = bounded_score(100.0 - annualized * 145.0)
    return _result("volatility_quality", score, 62.0, "Lower realized volatility receives higher quality score.")


def _volume_participation_factor(snapshot: LightweightSnapshot) -> FactorResult:
    if len(snapshot.volumes) < 21:
        return _partial("volume_participation", "Volume participation unavailable until recent volume history is cached.")
    recent = snapshot.volumes[-1]
    baseline = sum(snapshot.volumes[-20:]) / 20.0
    relative = recent / max(baseline, 1.0)
    score = bounded_score(50.0 + (relative - 1.0) * 28.0)
    return _result("volume_participation", score, 58.0, "Latest volume compared with 20-day average volume.")


def _drawdown_pressure_factor(snapshot: LightweightSnapshot) -> FactorResult:
    if len(snapshot.closes) < 22:
        return _partial("drawdown_pressure", "Drawdown pressure unavailable until enough close history is cached.")
    high = max(snapshot.closes[-60:])
    drawdown = snapshot.closes[-1] / high - 1.0 if high > 0 else 0.0
    score = bounded_score(100.0 + drawdown * 260.0)
    return _result("drawdown_pressure", score, 60.0, "Score penalizes distance from recent 3-month highs.")


def _trend_consistency_factor(snapshot: LightweightSnapshot) -> FactorResult:
    returns = _returns(snapshot.closes)
    if len(returns) < 20:
        return _partial("trend_consistency", "Trend consistency unavailable until enough daily returns are cached.")
    positive = sum(1 for value in returns[-20:] if value > 0.0)
    sma = sum(snapshot.closes[-20:]) / 20.0
    above_sma_bonus = 10.0 if snapshot.closes[-1] >= sma else -8.0
    score = bounded_score(positive / 20.0 * 100.0 + above_sma_bonus)
    return _result("trend_consistency", score, 58.0, "Breadth of positive days plus 20-day trend confirmation.")


def _period_return(closes: tuple[float, ...], periods: int) -> float | None:
    if len(closes) <= periods or closes[-periods - 1] <= 0.0:
        return None
    return closes[-1] / closes[-periods - 1] - 1.0


def _returns(closes: tuple[float, ...]) -> list[float]:
    return [closes[index] / closes[index - 1] - 1.0 for index in range(1, len(closes)) if closes[index - 1] > 0.0]


def _finite_series(values: Iterable[Any], positive_only: bool = True) -> list[float]:
    result: list[float] = []
    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(parsed):
            continue
        if positive_only and parsed <= 0.0:
            continue
        result.append(parsed)
    return result


def _result(factor_id: str, score: float, confidence: float, explanation: str) -> FactorResult:
    return FactorResult(factor_id, bounded_score(score), bounded_score(confidence), "live", "cached_3mo_history", "live", explanation, "live")


def _partial(factor_id: str, explanation: str) -> FactorResult:
    return FactorResult(factor_id, None, 0.0, "partial_data", "cached_3mo_history", "partial", explanation, "partial_live")


def _factor_score(factors: Iterable[FactorResult], factor_id: str) -> float | None:
    for factor in factors:
        if factor.factor_id == factor_id:
            return factor.score
    return None


def _average(values: Iterable[Any]) -> float | None:
    finite: list[float] = []
    for value in values:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed):
            finite.append(parsed)
    return bounded_score(sum(finite) / len(finite)) if finite else None


def _explain_score(symbol: str, score: float, factors: Iterable[FactorResult]) -> str:
    by_id = {factor.factor_id: factor.score for factor in factors}
    if score >= 65.0:
        return f"{symbol} leadership strengthened by momentum and relative strength factors."
    if score <= 42.0:
        return f"{symbol} lightweight alpha is weak due to trend or drawdown pressure."
    if (by_id.get("volume_participation") or 0.0) >= 60.0:
        return f"{symbol} is neutral-to-positive with elevated volume participation."
    return f"{symbol} lightweight alpha is balanced with mixed factor confirmation."
