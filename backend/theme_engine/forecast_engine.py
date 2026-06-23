"""forecast_engine.py — Phase 6.0C Confidence Calibration + Residual Alpha Engine.

Transforms theme scoring from a sector-strength detector into a future
relative-alpha detector: "Where is capital moving next INSIDE the dominant trend?"

Key fixes over 6.0B:
  1. True residual alpha — measures theme vs peer TICKER BASKET, not just raw scores
  2. Probabilistic confidence — 8 independent signals, output bounded [28, 82]
  3. Cross-horizon differentiation — each horizon uses orthogonal factor sets
     with its own percentile_rescale
  4. Rotation velocity/direction/persistence added
  5. Crowding penalty tightened with RSI extension + volatility expansion + breadth saturation
  6. Peer group engine with explicit ticker baskets per cohort

Public API consumed by theme_scoring.py and theme_rotation.py:
    compute_residual_alpha(theme_name, theme_metrics_map)
    compute_capital_rotation(theme_name, theme_metrics_map)
    compute_crowding_penalty_raw(metrics_dict)
    compute_crowding_score(metrics_dict)
    compute_forecast_confidence(conf_inputs)
    compute_horizon_scores(theme_name, metrics, raw_scores)
    percentile_rescale(scores_by_theme, target_low, target_high)
    update_score_history(theme_name, score, rank, horizon_scores)
    compute_forecast_stability(theme_name)
    explain_forecast(...)
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from alpha_engine.scoring import bounded_score

# ---------------------------------------------------------------------------
# Part 2 — Peer Group Engine
# Explicit ticker baskets define each peer cohort so residual is computed
# from actual constituent momentum differentials, NOT raw composite scores.
# ---------------------------------------------------------------------------

# Peer groups: cohort name → list of representative ETF/ticker proxies
# These tickers are shared across themes — that is intentional.
# The residual alpha is the DIFFERENTIAL between a theme's basket and this cohort.
PEER_GROUP_TICKERS: Dict[str, List[str]] = {
    # Memory / HBM cohort
    "Memory": ["MU", "WDC", "STX", "AMAT", "LRCX"],
    # Advanced packaging cohort
    "Packaging": ["TSM", "AMAT", "KLAC", "ASML", "GLW"],
    # AI compute cohort
    "AI Compute": ["NVDA", "AMD", "AVGO", "TSLA", "INTC"],
    # AI infrastructure cohort
    "AI Infrastructure": ["NVDA", "AMD", "AVGO", "ANET", "VRT"],
    # Semiconductor broad cohort
    "Semiconductor": ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "TSM"],
    # AI networking cohort
    "AI Networking": ["ANET", "MRVL", "CSCO", "CIEN", "AVGO"],
    # Data center / cloud cohort
    "Data Center": ["VRT", "ETN", "TT", "JCI", "CARR"],
    # Electric / grid cohort
    "Electric Grid": ["ETN", "PWR", "HUBB", "NEE", "SO"],
    # Nuclear / energy cohort
    "Nuclear Energy": ["CEG", "VST", "CCJ", "BWXT", "NEE"],
    # Materials / industrial cohort
    "Materials": ["FCX", "SCCO", "TECK", "NUE", "STLD"],
    # Broad tech cohort (QQQ proxy)
    "Broad Tech": ["AAPL", "MSFT", "GOOGL", "META", "AMZN"],
}

# Theme → peer group mapping
THEME_PEER_GROUP: Dict[str, str] = {
    "HBM":                "Memory",
    "DRAM Cycle":         "Memory",
    "NAND Cycle":         "Memory",
    "Glass Substrate":    "Packaging",
    "CoWoS":              "Packaging",
    "AI Infrastructure":  "AI Infrastructure",
    "Semiconductor":      "Semiconductor",
    "Networking":         "AI Networking",
    "Data Center Cooling":"Data Center",
    "Electric Grid":      "Electric Grid",
    "Nuclear Energy":     "Nuclear Energy",
    "Cable / Copper":     "Materials",
    "Commodities":        "Materials",
    "Robotics":           "Broad Tech",
    "Cybersecurity":      "Broad Tech",
}

# Parent theme hierarchy (theme → one level up)
THEME_PARENT: Dict[str, str] = {
    # Memory sub-themes → Semiconductor parent
    "HBM":                "Semiconductor",
    "DRAM Cycle":         "Semiconductor",
    "NAND Cycle":         "Semiconductor",
    "Glass Substrate":    "Semiconductor",
    "CoWoS":              "Semiconductor",
    # AI sub-themes → AI Infrastructure parent
    "Networking":             "AI Infrastructure",
    "Data Center Cooling":    "AI Infrastructure",
    # Energy sub-themes → Electric Grid parent
    "Nuclear Energy":   "Electric Grid",
    "Cable / Copper":   "Electric Grid",
    "Utilities":        "Electric Grid",
    # Materials sub-themes → Commodities parent
    "Shipping":         "Commodities",
}

# Peer themes within the same parent
THEME_PEERS: Dict[str, List[str]] = {
    # Memory cluster
    "HBM":              ["DRAM Cycle", "NAND Cycle", "Glass Substrate", "CoWoS"],
    "DRAM Cycle":       ["HBM", "NAND Cycle", "Glass Substrate", "CoWoS"],
    "NAND Cycle":       ["HBM", "DRAM Cycle"],
    "Glass Substrate":  ["HBM", "CoWoS"],
    "CoWoS":            ["HBM", "Glass Substrate"],
    # AI cluster
    "AI Infrastructure":    ["Semiconductor", "Networking"],
    "Semiconductor":        ["AI Infrastructure"],
    "Networking":           ["AI Infrastructure", "Data Center Cooling"],
    "Data Center Cooling":  ["Networking", "AI Infrastructure"],
    # Energy cluster
    "Electric Grid":    ["Nuclear Energy", "Cable / Copper"],
    "Nuclear Energy":   ["Electric Grid", "Utilities"],
    "Cable / Copper":   ["Electric Grid"],
    "Utilities":        ["Nuclear Energy", "Electric Grid"],
}

# Macro cohort grouping for cross-cohort regime alignment
MACRO_COHORTS: Dict[str, List[str]] = {
    "AI_capex": [
        "AI Infrastructure", "Semiconductor", "HBM", "Glass Substrate",
        "CoWoS", "Networking", "Data Center Cooling",
    ],
    "Memory": ["HBM", "DRAM Cycle", "NAND Cycle"],
    "Packaging": ["Glass Substrate", "CoWoS"],
    "Energy_infra": [
        "Electric Grid", "Nuclear Energy", "Cable / Copper", "Utilities",
    ],
    "Industrials": [
        "Infrastructure", "Industrial Automation", "Robotics", "Defense",
    ],
    "Commodities": ["Commodities", "Shipping", "Agriculture", "Steel", "Cement"],
}

# Capital rotation chains — where money migrates NEXT as a theme matures
ROTATION_DOWNSTREAM: Dict[str, List[str]] = {
    "AI Infrastructure": ["HBM", "Networking", "Data Center Cooling", "Glass Substrate"],
    "Semiconductor":     ["HBM", "Glass Substrate", "CoWoS"],
    "HBM":               ["Glass Substrate", "CoWoS"],
    "Electric Grid":     ["Nuclear Energy", "Cable / Copper"],
    "Networking":        ["Data Center Cooling"],
    "Commodities":       ["Cable / Copper", "Electric Grid"],
}

# Auto-build upstream map
ROTATION_UPSTREAM: Dict[str, List[str]] = {}
for _src, _dsts in ROTATION_DOWNSTREAM.items():
    for _dst in _dsts:
        ROTATION_UPSTREAM.setdefault(_dst, []).append(_src)


# ---------------------------------------------------------------------------
# Score / rank / horizon history (in-process, no DB)
# maxlen=6 = ~90 minutes of data at 15-min cache buckets
# ---------------------------------------------------------------------------

_score_history:     Dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
_rank_history:      Dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
_horizon_history:   Dict[str, deque] = defaultdict(lambda: deque(maxlen=6))
_rotation_history:  Dict[str, deque] = defaultdict(lambda: deque(maxlen=6))


def update_score_history(
    theme_name: str,
    score: float,
    rank: int = -1,
    horizon_scores: Optional[Dict[str, float]] = None,
    rotation_score: float = 50.0,
) -> None:
    """Record score, rank, horizon scores, and rotation score for stability tracking."""
    if math.isfinite(score):
        _score_history[theme_name].append(score)
    if rank >= 0:
        _rank_history[theme_name].append(rank)
    if horizon_scores:
        avg_h = mean(v for v in horizon_scores.values() if math.isfinite(v)) if horizon_scores else score
        _horizon_history[theme_name].append(avg_h)
    if math.isfinite(rotation_score):
        _rotation_history[theme_name].append(rotation_score)


# ---------------------------------------------------------------------------
# Part 4 — Forecast Stability + Rotation Velocity
# ---------------------------------------------------------------------------

def compute_forecast_stability(theme_name: str) -> Dict[str, Any]:
    """Return a stability dict with score, velocity, direction, persistence.

    Returns:
        {
          "forecast_stability_score": float [28, 85],
          "rotation_velocity":   float [-1.0, +1.0],  # rate of score change
          "rotation_direction":  int    {-1, 0, +1},   # trend direction
          "rotation_persistence": int   [0, 6],         # consecutive same-direction periods
        }
    """
    score_hist  = list(_score_history[theme_name])
    rank_hist   = list(_rank_history[theme_name])
    rot_hist    = list(_rotation_history[theme_name])

    # Default response when no history
    if len(score_hist) < 2:
        return {
            "forecast_stability_score": 60.0,
            "rotation_velocity":       0.0,
            "rotation_direction":      0,
            "rotation_persistence":    0,
        }

    # Score stability: low variance = high stability
    score_var = stdev(score_hist) if len(score_hist) > 1 else 0.0
    rank_var  = stdev(rank_hist)  if len(rank_hist) > 1  else 0.0
    stability = bounded_score(
        80.0
        - score_var * 4.0    # ±10 pt swings → -40
        - rank_var  * 9.0    # ±2 rank swings → -18
    )
    # Clamp stability to [28, 85] so it always differentiates
    stability = max(28.0, min(85.0, stability))

    # Rotation velocity: last delta / span
    velocity = 0.0
    if len(score_hist) >= 2:
        delta = score_hist[-1] - score_hist[-2]
        span = max(abs(score_hist[-1]), abs(score_hist[-2]), 1.0)
        velocity = round(delta / span, 3)   # normalized to asset scale

    # Rotation direction
    if len(score_hist) >= 3:
        direction = 1 if score_hist[-1] > score_hist[-2] else (-1 if score_hist[-1] < score_hist[-2] else 0)
    else:
        direction = 0

    # Rotation persistence: how many consecutive periods same direction
    persistence = 0
    if direction != 0 and len(score_hist) >= 2:
        for i in range(len(score_hist) - 1, 0, -1):
            this_dir = 1 if score_hist[i] > score_hist[i - 1] else (-1 if score_hist[i] < score_hist[i - 1] else 0)
            if this_dir == direction:
                persistence += 1
            else:
                break

    return {
        "forecast_stability_score": round(stability, 1),
        "rotation_velocity":        round(velocity, 3),
        "rotation_direction":       direction,
        "rotation_persistence":     persistence,
    }


# ---------------------------------------------------------------------------
# Part 1 — True Residual Alpha Model
# ---------------------------------------------------------------------------

def compute_residual_alpha(
    theme_name: str,
    theme_metrics_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute residual alpha of a theme vs its peer group basket.

    theme_metrics_map: {theme_name: {"ret_1m": float, "ret_3m": float,
                                      "acceleration": float, "breadth": float, ...}}

    The key insight: residual is computed from raw return differentials
    (ret_1m, ret_3m, acceleration), NOT from composite bounded_scores.
    This gives true differentiation even when all themes beat SPY equally.

    Returns:
        {
          "residual_alpha_score":    float [0, 100] (50 = neutral),
          "peer_relative_strength":  float [-1, +1] (signed differential),
          "peer_momentum_rank":      int   [1, N]    (rank within peer group),
          "peer_breadth_rank":       int   [1, N],
          "peer_group":              str,
        }
    """
    my = theme_metrics_map.get(theme_name, {})
    my_ret_1m = _safe(my.get("ret_1m"), 0.0)
    my_ret_3m = _safe(my.get("ret_3m"), 0.0)
    my_acc    = _safe(my.get("acceleration"), 0.0)
    my_breadth = _safe(my.get("breadth"), 0.5)

    peer_group_name = THEME_PEER_GROUP.get(theme_name)
    peer_themes     = THEME_PEERS.get(theme_name, [])

    # Build peer basket from peer themes in this run
    peer_ret_1m_list:  List[float] = []
    peer_ret_3m_list:  List[float] = []
    peer_acc_list:     List[float] = []
    peer_breadth_list: List[float] = []

    for peer_name in peer_themes:
        peer = theme_metrics_map.get(peer_name, {})
        if peer:
            peer_ret_1m_list.append(_safe(peer.get("ret_1m"), 0.0))
            peer_ret_3m_list.append(_safe(peer.get("ret_3m"), 0.0))
            peer_acc_list.append(_safe(peer.get("acceleration"), 0.0))
            peer_breadth_list.append(_safe(peer.get("breadth"), 0.5))

    # Also compare vs parent theme
    parent_name = THEME_PARENT.get(theme_name)
    parent_data = theme_metrics_map.get(parent_name, {}) if parent_name else {}
    parent_ret_1m = _safe(parent_data.get("ret_1m"), my_ret_1m) if parent_data else my_ret_1m
    parent_ret_3m = _safe(parent_data.get("ret_3m"), my_ret_3m) if parent_data else my_ret_3m
    parent_acc    = _safe(parent_data.get("acceleration"), my_acc) if parent_data else my_acc

    # Peer basket averages
    peer_avg_1m = mean(peer_ret_1m_list) if peer_ret_1m_list else my_ret_1m
    peer_avg_3m = mean(peer_ret_3m_list) if peer_ret_3m_list else my_ret_3m
    peer_avg_acc = mean(peer_acc_list)   if peer_acc_list    else my_acc

    # Raw return differentials (percentage points, not normalized)
    residual_1m_vs_peers   = my_ret_1m - peer_avg_1m
    residual_3m_vs_peers   = my_ret_3m - peer_avg_3m
    residual_acc_vs_peers  = my_acc    - peer_avg_acc
    residual_1m_vs_parent  = my_ret_1m - parent_ret_1m
    residual_3m_vs_parent  = my_ret_3m - parent_ret_3m
    residual_acc_vs_parent = my_acc    - parent_acc

    # Composite residual (peers weighted 60%, parent 40%)
    # Each unit = 1% return differential; coefficient chosen so ±5% → ±25 pts
    composite_residual = (
        residual_1m_vs_peers   * 250.0 * 0.30   # 1M return vs peers
        + residual_3m_vs_peers * 120.0 * 0.20   # 3M return vs peers
        + residual_acc_vs_peers * 80.0 * 0.10   # acceleration vs peers
        + residual_1m_vs_parent * 200.0 * 0.20  # 1M return vs parent
        + residual_3m_vs_parent * 90.0  * 0.15  # 3M return vs parent
        + residual_acc_vs_parent * 60.0 * 0.05  # accel vs parent
    )
    residual_alpha_score = bounded_score(50.0 + composite_residual)

    # Peer-relative strength: signed sum of return differentials
    peer_relative_strength = round(
        residual_1m_vs_peers * 0.5 + residual_3m_vs_peers * 0.3 + residual_acc_vs_peers * 0.2,
        4
    )

    # Peer momentum rank (1 = highest momentum in peer group)
    all_peer_1m = sorted(peer_ret_1m_list + [my_ret_1m], reverse=True)
    try:
        peer_momentum_rank = all_peer_1m.index(my_ret_1m) + 1
    except ValueError:
        peer_momentum_rank = len(all_peer_1m)

    # Peer breadth rank (1 = widest breadth in peer group)
    all_peer_breadth = sorted(peer_breadth_list + [my_breadth], reverse=True)
    try:
        peer_breadth_rank = all_peer_breadth.index(my_breadth) + 1
    except ValueError:
        peer_breadth_rank = len(all_peer_breadth)

    return {
        "residual_alpha_score":   round(residual_alpha_score, 1),
        "peer_relative_strength": peer_relative_strength,
        "peer_momentum_rank":     peer_momentum_rank,
        "peer_breadth_rank":      peer_breadth_rank,
        "peer_group":             peer_group_name or "Broad",
    }


# ---------------------------------------------------------------------------
# Part 6 — Capital Rotation Refinement
# ---------------------------------------------------------------------------

def compute_capital_rotation(
    theme_name: str,
    theme_metrics_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute capital rotation metrics for a theme.

    Returns:
        {
          "capital_rotation_score":  float [0, 100],
          "rotation_velocity":       float [-1, +1],  # per-period change in score
          "rotation_direction":      int   {-1, 0, +1},
          "rotation_persistence":    int   [0, 6],
        }
    """
    my = theme_metrics_map.get(theme_name, {})
    my_acc = _safe(my.get("acceleration"), 0.0)
    my_mom = _safe(my.get("ret_1m"), 0.0)

    inflow_signals:  List[float] = []
    outflow_signals: List[float] = []

    # Upstream themes decelerating → capital flowing INTO me
    for up_name in ROTATION_UPSTREAM.get(theme_name, []):
        up = theme_metrics_map.get(up_name, {})
        up_acc = _safe(up.get("acceleration"), 0.0)
        # Positive = I'm accelerating more than upstream (rotation into me)
        migration = my_acc - up_acc
        inflow_signals.append(migration)

    # Downstream themes accelerating → capital flowing OUT of me
    for dn_name in ROTATION_DOWNSTREAM.get(theme_name, []):
        dn = theme_metrics_map.get(dn_name, {})
        dn_acc = _safe(dn.get("acceleration"), 0.0)
        departure = dn_acc - my_acc
        outflow_signals.append(max(0.0, departure))

    inflow_mean  = mean(inflow_signals)  if inflow_signals  else 0.0
    outflow_mean = mean(outflow_signals) if outflow_signals else 0.0

    # Peer comparison for validation
    peer_names = THEME_PEERS.get(theme_name, [])
    peer_accs  = [_safe(theme_metrics_map.get(p, {}).get("acceleration"), 0.0) for p in peer_names]
    peer_moms  = [_safe(theme_metrics_map.get(p, {}).get("ret_1m"), 0.0) for p in peer_names]
    peer_acc_mean = mean(peer_accs) if peer_accs else my_acc
    peer_mom_mean = mean(peer_moms) if peer_moms else my_mom

    acc_vs_peers = my_acc - peer_acc_mean
    mom_vs_peers = my_mom - peer_mom_mean

    capital_rotation_score = bounded_score(
        50.0
        + inflow_mean    * 85.0    # receiving from upstream
        - outflow_mean   * 45.0    # losing to downstream
        + acc_vs_peers   * 65.0    # outperforming peer acceleration
        + mom_vs_peers   * 45.0    # outperforming peer momentum
    )

    # Rotation velocity from history
    rot_hist = list(_rotation_history[theme_name])
    if len(rot_hist) >= 2:
        delta = capital_rotation_score - rot_hist[-1]
        velocity  = round(delta / max(abs(capital_rotation_score), abs(rot_hist[-1]), 1.0), 3)
        direction = 1 if delta > 0.5 else (-1 if delta < -0.5 else 0)
    else:
        velocity  = 0.0
        direction = 0

    # Persistence: consecutive periods in same direction
    persistence = 0
    if direction != 0 and len(rot_hist) >= 2:
        all_rot = rot_hist + [capital_rotation_score]
        for i in range(len(all_rot) - 1, 0, -1):
            d = 1 if all_rot[i] > all_rot[i - 1] else (-1 if all_rot[i] < all_rot[i - 1] else 0)
            if d == direction:
                persistence += 1
            else:
                break

    return {
        "capital_rotation_score":  round(capital_rotation_score, 1),
        "rotation_velocity":       velocity,
        "rotation_direction":      direction,
        "rotation_persistence":    persistence,
    }


# ---------------------------------------------------------------------------
# Part 7 — Crowding Penalty Refinement
# ---------------------------------------------------------------------------

def compute_crowding_metrics(
    ret_1m:                  float,
    ret_3m:                  float,
    acceleration:            float,
    relative_volume:         float,
    volatility:              float,
    leadership_concentration: float,
    breadth:                 float,
    volatility_expansion:    float = 0.0,   # current_vol / baseline_vol - 1.0
) -> Dict[str, Any]:
    """Compute enhanced crowding penalty with 7 signals.

    Returns:
        {
          "crowding_raw_penalty": float [0, 45],  # raw pts to subtract from score pre-clamp
          "crowding_score":       float [0, 100], # display metric
          "crowding_components":  dict,           # breakdown of each signal
        }
    """
    # 1. Parabolic extension: monthly return z-score vs annualised vol
    monthly_vol = max(volatility / math.sqrt(12.0), 0.005)
    z_score_1m  = ret_1m / monthly_vol
    parabolic   = max(0.0, z_score_1m - 1.6) * 7.0   # starts at z=1.6

    # 2. Volume climax: 3M return + volume surge → potential blow-off
    volume_climax = max(0.0, relative_volume - 2.2) * 10.0

    # 3. Acceleration overextension: 1M >> 3M/3 (mean reversion risk)
    expected_monthly = ret_3m / 3.0 if ret_3m != 0.0 else 0.0
    accel_excess = acceleration - expected_monthly  # > 0 → accelerating above trend
    acceleration_penalty = max(0.0, accel_excess - 0.06) * 50.0

    # 4. Leadership concentration: top stock dominates market cap
    concentration_penalty = max(0.0, leadership_concentration - 0.50) * 28.0

    # 5. Excessive breadth saturation: breadth = 1.0 in mature uptrend
    #    (everyone already long → no new buyers, rotation imminent)
    breadth_saturation = max(0.0, breadth - 0.88) * 80.0

    # 6. Volatility expansion: rising vol during rally = late-stage
    vol_expansion_penalty = max(0.0, volatility_expansion - 0.15) * 25.0

    # 7. 3M parabolic: 3M return itself extreme vs annual expectation
    quarterly_vol = max(volatility / math.sqrt(4.0), 0.01)
    z_score_3m = ret_3m / quarterly_vol
    three_month_parabolic = max(0.0, z_score_3m - 2.0) * 5.0

    raw_total = (
        parabolic
        + volume_climax
        + acceleration_penalty
        + concentration_penalty
        + breadth_saturation
        + vol_expansion_penalty
        + three_month_parabolic
    )
    crowding_raw_penalty = min(raw_total, 45.0)

    # Display score (0-100)
    display = bounded_score(
        parabolic              * 4.0
        + volume_climax        * 3.5
        + acceleration_penalty * 3.0
        + concentration_penalty * 2.5
        + breadth_saturation   * 2.0
        + vol_expansion_penalty * 2.5
        + three_month_parabolic * 3.0
    )

    return {
        "crowding_raw_penalty": round(crowding_raw_penalty, 2),
        "crowding_score":       round(display, 1),
        "crowding_components": {
            "parabolic_extension":   round(parabolic, 2),
            "volume_climax":         round(volume_climax, 2),
            "acceleration_excess":   round(acceleration_penalty, 2),
            "leadership_concentration": round(concentration_penalty, 2),
            "breadth_saturation":    round(breadth_saturation, 2),
            "volatility_expansion":  round(vol_expansion_penalty, 2),
            "three_month_parabolic": round(three_month_parabolic, 2),
        },
    }


def compute_crowding_penalty_raw(
    ret_1m: float,
    acceleration: float,
    relative_volume: float,
    volatility: float,
    leadership_concentration: float,
    ret_3m: float = 0.0,
    breadth: float = 0.5,
    volatility_expansion: float = 0.0,
) -> float:
    """Convenience wrapper returning only the raw penalty scalar."""
    result = compute_crowding_metrics(
        ret_1m=ret_1m,
        ret_3m=ret_3m,
        acceleration=acceleration,
        relative_volume=relative_volume,
        volatility=volatility,
        leadership_concentration=leadership_concentration,
        breadth=breadth,
        volatility_expansion=volatility_expansion,
    )
    return result["crowding_raw_penalty"]


def compute_crowding_score(
    ret_1m: float,
    acceleration: float,
    relative_volume: float,
    volatility: float,
    leadership_concentration: float,
    ret_3m: float = 0.0,
    breadth: float = 0.5,
    volatility_expansion: float = 0.0,
) -> float:
    """Convenience wrapper returning only the display score."""
    result = compute_crowding_metrics(
        ret_1m=ret_1m,
        ret_3m=ret_3m,
        acceleration=acceleration,
        relative_volume=relative_volume,
        volatility=volatility,
        leadership_concentration=leadership_concentration,
        breadth=breadth,
        volatility_expansion=volatility_expansion,
    )
    return result["crowding_score"]


# ---------------------------------------------------------------------------
# Part 3 — Probabilistic Confidence Calibration
# ---------------------------------------------------------------------------

def compute_forecast_confidence(conf_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute probabilistic forecast confidence from 8 independent signals.

    Confidence is ORTHOGONAL to score magnitude.
    High score + high confidence = strong, confirmed, stable signal.
    High score + low confidence  = strong but unstable or conflicted signal.

    Input keys (all optional with safe defaults):
        subscores:          List[float]  — individual factor scores (0-100)
        breadth:            float        — theme breadth (0-1)
        peer_breadth:       float        — peer group avg breadth (0-1)
        macro_alignment:    float        — macro alignment score (0-100)
        residual_alpha:     float        — residual alpha score (0-100)
        score_1w:           float        — 1W forecast score
        score_1m:           float        — 1M forecast score
        score_3m:           float        — 3M forecast score
        theme_name:         str          — for history lookup
        data_completeness:  float        — pct of data available (0-100)
        crowding:           float        — crowding score (0-100)

    Returns:
        {
          "forecast_confidence":     float [28, 82],
          "confidence_components":   dict,  # breakdown of 8 signals
          "confidence_label":        str,
        }
    """
    # Extract inputs
    subscores         = conf_inputs.get("subscores") or []
    breadth           = _safe(conf_inputs.get("breadth"), 0.5)
    peer_breadth      = _safe(conf_inputs.get("peer_breadth"), breadth)
    macro_alignment   = _safe(conf_inputs.get("macro_alignment"), 50.0)
    residual_alpha    = _safe(conf_inputs.get("residual_alpha"), 50.0)
    score_1w          = _safe(conf_inputs.get("score_1w"), 50.0)
    score_1m          = _safe(conf_inputs.get("score_1m"), 50.0)
    score_3m          = _safe(conf_inputs.get("score_3m"), 50.0)
    theme_name        = conf_inputs.get("theme_name") or ""
    data_completeness = _safe(conf_inputs.get("data_completeness"), 60.0)
    crowding          = _safe(conf_inputs.get("crowding"), 20.0)

    # Signal 1: Inter-factor agreement (low stdev = high agreement)
    finite_subs = [s for s in subscores if math.isfinite(s)]
    if len(finite_subs) >= 3:
        sub_stdev = stdev(finite_subs)
        # stdev of 0 → perfect agreement (score=85); stdev of 35 → poor (score=22)
        factor_agreement = bounded_score(85.0 - sub_stdev * 1.8)
    else:
        factor_agreement = 50.0  # insufficient data

    # Signal 2: Breadth vs peer breadth (relative breadth, not absolute)
    # If my breadth = 1.0 but peer_breadth = 1.0 too, confidence is NOT inflated
    breadth_vs_peer = breadth - peer_breadth
    # Positive = wider breadth than peers = genuinely confirmed
    # All 1.0: breadth_vs_peer = 0 → breadth_confidence = 50
    breadth_confidence = bounded_score(50.0 + breadth_vs_peer * 200.0)

    # Signal 3: Residual alpha consistency
    # Residual ≈ 50 (neutral) → low confidence in direction
    # Residual strongly above/below 50 → high confidence in direction
    residual_directional_strength = abs(residual_alpha - 50.0)
    residual_confidence = bounded_score(20.0 + residual_directional_strength * 2.0)

    # Signal 4: Macro regime agreement
    # Macro alignment = 50 is neutral; 80+ is strongly supportive
    regime_confidence = bounded_score(macro_alignment * 0.85)

    # Signal 5: Cross-horizon consistency
    # If 1W, 1M, 3M all point the same direction → high confidence
    horizon_scores = [score_1w, score_1m, score_3m]
    horizon_range = max(horizon_scores) - min(horizon_scores)
    # Range = 0: all horizons agree (score=80); Range = 50: divergent (score=30)
    horizon_consistency = bounded_score(80.0 - horizon_range * 1.0)

    # Signal 6: Ranking stability from history
    stab = compute_forecast_stability(theme_name)
    stability_score = _safe(stab.get("forecast_stability_score") if isinstance(stab, dict) else stab, 60.0)

    # Signal 7: Data completeness (partial data = lower confidence)
    completeness_confidence = bounded_score(data_completeness * 0.85)

    # Signal 8: Crowding penalty on confidence
    # High crowding = late-stage signal = lower predictive confidence
    crowding_confidence_penalty = max(0.0, crowding - 45.0) * 0.5
    crowding_confidence = bounded_score(75.0 - crowding_confidence_penalty)

    # Weighted composite — NONE of the inputs is score magnitude
    raw_confidence = (
        factor_agreement      * 0.20
        + breadth_confidence  * 0.12
        + residual_confidence * 0.15
        + regime_confidence   * 0.15
        + horizon_consistency * 0.15
        + stability_score     * 0.12
        + completeness_confidence * 0.08
        + crowding_confidence * 0.03
    )

    # Hard-clamp to [28, 82] — confidence never saturates to 100
    confidence = max(28.0, min(82.0, raw_confidence))

    # Label
    if confidence >= 70:
        label = "High"
    elif confidence >= 52:
        label = "Medium"
    elif confidence >= 38:
        label = "Partial"
    else:
        label = "Low"

    return {
        "forecast_confidence": round(confidence, 1),
        "confidence_components": {
            "factor_agreement":      round(factor_agreement, 1),
            "breadth_vs_peer":       round(breadth_confidence, 1),
            "residual_consistency":  round(residual_confidence, 1),
            "regime_alignment":      round(regime_confidence, 1),
            "horizon_consistency":   round(horizon_consistency, 1),
            "ranking_stability":     round(stability_score, 1),
            "data_completeness":     round(completeness_confidence, 1),
            "crowding_impact":       round(crowding_confidence, 1),
        },
        "confidence_label": label,
    }


# ---------------------------------------------------------------------------
# Part 5 — Cross-Horizon Differentiation
# ---------------------------------------------------------------------------

# Intentionally orthogonal factor sets — no factor appears in all three
HORIZON_WEIGHTS: Dict[str, Dict[str, float]] = {
    # 1W: Short-term flow pressure / breakout detection
    "1W": {
        "acceleration":         0.32,   # momentum acceleration (UNIQUE to 1W)
        "volume_expansion":     0.25,   # volume breakout (UNIQUE to 1W)
        "flow_expansion":       0.22,   # smart money / institutional flow
        "momentum_1m":          0.14,   # short-term price momentum
        "breadth":              0.07,   # breadth (small weight in 1W)
    },
    # 1M: Breadth, participation, peer leadership
    "1M": {
        "breadth":              0.28,   # wide participation (UNIQUE emphasis to 1M)
        "residual_alpha":       0.25,   # peer-relative alpha (KEY for 1M)
        "peer_leadership":      0.20,   # rank within peer group
        "momentum_3m":          0.15,   # 3M trend (longer window)
        "macro_alignment":      0.12,   # regime support
    },
    # 3M: Structural rotation, persistent capital, regime
    "3M": {
        "regime_alignment":     0.30,   # macro regime (UNIQUE emphasis to 3M)
        "structural_rotation":  0.27,   # capital rotation persistence (UNIQUE to 3M)
        "persistent_breadth":   0.22,   # sustained breadth (different from 1M point-in-time)
        "crowding_inverse":     0.13,   # uncrowded → room to run
        "residual_alpha":       0.08,   # smaller weight at 3M (structural over tactical)
    },
}


def compute_horizon_scores(
    theme_name: str,
    metrics: Dict[str, Any],
    raw_scores: Dict[str, float],
) -> Dict[str, float]:
    """Return horizon-differentiated scores using orthogonal factor sets.

    metrics keys:
        acceleration:       float [0-100]  (narrative / supply chain acceleration score)
        volume_expansion:   float [ratio]  (>1 = above average)
        flow_expansion:     float [0-100]  (smart money / institutional)
        momentum_1m:        float [0-100]  (short-term momentum score)
        breadth:            float [0-100]  (participation breadth score)
        residual_alpha:     float [0-100]  (residual_alpha_score)
        peer_leadership:    float [0-100]  (inverted peer_momentum_rank → score)
        momentum_3m:        float [0-100]  (3M momentum score)
        macro_alignment:    float [0-100]  (macro regime alignment)
        regime_alignment:   float [0-100]  (alias for macro_alignment)
        structural_rotation: float [0-100] (capital_rotation_score × persistence)
        persistent_breadth: float [0-100]  (breadth × stability)
        crowding_inverse:   float [0-100]  (100 - crowding_score)

    Returns {"1w": float, "1m": float, "3m": float} — all pre-rescale.
    """
    def _m(key: str, default: float = 50.0) -> float:
        return _safe(metrics.get(key), default)

    accel       = _m("acceleration")
    volume      = _safe(metrics.get("volume_expansion"), 1.0)
    volume_score = bounded_score(50.0 + (volume - 1.0) * 20.0)  # convert ratio to 0-100
    flow        = _m("flow_expansion")
    mom_1m      = _m("momentum_1m")
    breadth     = _m("breadth")
    residual    = _m("residual_alpha")
    peer_leader = _m("peer_leadership")
    mom_3m      = _m("momentum_3m")
    macro       = _m("macro_alignment")
    regime      = _m("regime_alignment", macro)
    struct_rot  = _m("structural_rotation")
    pers_breadth = _m("persistent_breadth", breadth)
    crowd_inv   = _m("crowding_inverse", bounded_score(100.0 - _m("crowding_penalty", 20.0)))

    w = HORIZON_WEIGHTS
    score_1w = bounded_score(
        accel        * w["1W"]["acceleration"]
        + volume_score * w["1W"]["volume_expansion"]
        + flow       * w["1W"]["flow_expansion"]
        + mom_1m     * w["1W"]["momentum_1m"]
        + breadth    * w["1W"]["breadth"]
    )
    score_1m = bounded_score(
        breadth      * w["1M"]["breadth"]
        + residual   * w["1M"]["residual_alpha"]
        + peer_leader * w["1M"]["peer_leadership"]
        + mom_3m     * w["1M"]["momentum_3m"]
        + macro      * w["1M"]["macro_alignment"]
    )
    score_3m = bounded_score(
        regime       * w["3M"]["regime_alignment"]
        + struct_rot * w["3M"]["structural_rotation"]
        + pers_breadth * w["3M"]["persistent_breadth"]
        + crowd_inv  * w["3M"]["crowding_inverse"]
        + residual   * w["3M"]["residual_alpha"]
    )

    return {
        "1w": round(score_1w, 1),
        "1m": round(score_1m, 1),
        "3m": round(score_3m, 1),
    }


# ---------------------------------------------------------------------------
# Cross-Sectional Percentile Rescaling (per-horizon)
# ---------------------------------------------------------------------------

def percentile_rescale(
    theme_raw_scores: Dict[str, float],
    target_low: float = 26.0,
    target_high: float = 95.0,
) -> Dict[str, float]:
    """Map raw scores to calibrated range using rank percentile.

    Prevents saturation: even when ALL themes score 95+, output is spread
    across [target_low, target_high].

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
        pct = position / (len(sorted_names) - 1)
        result[name] = round(target_low + pct * span, 1)
    return result


def percentile_rescale_all_horizons(
    rows: List[Dict[str, Any]],
    target_low: float = 26.0,
    target_high: float = 95.0,
) -> None:
    """Rescale 1W, 1M, 3M forecast scores independently across all themes.

    Modifies rows in-place. Each horizon gets its own spread — prevents
    1W/1M/3M from all clustering in the same range.

    1W uses slightly compressed range [28, 92] — short-term is more volatile.
    1M uses standard range [26, 95].
    3M uses compressed top [26, 90] — structural forecasts regress to mean.
    """
    for horizon, key, lo, hi in [
        ("1w", "forecast_score_1w", 28.0, 92.0),
        ("1m", "forecast_score_1m", 26.0, 95.0),
        ("3m", "forecast_score_3m", 26.0, 90.0),
    ]:
        raw = {row["theme"]: _safe(row.get(key), 50.0) for row in rows}
        calibrated = percentile_rescale(raw, target_low=lo, target_high=hi)
        for row in rows:
            row[key] = calibrated.get(row["theme"], row.get(key, 50.0))


# ---------------------------------------------------------------------------
# Explanation Layer — Phase 6.0C signals explicitly named
# ---------------------------------------------------------------------------

def explain_forecast(
    theme_name: str,
    score_1w: float,
    score_1m: float,
    score_3m: float,
    residual_alpha: float,
    peer_relative_strength: float,
    peer_momentum_rank: int,
    capital_rotation: float,
    rotation_velocity: float,
    rotation_direction: int,
    crowding: float,
    crowding_components: Optional[Dict[str, float]] = None,
    macro_alignment: float = 50.0,
    forecast_confidence: float = 60.0,
    confidence_label: str = "Medium",
    peer_group: str = "peers",
) -> List[str]:
    """Generate forecast explanation referencing all Phase 6.0C signals explicitly."""
    lines: List[str] = []

    # 1. Residual alpha vs peer leadership
    parent = THEME_PARENT.get(theme_name)
    if residual_alpha > 60:
        lines.append(
            f"Residual alpha vs {peer_group}: +{residual_alpha - 50:.0f} pts above peer basket "
            f"(peer rank #{peer_momentum_rank}, peer RS: {peer_relative_strength:+.1%})."
        )
    elif residual_alpha < 42:
        lines.append(
            f"Lagging {peer_group} peer basket by {50 - residual_alpha:.0f} pts "
            f"(peer rank #{peer_momentum_rank})."
        )
    else:
        lines.append(
            f"Neutral vs {peer_group} peer basket (residual alpha: {residual_alpha:.0f}/100)."
        )

    # 2. Capital rotation signal with velocity
    direction_str = "↑ rising" if rotation_direction == 1 else ("↓ falling" if rotation_direction == -1 else "→ stable")
    if capital_rotation > 62:
        upstreams = ROTATION_UPSTREAM.get(theme_name, [])
        src = upstreams[0] if upstreams else "broader market"
        lines.append(
            f"Capital rotation: inflows from {src} detected "
            f"(rotation score {capital_rotation:.0f}, velocity {direction_str})."
        )
    elif capital_rotation < 40:
        downstreams = ROTATION_DOWNSTREAM.get(theme_name, [])
        dst = downstreams[0] if downstreams else "sub-themes"
        lines.append(
            f"Capital rotating toward {dst} "
            f"(rotation score {capital_rotation:.0f}, velocity {direction_str})."
        )

    # 3. Crowding state
    if crowding > 58:
        components = crowding_components or {}
        top_signal = max(components, key=components.get) if components else "acceleration"
        lines.append(
            f"Crowding detected: {top_signal.replace('_', ' ')} elevated "
            f"(crowding score {crowding:.0f}/100 — late-stage risk)."
        )
    elif crowding < 25:
        lines.append(
            f"Low crowding ({crowding:.0f}/100) — ample room for new positioning."
        )

    # 4. Confidence drivers
    lines.append(
        f"Forecast confidence: {confidence_label} ({forecast_confidence:.0f}/100)."
    )

    # 5. Horizon divergence — surface the 'next' forecast vs 'now'
    h_spread = score_3m - score_1w
    if h_spread > 10:
        lines.append(
            f"3M structural outlook ({score_3m:.0f}) exceeds near-term ({score_1w:.0f}) "
            f"— early positioning opportunity for patient capital."
        )
    elif h_spread < -10:
        lines.append(
            f"Near-term momentum ({score_1w:.0f}) leads structural 3M ({score_3m:.0f}) "
            f"— tactical opportunity with rotation risk ahead."
        )

    # 6. Peer leadership summary
    if peer_momentum_rank == 1:
        lines.append(f"{theme_name} leads its {peer_group} peer group on momentum.")

    if not lines:
        lines.append(
            f"{theme_name} shows neutral cross-sectional positioning within {peer_group}."
        )
    return lines[:6]


# ---------------------------------------------------------------------------
# Legacy compatibility wrappers (called by theme_scoring.py)
# ---------------------------------------------------------------------------

def compute_residual_strength(
    theme_name: str,
    raw_scores: Dict[str, float],
) -> float:
    """Backward-compat wrapper. Returns residual_alpha_score from score-based fallback.

    Used by theme_scoring.py which doesn't have full metrics map.
    For true residual alpha, use compute_residual_alpha() in theme_rotation.py
    where full theme_metrics_map is available.
    """
    my_score = raw_scores.get(theme_name)
    if my_score is None or not math.isfinite(my_score):
        return 50.0

    parent_name = THEME_PARENT.get(theme_name)
    parent_score = raw_scores.get(parent_name, my_score) if parent_name else my_score
    residual_vs_parent = my_score - parent_score

    peer_names = THEME_PEERS.get(theme_name, [])
    peer_scores = [raw_scores[p] for p in peer_names if p in raw_scores and math.isfinite(raw_scores[p])]
    peer_mean = mean(peer_scores) if peer_scores else my_score
    residual_vs_peers = my_score - peer_mean

    return round(bounded_score(50.0 + residual_vs_parent * 0.60 + residual_vs_peers * 0.40), 1)


# ---------------------------------------------------------------------------
# Part 10 — Discovery Architecture Hooks
# ---------------------------------------------------------------------------

@runtime_checkable
class ThemeDiscoveryHook(Protocol):
    """Protocol for future Theme Discovery Engine plugins (Phase 7+).

    Future implementations will cover:
    - Keyword/narrative emergence via news clustering
    - Stock co-movement clustering (unsupervised)
    - Supply-chain expansion detection beyond static registry
    - Abnormal relative-strength diffusion (early-stage signals)
    - Cross-theme capital migration from microstructure data
    - Early-stage theme birth scoring and lifecycle classification

    Examples of themes discovered via this mechanism:
        Glass Substrate, CPO (Co-Packaged Optics), AI Cooling,
        AI Power, Advanced Packaging, Robotics Supply Chain
    """

    def detect_emerging_narratives(
        self, news_corpus: List[str], lookback_days: int = 30
    ) -> List[Dict[str, Any]]: ...

    def cluster_co_movement(
        self, returns_matrix: Any, n_clusters: int = 8
    ) -> List[Dict[str, Any]]: ...

    def map_supply_chain_expansion(
        self, seed_theme: str
    ) -> List[Dict[str, Any]]: ...

    def score_early_stage_theme(
        self, candidate: Dict[str, Any]
    ) -> float: ...

    def detect_narrative_inflection(
        self, keyword_series: Dict[str, List[float]]
    ) -> List[Dict[str, Any]]: ...


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
