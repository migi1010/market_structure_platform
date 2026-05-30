# Phase 6.0 Local Full-Power Quant + Theme Forecast AI Design

## Goal

Build a parallel `local_full` research subsystem for MIJI Terminal that supports theme trend forecasting, sector rotation prediction, macro regime overlays, explainable forecast ranking, walk-forward validation, and LEAN signal export without destabilizing the existing Render-safe API.

## Architectural Principle

Phase 6.0 does not replace the current `/stock`, `/alpha/top`, `/sector/rotation`, or quote pipeline. It adds a local-first research layer beside them. Default runtime remains `render_safe`; local research behavior only activates when `MIJI_RUNTIME_MODE=local_full` or explicit local feature flags are enabled.

## Runtime Modes

- `render_safe`: current production behavior, lightweight by default, heavy systems disabled.
- `local_full`: local workstation behavior, persistent research store enabled, theme forecasts enabled, heavy alpha/regime allowed when dependencies are installed.

Settings added:

- `MIJI_RUNTIME_MODE`
- `MIJI_ENABLE_THEME_FORECAST`
- `MIJI_ENABLE_LEAN`
- `MIJI_ENABLE_BACKGROUND_JOBS`
- `MIJI_ENABLE_FEATURE_STORE`
- `MIJI_FEATURE_STORE_DIR`

## System Of Record

The research store is the source of truth for Phase 6 research artifacts:

- prices and returns
- theme definitions and constituent maps
- factor features
- forecast snapshots
- validation snapshots
- LEAN signal exports

Initial persistence is local filesystem + parquet when available, with CSV fallback. This keeps the system usable before Redis/PostgreSQL are mandatory. Docker can add Redis/PostgreSQL without changing the forecast interfaces.

## Feature Store

The feature store computes and persists theme-level research features:

- 5d, 20d, 60d, 120d returns
- relative strength versus SPY and QQQ
- relative strength versus sector/theme proxy
- MA slope and trend consistency
- breakout distance and moving-average confirmation
- volume participation and volume z-score
- realized volatility, downside volatility, drawdown
- breadth above 20MA and 50MA
- constituent participation and average constituent alpha
- crowding through overextension and acceleration
- regime context through risk-on/risk-off and growth/defensive rotation proxies

All features are timestamped. Target construction must use shifted future returns only.

## Forecast Engine

The theme forecast engine outputs forecasts for:

- 1 week
- 1 month
- 3 months

Forecasts predict future excess return versus SPY and classify themes into:

- Emerging
- Leadership
- Accelerating
- Neutral
- Weakening
- Crowded
- Defensive

Forecast output shape:

```json
{
  "theme": "AI Infrastructure",
  "forecast_horizon": "1m",
  "forecast_score": 76.4,
  "expected_excess_return": 0.034,
  "outperformance_probability": 0.68,
  "confidence": 72.0,
  "lifecycle_state": "live",
  "risk_state": "balanced",
  "crowding_state": "moderate",
  "explanation": "AI Infrastructure has broad relative strength with supportive regime context.",
  "top_positive_drivers": ["relative_strength_spy", "breadth_20ma"],
  "top_negative_drivers": ["crowding"],
  "regime_context": {"risk_on_off": "Risk-On"}
}
```

## Model Layer

Phase 6.0 starts with a deterministic, explainable ensemble:

1. Rule-based factor composite.
2. Logistic regression when `sklearn` is installed and enough samples exist.
3. RandomForest when `sklearn` is installed and enough samples exist.
4. XGBoost/LightGBM adapters as optional local-only modules.
5. HMM regime overlay when `hmmlearn` is installed and enabled.
6. Ensemble ranking combines model probability, factor composite, and regime alignment.

No deep learning in Phase 6.0.

## No Lookahead Bias

Validation and training must use:

- chronological splits
- expanding windows
- forecast targets shifted forward by horizon
- no random shuffle
- no target fields inside feature columns

Any validation endpoint must report the window sizes, horizons, and cutoff dates.

## Validation Engine

Walk-forward validation computes:

- hit rate
- precision@top5
- information ratio
- max drawdown
- calibration quality
- confusion matrix
- turnover
- excess return stability

When there is insufficient history, validation returns `partial_data` with explicit reasons.

## Regime Engine

Local full mode can use HMM and heavier macro proxies. The Phase 6 forecast engine consumes regime context but does not make forecasts black-box. Regime overlays must appear in forecast explanations and driver lists.

## LEAN Integration Boundary

Create:

- `LeanSignalExporter`
- `LeanInsightAdapter`
- `LeanBacktestRunner`

Phase 6.0 exports forecast signals as LEAN-style Insight JSON. It does not enable live brokerage execution.

## API Surface

New endpoints:

- `GET /theme/forecast?horizon=1m`
- `GET /theme/forecast/validation?horizon=1m`
- `GET /theme/forecast/status`
- `GET /lean/insights?horizon=1m`

Render-safe defaults:

- If forecast mode is disabled, endpoints return `available=false`, `status=disabled`, and do not call heavy systems.
- Existing endpoints are unchanged.

## Frontend Surface

Add `Theme Forecast AI` as a terminal module. Page sections:

- Top Future Themes
- Emerging Themes
- Weakening Themes
- Crowded Themes
- Defensive Rotation
- Forecast Horizon Toggle
- Regime Context
- Driver Explanation
- Validation Performance

The UI displays finite forecast data when available and honest lifecycle states when not.

## Docker Structure

Phase 6.0 docker-compose should support:

- frontend
- backend
- redis
- postgres
- lean placeholder/service boundary

The app remains runnable without Docker for local development.

## Non-Goals

- No live brokerage execution.
- No replacement of Render-safe endpoints.
- No deep learning.
- No hidden black-box forecasts.
- No random-shuffle validation.
