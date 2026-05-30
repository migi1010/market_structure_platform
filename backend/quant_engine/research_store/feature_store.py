from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from alpha_engine.scoring import bounded_score
from quant_engine.data_pipeline import get_history
from settings import get_settings
from theme_engine.theme_detector import ThemeDefinition, get_theme_definitions

from .schemas import FeatureStoreStatus, ThemeFeatureRow


class LocalFeatureStore:
    def __init__(self, root: Path | None = None) -> None:
        settings = get_settings()
        self.root = root or settings.miji_feature_store_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def status(self) -> FeatureStoreStatus:
        settings = get_settings()
        enabled = settings.miji_runtime_mode == "local_full" or settings.miji_enable_feature_store
        return FeatureStoreStatus(
            available=enabled,
            status="live" if enabled else "disabled",
            lifecycle_state="partial_live" if enabled else "warming",
            feature_store_dir=str(self.root),
            message="Local feature store enabled." if enabled else "Feature store disabled outside local_full mode.",
        )

    def build_theme_features(self, limit: int | None = None) -> list[ThemeFeatureRow]:
        themes = list(get_theme_definitions())
        if limit:
            themes = themes[:limit]
        spy = _history("SPY")
        qqq = _history("QQQ")
        rows = [self._theme_row(theme, spy, qqq) for theme in themes]
        self.persist_rows(rows, "theme_features_latest")
        return rows

    def persist_rows(self, rows: list[ThemeFeatureRow], name: str) -> None:
        data = [row.to_dict() for row in rows]
        if not data:
            return
        frame = pd.DataFrame(data)
        try:
            frame.to_parquet(self.root / f"{name}.parquet", index=False)
        except Exception:
            frame.to_csv(self.root / f"{name}.csv", index=False)

    def _theme_row(self, theme: ThemeDefinition, spy: pd.DataFrame, qqq: pd.DataFrame) -> ThemeFeatureRow:
        generated_at = datetime.now(timezone.utc).isoformat()
        symbols = _ordered_symbols(theme)
        histories = {symbol: _history(symbol) for symbol in symbols[:10]}
        proxy_symbol = theme.etf_symbols[0] if theme.etf_symbols else symbols[0]
        proxy_history = histories.get(proxy_symbol) if proxy_symbol in histories else _history(proxy_symbol)
        proxy_close = _close(proxy_history)
        spy_close = _close(spy)
        qqq_close = _close(qqq)
        returns = {period: _period_return(proxy_close, period) for period in (5, 20, 60, 120)}
        constituent_rows = [_symbol_features(history) for history in histories.values()]
        valid_constituents = [row for row in constituent_rows if row["available"]]
        breadth_20 = _average(row["above_ma20"] for row in valid_constituents)
        breadth_50 = _average(row["above_ma50"] for row in valid_constituents)
        avg_alpha = _average(row["alpha"] for row in valid_constituents)
        participation = _average(row["participation"] for row in valid_constituents)
        acceleration = _safe_sub(returns[20], _safe_div(returns[60], 3.0))
        overextension = _overextension(proxy_close)
        crowding = bounded_score((overextension or 0.0) * 0.55 + max(0.0, acceleration or 0.0) * 230.0)
        observations = len(proxy_close)
        return ThemeFeatureRow(
            theme=theme.name,
            category=theme.category,
            etf_proxy=proxy_symbol,
            representative_symbols=symbols[:8],
            return_5d=returns[5],
            return_20d=returns[20],
            return_60d=returns[60],
            return_120d=returns[120],
            relative_strength_spy=_excess_return(proxy_close, spy_close, 60),
            relative_strength_qqq=_excess_return(proxy_close, qqq_close, 60),
            ma_slope=_ma_slope(proxy_close, 20),
            breakout_distance=_breakout_distance(proxy_close, 60),
            trend_consistency=_trend_consistency(proxy_close),
            price_above_ma20_pct=breadth_20,
            price_above_ma50_pct=breadth_50,
            volume_z_score=_volume_z(proxy_history),
            participation=participation,
            accumulation=_accumulation(proxy_history),
            realized_volatility=_realized_vol(proxy_close),
            downside_volatility=_downside_vol(proxy_close),
            drawdown=_drawdown(proxy_close),
            volatility_compression=_volatility_compression(proxy_close),
            breadth_20ma=breadth_20,
            breadth_50ma=breadth_50,
            constituent_participation=participation,
            average_constituent_alpha=avg_alpha,
            overextension=overextension,
            acceleration=acceleration,
            crowding_risk=crowding,
            regime_risk_on=_period_return(spy_close, 60),
            regime_growth_leadership=_excess_return(qqq_close, spy_close, 60),
            observations=observations,
            lifecycle_state="live" if observations >= 60 and valid_constituents else "partial_live",
            generated_at=generated_at,
        )


def _history(symbol: str) -> pd.DataFrame:
    try:
        return get_history(symbol, "3mo")
    except Exception:
        return pd.DataFrame()


def _ordered_symbols(theme: ThemeDefinition) -> list[str]:
    symbols = list(theme.etf_symbols) + list(theme.tickers)
    for bucket in theme.supply_chain.values():
        symbols.extend(bucket)
    result: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result or ["SPY"]


def _close(history: pd.DataFrame) -> list[float]:
    if history is None or history.empty or "Close" not in history:
        return []
    return [_finite(value) for value in history["Close"].tolist() if _finite(value) is not None]


def _volume(history: pd.DataFrame) -> list[float]:
    if history is None or history.empty or "Volume" not in history:
        return []
    return [_finite(value) for value in history["Volume"].tolist() if _finite(value) is not None and _finite(value) > 0]


def _symbol_features(history: pd.DataFrame) -> dict[str, Any]:
    close = _close(history)
    alpha = _score_return(_period_return(close, 60))
    return {
        "available": len(close) >= 20,
        "above_ma20": 100.0 if _above_ma(close, 20) else 0.0,
        "above_ma50": 100.0 if _above_ma(close, 50) else 0.0,
        "alpha": alpha,
        "participation": _participation(history),
    }


def _period_return(close: list[float], period: int) -> float | None:
    if len(close) <= period or close[-period - 1] <= 0:
        return None
    return close[-1] / close[-period - 1] - 1.0


def _excess_return(left: list[float], right: list[float], period: int) -> float | None:
    left_ret = _period_return(left, period)
    right_ret = _period_return(right, period)
    if left_ret is None or right_ret is None:
        return None
    return left_ret - right_ret


def _ma_slope(close: list[float], period: int) -> float | None:
    if len(close) < period * 2:
        return None
    recent = sum(close[-period:]) / period
    previous = sum(close[-period * 2:-period]) / period
    return recent / previous - 1.0 if previous > 0 else None


def _breakout_distance(close: list[float], period: int) -> float | None:
    if len(close) < period:
        return None
    high = max(close[-period:])
    return close[-1] / high - 1.0 if high > 0 else None


def _trend_consistency(close: list[float]) -> float | None:
    if len(close) < 22:
        return None
    positives = sum(1 for idx in range(len(close) - 20, len(close)) if close[idx] > close[idx - 1])
    return positives / 20.0


def _participation(history: pd.DataFrame) -> float | None:
    volumes = _volume(history)
    if len(volumes) < 20:
        return None
    baseline = sum(volumes[-20:]) / 20.0
    return volumes[-1] / baseline if baseline > 0 else None


def _volume_z(history: pd.DataFrame) -> float | None:
    volumes = _volume(history)
    if len(volumes) < 21:
        return None
    window = volumes[-21:-1]
    mean = sum(window) / len(window)
    variance = sum((value - mean) ** 2 for value in window) / max(len(window) - 1, 1)
    std = math.sqrt(variance)
    return (volumes[-1] - mean) / std if std > 0 else 0.0


def _accumulation(history: pd.DataFrame) -> float | None:
    close = _close(history)
    volumes = _volume(history)
    if len(close) < 21 or len(volumes) < 21:
        return None
    up_volume = sum(volumes[-20:][idx] for idx in range(20) if close[-20:][idx] >= close[-21:-1][idx])
    total = sum(volumes[-20:])
    return up_volume / total if total > 0 else None


def _realized_vol(close: list[float]) -> float | None:
    returns = _returns(close)
    if len(returns) < 20:
        return None
    mean = sum(returns[-60:]) / len(returns[-60:])
    variance = sum((value - mean) ** 2 for value in returns[-60:]) / max(len(returns[-60:]) - 1, 1)
    return math.sqrt(max(variance, 0.0)) * math.sqrt(252.0)


def _downside_vol(close: list[float]) -> float | None:
    returns = [value for value in _returns(close)[-60:] if value < 0]
    if len(returns) < 5:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(len(returns) - 1, 1)
    return math.sqrt(max(variance, 0.0)) * math.sqrt(252.0)


def _drawdown(close: list[float]) -> float | None:
    if len(close) < 20:
        return None
    high = max(close[-60:])
    return close[-1] / high - 1.0 if high > 0 else None


def _volatility_compression(close: list[float]) -> float | None:
    returns = _returns(close)
    if len(returns) < 40:
        return None
    recent = _std(returns[-20:])
    prior = _std(returns[-40:-20])
    return 1.0 - recent / prior if prior > 0 else None


def _overextension(close: list[float]) -> float | None:
    breakout = _breakout_distance(close, 60)
    ret20 = _period_return(close, 20)
    if breakout is None and ret20 is None:
        return None
    return bounded_score(max(0.0, (breakout or 0.0)) * 280.0 + max(0.0, (ret20 or 0.0)) * 180.0)


def _returns(close: list[float]) -> list[float]:
    return [close[idx] / close[idx - 1] - 1.0 for idx in range(1, len(close)) if close[idx - 1] > 0]


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _average(values: Any) -> float | None:
    usable = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return sum(usable) / len(usable) if usable else None


def _score_return(value: float | None) -> float | None:
    return bounded_score(50.0 + value * 170.0) if value is not None else None


def _above_ma(close: list[float], period: int) -> bool:
    return len(close) >= period and close[-1] >= sum(close[-period:]) / period


def _finite(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_div(value: float | None, divisor: float) -> float | None:
    return value / divisor if value is not None and divisor else None


def _safe_sub(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right
