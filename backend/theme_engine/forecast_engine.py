"""forecast_engine.py — Phase 6.0B Theme Differentiation Engine.

Transforms theme scoring from a strength ranker into a differentiated
forward-looking forecast engine.  All functions here are pure or
side-effect-free except the score-history registry (module-level deque),
which intentionally persists across requests to enable stability scoring.

Public API consumed by theme_scoring.py and theme_rotation.py:
    compute_residual_strength(theme_name, raw_scores)
    compute_capital_rotation(theme_name, all_metrics)
    compute_crowding_penalty_raw(ret_1m, acceleration, relative_volume,
                                  volatility, leadership_concentration)
    compute_forecast_confidence(metrics_agreement, breadth, macro_alignment,
                                 theme_name)
    compute_horizon_scores(base_metrics, macro_state)
    percentile_rescale(scores_by_theme, target_low, target_high)
    update_score_history(theme_name, score)
    compute_forecast_stability(theme_name)
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from alpha_engine.scoring import bounded_score

# ---------------------------------------------------------------------------
# Theme hierarchy — parent / peer / downstream relationships
# ---------------------------------------------------------------------------

THEME_PARENT: Dict[str, str] = {
    # Memory sub-themes → Semiconductor parent
    "HBM":              "Semiconductor",
    "DRAM Cycle":       "Semiconductor",
    "NAND Cycle":       "Semiconductor",
    "Glass Substrate":  "Semiconductor",
    "CoWoS":            "Semiconductor",
    # AI sub-themes → AI Infrastructure parent
    "Networking":           "AI Infrastructure",
    "Data Center Cooling":  "AI Infrastructure",
    # Energy sub-themes → Electric Grid parent
    "Nuclear Energy":   "Electric Grid",
    "Cable / Copper":   "Electric Grid",
    "Utilities":        "Electric Grid",
    # Materials sub-themes → Commodities parent
    "Shipping":         "Commodities",
}

THEME_PEERS: Dict[str, List[str]] = {
    # Memory cluster
    "HBM":              ["DRAM Cycle", "NAND Cycle", "Glass Substrate", "CoWoS"],
    "DRAM Cycle":       ["HBM", "NAND Cycle", "Glass Substrate", "CoWoS"],
    "NAND Cycle":       ["HBM", "DRAM Cycle"],
    "Glass Substrate":  ["HBM", "CoWoS"],
    "CoWoS":            ["HBM", "Glass Substrate"],
    # AI cluster
    "AI Infrastructure":    ["Semiconductor", "Networking"],
    "Networking":           ["AI Infrastructure", "Data Center Cooling"],
    "Data Center Cooling":  ["Networking", "AI Infrastructure"],
    # Energy cluster
    "Electric Grid":    ["Nuclear Energy", "Cable / Copper"],
    "Nuclear Energy":   ["Electric Grid", "Utilities"],
    "Cable / Copper":   ["Electric Grid"],
    "Utilities":        ["Nuclear Energy", "Electric Grid"],
    # Top-level
    "Semiconductor":    ["AI Infrastructure"],
}

# Capital rotation chains — where money migrates NEXT as a theme matures
# key = source theme, value = list of themes that receive rotated capital
ROTATION_DOWNSTREAM: Dict[str, List[str]] = {
    "AI Infrastructure": ["HBM", "Networking", "Data Center Cooling", "Glass Substrate"],
    "Semiconductor":     ["HBM", "Glass Substrate", "CoWoS"],
    "HBM":               ["Glass Substrate", "CoWoS"],
    "Electric Grid":     ["Nuclear Energy", "Cable / Copper"],
    "Networking":        ["Data Center Cooling"],
    "Commodities":       ["Cable / Copper", "Electric Grid"],
}

# For each theme: which upstream themes rotate INTO it
ROTATION_UPSTREAM: Dict[str, List[str]] = {}
for _src, _dsts in ROTATION_DOWNSTREAM.items():
    for _dst in _dsts:
        ROTATION_UPSTREAM.setdefault(_dst, []).append(_src)


# ---------------------------------------------------------------------------
# Horizon-specific factor weights
# ---------------------------------------------------------------------------

HORIZON_WEIGHTS: Dict[str, Dict[str, float]] = {
    "1W": {
        "momentum_1m":          0.30,
        "acceleration":         0.25,
        "volume_expansion":     0.20,
        "breadth":              0.15,
        "macro_alignment":      0.10,
    },
    "1M": {
        "momentum_3m":          0.25,
        "breadth":              0.22,
        "residual_vs_parent":   0.18,
        "capital_rotation":     0.15,
        "macro_alignment":      0.20,
    },
    "3M": {
        "regime_alignment":     0.28,
        "capital_rotation":     0.25,
        "residual_vs_parent":   0.22,
        "structural_leadership":0.15,
        "crowding_inverse":     0.10,
    },
}


# ---------------------------------------------------------------------------
# Score history registry (in-process, no SQLite dependency)
# ---------------------------------------------------------------------------

_score_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=4))
_rank_history:  Dict[str, deque] = defaultdict(lambda: deque(maxlen=4))


def update_score_history(theme_name: str, score: float, rank: int = -1) -> None:
    """Record a theme's score and rank for stability tracking."""
    if math.isfinite(score):
        _score_history[theme_name].append(score)
    if rank >= 0:
        _rank_history[theme_name].append(rank)


def compute_forecast_stability(theme_name: str) -> float:
    """Return a stability score 0-100.

    High score = ranking has been consistent across recent periods.
    Low score  = forecast is oscillating / unreliable.
    """
    score_hist = list(_score_history[theme_name])
    rank_hist  = list(_rank_history[theme_name])

    if len(score_hist) < 2:
        return 60.0  # neutral default when no history

    score_variance = stdev(score_hist) if len(score_hist) > 1 else 0.0
    rank_variance  = stdev(rank_hist)  if len(rank_hist) > 1  else 0.0

    # High variance → low stability
    stability = bounded_score(
        82.0
        - score_variance * 3.5   # score swings of ±10 pts ≈ -35
        - rank_variance  * 8.0   # rank swings of ±2 positions ≈ -16
    )
    return round(stability, 1)


# ---------------------------------------------------------------------------
# Part 1 — Residual Strength
# ---------------------------------------------------------------------------

def compute_residual_strength(
    theme_name: str,
    raw_scores: Dict[str, float],
) -> float:
    """Return residual alpha of a theme over its parent sector and peers.

    raw_scores: {theme_name: raw_weighted_score} for ALL themes in this run.
    Returns bounded_score centered at 50 (50 = no residual edge).
    """
    my_score = raw_scores.get(theme_name)
    if my_score is None or not math.isfinite(my_score):
        return 50.0

    parent_name = THEME_PARENT.get(theme_name)
    parent_score = raw_scores.get(parent_name, my_score) if parent_name else my_score
    residual_vs_parent = my_score - parent_score  # positive = outperforming parent

    peer_names = THEME_PEERS.get(theme_name, [])
    peer_scores = [raw_scores[p] for p in peer_names if p in raw_scores and math.isfinite(raw_scores[p])]
    peer_mean = mean(peer_scores) if peer_scores else my_score
    residual_vs_peers = my_score - peer_mean  # positive = outperforming peers

    residual = bounded_score(
        50.0
        + residual_vs_parent * 0.60
        + residual_vs_peers  * 0.40
    )
    return round(residual, 1)


# ---------------------------------------------------------------------------
# Part 2 — Capital Rotation Score
# ---------------------------------------------------------------------------

def compute_capital_rotation(
    theme_name: str,
    all_metrics: Dict[str, Dict[str, Any]],
) -> float:
    """Measure capital migration signal for a theme.

    Positive = capital rotating INTO this theme.
    Negative = capital rotating OUT OF this theme.

    all_metrics: {theme_name: {"acceleration": float, "momentum_1m": float, ...}}
    """
    my = all_metrics.get(theme_name, {})
    my_acc = _safe(my.get("acceleration"), 0.0)
    my_mom = _safe(my.get("momentum_1m"), 0.0)

    inflow_signals: List[float] = []
    outflow_signals: List[float] = []

    # Upstreams rotating into me: upstream decelerating while I accelerate
    for upstream_name in ROTATION_UPSTREAM.get(theme_name, []):
        upstream = all_metrics.get(upstream_name, {})
        upstream_acc = _safe(upstream.get("acceleration"), 0.0)
        # Positive migration signal when I accelerate more than my upstream
        migration = my_acc - upstream_acc
        inflow_signals.append(migration)

    # Downstreams I'm rotating into: I decelerate while downstream accelerates
    for downstream_name in ROTATION_DOWNSTREAM.get(theme_name, []):
        downstream = all_metrics.get(downstream_name, {})
        downstream_acc = _safe(downstream.get("acceleration"), 0.0)
        # Outflow signal when downstream accelerates more than me
        departure = downstream_acc - my_acc
        outflow_signals.append(max(0.0, departure))

    inflow_mean  = mean(inflow_signals)  if inflow_signals  else 0.0
    outflow_mean = mean(outflow_signals) if outflow_signals else 0.0

    # Acceleration vs peer themes (broad rotation signal)
    peer_names = THEME_PEERS.get(theme_name, [])
    peer_accs = [_safe(all_metrics.get(p, {}).get("acceleration"), 0.0) for p in peer_names]
    peer_acc_mean = mean(peer_accs) if peer_accs else my_acc
    acceleration_vs_peers = my_acc - peer_acc_mean

    # Momentum comparison vs peers (confirms rotation is real)
    peer_moms = [_safe(all_metrics.get(p, {}).get("momentum_1m"), 0.0) for p in peer_names]
    peer_mom_mean = mean(peer_moms) if peer_moms else my_mom
    momentum_vs_peers = my_mom - peer_mom_mean

    capital_rotation = bounded_score(
        50.0
        + inflow_mean              * 80.0   # receiving capital from upstream
        - outflow_mean             * 40.0   # losing capital to downstream
        + acceleration_vs_peers    * 60.0   # outperforming peers on acceleration
        + momentum_vs_peers        * 40.0   # outperforming peers on momentum
    )
    return round(capital_rotation, 1)


# ---------------------------------------------------------------------------
# Part 3 — Crowding Penalty (raw, applied BEFORE bounded_score)
# ---------------------------------------------------------------------------

def compute_crowding_penalty_raw(
    ret_1m: float,
    acceleration: float,
    relative_volume: float,
    volatility: float,
    leadership_concentration: float,
) -> float:
    """Return crowding penalty as a RAW reduction to apply before clamping.

    The current system applies penalty after bounded_score() clips to 100,
    making it ineffective for saturated themes.  Apply this directly to the
    weighted sum before passing through bounded_score().

    Returns a value in [0, 35] that should be SUBTRACTED from raw score.
    """
    # Parabolic move: short-term return >> expected from volatility
    z_score_1m = ret_1m / max(volatility / math.sqrt(12.0), 0.005)
    parabolic_penalty = max(0.0, z_score_1m - 1.8) * 6.0

    # Volume climax: extreme above-average volume signals distribution
    volume_climax_penalty = max(0.0, relative_volume - 2.8) * 8.0

    # Acceleration overextension: short-term >> medium-term trend
    acceleration_penalty = max(0.0, acceleration - 0.18) * 40.0

    # Leadership concentration: one stock dominates (crowded into leaders)
    concentration_penalty = max(0.0, leadership_concentration - 0.55) * 20.0

    raw_penalty = parabolic_penalty + volume_climax_penalty + acceleration_penalty + concentration_penalty
    return min(raw_penalty, 35.0)  # cap at 35 raw score points


def compute_crowding_score(
    ret_1m: float,
    acceleration: float,
    relative_volume: float,
    volatility: float,
    leadership_concentration: float,
) -> float:
    """Return crowding as a 0-100 score for display (separate from penalty).

    High score = late-stage crowded = risk signal.
    """
    z_score_1m = ret_1m / max(volatility / math.sqrt(12.0), 0.005)
    parabolic = max(0.0, z_score_1m - 1.5) * 20.0
    volume_climax = max(0.0, relative_volume - 2.0) * 25.0
    overextension = max(0.0, acceleration - 0.12) * 80.0
    concentration = max(0.0, leadership_concentration - 0.50) * 60.0
    return bounded_score(parabolic + volume_climax + overextension + concentration)


# ---------------------------------------------------------------------------
# Part 4 — Calibrated Forecast Confidence
# ---------------------------------------------------------------------------

def compute_forecast_confidence(
    subscores: List[float],
    breadth: float,
    macro_alignment: float,
    theme_name: str,
) -> float:
    """Return forecast confidence 0-100.

    Confidence is INDEPENDENT of score magnitude.
    High confidence = factors agree, breadth is wide, macro supports, stable rank.

    subscores: list of individual factor scores (momentum, volume, earnings etc.)
    breadth: fraction of theme tickers with positive momentum (0-1)
    macro_alignment: macro_alignment score (0-100)
    """
    # Feature agreement: low inter-factor standard deviation = high agreement
    finite_subs = [s for s in subscores if math.isfinite(s)]
    if len(finite_subs) >= 2:
        inter_factor_stdev = stdev(finite_subs)
        agreement_score = bounded_score(75.0 - inter_factor_stdev * 1.2)
    else:
        agreement_score = 55.0

    # Breadth agreement: wide participation = credible signal
    breadth_score = bounded_score(breadth * 100.0)

    # Regime agreement: macro environment supports the theme
    regime_score = macro_alignment  # already 0-100

    # Ranking stability from history
    stability = compute_forecast_stability(theme_name)

    confidence = bounded_score(
        agreement_score * 0.30
        + breadth_score  * 0.25
        + regime_score   * 0.25
        + stability      * 0.20
    )
    return round(confidence, 1)


# ---------------------------------------------------------------------------
# Part 5 — Horizon-Differentiated Scoring
# ---------------------------------------------------------------------------

def compute_horizon_scores(
    theme_name: str,
    metrics: Dict[str, Any],
    macro_state: Dict[str, Any],
    raw_scores: Dict[str, float],
) -> Dict[str, float]:
    """Return horizon-differentiated raw scores (pre-rescale).

    metrics keys expected:
        momentum_1m, momentum_3m, acceleration, volume_expansion,
        breadth, macro_alignment, capital_rotation, residual_vs_parent,
        structural_leadership (≈ institutional_accumulation),
        crowding_penalty (display score 0-100)

    Returns {"1w": float, "1m": float, "3m": float}
    """
    # Extract and default all needed values
    mom_1m       = _safe(metrics.get("momentum_1m"),          50.0)
    mom_3m       = _safe(metrics.get("momentum_3m"),          50.0)
    accel        = _safe(metrics.get("acceleration"),          50.0)  # already in score form 0-100
    volume       = _safe(metrics.get("volume_expansion"),      50.0)
    breadth      = _safe(metrics.get("breadth"),               50.0)
    macro        = _safe(metrics.get("macro_alignment"),       50.0)
    cap_rot      = _safe(metrics.get("capital_rotation"),      50.0)
    residual     = _safe(metrics.get("residual_vs_parent"),    50.0)
    structural   = _safe(metrics.get("structural_leadership"), 50.0)
    crowding     = _safe(metrics.get("crowding_penalty"),      20.0)  # display score
    crowding_inv = bounded_score(100.0 - crowding)  # high crowding → low 3M score

    # Trend quality proxy: how many sub-factors agree with momentum direction
    trend_quality = bounded_score(
        mom_3m * 0.50 + breadth * 0.30 + structural * 0.20
    )

    w_1w = HORIZON_WEIGHTS["1W"]
    score_1w = bounded_score(
        mom_1m    * w_1w["momentum_1m"]
        + accel   * w_1w["acceleration"]
        + volume  * w_1w["volume_expansion"]
        + breadth * w_1w["breadth"]
        + macro   * w_1w["macro_alignment"]
    )

    w_1m = HORIZON_WEIGHTS["1M"]
    score_1m = bounded_score(
        mom_3m    * w_1m["momentum_3m"]
        + breadth * w_1m["breadth"]
        + residual * w_1m["residual_vs_parent"]
        + cap_rot  * w_1m["capital_rotation"]
        + macro    * w_1m["macro_alignment"]
    )

    w_3m = HORIZON_WEIGHTS["3M"]
    score_3m = bounded_score(
        macro         * w_3m["regime_alignment"]
        + cap_rot     * w_3m["capital_rotation"]
        + residual    * w_3m["residual_vs_parent"]
        + structural  * w_3m["structural_leadership"]
        + crowding_inv * w_3m["crowding_inverse"]
    )

    return {
        "1w": round(score_1w, 1),
        "1m": round(score_1m, 1),
        "3m": round(score_3m, 1),
    }


# ---------------------------------------------------------------------------
# Part 6 — Cross-Sectional Percentile Rescaling
# ---------------------------------------------------------------------------

def percentile_rescale(
    theme_raw_scores: Dict[str, float],
    target_low: float = 25.0,
    target_high: float = 96.0,
) -> Dict[str, float]:
    """Map raw theme scores to calibrated range using rank percentile.

    This prevents saturation: even when ALL themes score 95+, the output
    is spread across [target_low, target_high].

    Returns {theme_name: calibrated_score}.
    """
    names = [n for n, s in theme_raw_scores.items() if math.isfinite(s)]
    if not names:
        return {}
    if len(names) == 1:
        return {names[0]: (target_low + target_high) / 2.0}

    sorted_names = sorted(names, key=lambda n: theme_raw_scores[n])
    span = target_high - target_low
    result: Dict[str, float] = {}
    for position, name in enumerate(sorted_names):
        pct = position / (len(sorted_names) - 1)  # 0.0 → 1.0
        calibrated = target_low + pct * span
        result[name] = round(calibrated, 1)
    return result


# ---------------------------------------------------------------------------
# Explanation layer — Phase 6.0B aware
# ---------------------------------------------------------------------------

def explain_forecast(
    theme_name: str,
    score_1w: float,
    score_1m: float,
    score_3m: float,
    residual: float,
    capital_rotation: float,
    crowding: float,
    macro_alignment: float,
    forecast_confidence: float,
) -> List[str]:
    """Generate human-readable forecast explanation referencing all new signals."""
    lines: List[str] = []

    # Residual strength vs parent
    parent = THEME_PARENT.get(theme_name)
    if residual > 58:
        edge = "+" if residual > 65 else ""
        lines.append(
            f"{theme_name} shows residual alpha vs "
            f"{'parent sector ' + parent if parent else 'sector peers'} "
            f"(residual score: {edge}{residual:.0f})."
        )
    elif residual < 42:
        lines.append(
            f"{theme_name} is lagging its "
            f"{'parent ' + parent if parent else 'sector peers'} "
            f"(residual score: {residual:.0f})."
        )

    # Capital rotation
    if capital_rotation > 60:
        upstreams = ROTATION_UPSTREAM.get(theme_name, [])
        src = upstreams[0] if upstreams else "broader market"
        lines.append(
            f"Capital rotation signal: inflows from {src} detected "
            f"(rotation score: {capital_rotation:.0f})."
        )
    elif capital_rotation < 40:
        downstreams = ROTATION_DOWNSTREAM.get(theme_name, [])
        dst = downstreams[0] if downstreams else "sub-themes"
        lines.append(
            f"Capital appears to be rotating toward {dst} "
            f"(rotation score: {capital_rotation:.0f})."
        )

    # Crowding
    if crowding > 55:
        lines.append(
            f"Crowding risk detected: acceleration, volume, or concentration elevated "
            f"(crowding penalty: {crowding:.0f})."
        )

    # Regime context
    if macro_alignment > 65:
        lines.append(f"Cross-asset regime is aligned with {theme_name} thesis.")

    # Horizon divergence
    divergence = abs(score_1w - score_3m)
    if divergence > 12:
        if score_1w > score_3m:
            lines.append(
                f"Short-term momentum ({score_1w:.0f}/100) exceeds 3M structural forecast "
                f"({score_3m:.0f}/100) — near-term opportunity with rotation risk."
            )
        else:
            lines.append(
                f"Structural 3M forecast ({score_3m:.0f}/100) leads short-term momentum "
                f"({score_1w:.0f}/100) — early-stage positioning opportunity."
            )

    # Confidence caveat
    if forecast_confidence < 48:
        lines.append(
            f"Forecast confidence is limited ({forecast_confidence:.0f}/100) "
            f"— partial data or unstable ranking."
        )

    if not lines:
        lines.append(
            f"{theme_name} maintains watchlist status with moderate cross-factor agreement."
        )
    return lines


# ---------------------------------------------------------------------------
# Part 9 — Discovery Architecture Hooks (stubs)
# ---------------------------------------------------------------------------

@runtime_checkable
class ThemeDiscoveryHook(Protocol):
    """Protocol for future Theme Discovery Engine plugins.

    Phase 7+ will implement:
    - narrative emergence via keyword clustering
    - stock co-movement clustering
    - supply-chain expansion detection
    - abnormal relative strength diffusion
    - cross-theme capital migration detection
    - early-stage theme scoring
    """

    def detect_emerging_narratives(
        self, news_corpus: List[str], lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Return candidate emerging theme narratives from news/text."""
        ...

    def cluster_co_movement(
        self, returns_matrix: Any, n_clusters: int = 8
    ) -> List[Dict[str, Any]]:
        """Return stock clusters by return co-movement."""
        ...

    def map_supply_chain_expansion(
        self, seed_theme: str
    ) -> List[Dict[str, Any]]:
        """Return extended supply chain nodes beyond the static registry."""
        ...


# Future discovery plugins registered here — empty until Phase 7
DISCOVERY_REGISTRY: List[ThemeDiscoveryHook] = []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default
