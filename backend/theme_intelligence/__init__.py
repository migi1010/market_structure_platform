from __future__ import annotations

from .aggregate import ThemeIntelligenceAggregateService, get_theme_intelligence_detail
from .discovery import DiscoveryEngine, get_theme_discovery
from .lifecycle import LifecycleEngine, get_theme_lifecycle, get_theme_lifecycle_detail
from .service import ThemeIntelligenceService, get_theme_intelligence, get_top_theme_intelligence
from .graph import get_theme_graph, get_theme_graph_detail, get_theme_overlap


def get_theme_catalysts() -> dict:
    from .catalysts import get_theme_catalysts as _get_theme_catalysts

    return _get_theme_catalysts()


def get_theme_catalyst_detail(theme_id: str) -> dict:
    from .catalysts import get_theme_catalyst_detail as _get_theme_catalyst_detail

    return _get_theme_catalyst_detail(theme_id)


def get_theme_bottlenecks() -> dict:
    from .bottlenecks import get_theme_bottlenecks as _get_theme_bottlenecks

    return _get_theme_bottlenecks()


def get_theme_bottleneck_detail(theme_id: str) -> dict:
    from .bottlenecks import get_theme_bottleneck_detail as _get_theme_bottleneck_detail

    return _get_theme_bottleneck_detail(theme_id)


def get_theme_beneficiaries() -> dict:
    from .beneficiaries import get_theme_beneficiaries as _get_theme_beneficiaries

    return _get_theme_beneficiaries()


def get_theme_beneficiary_detail(theme_id: str) -> dict:
    from .beneficiaries import get_theme_beneficiary_detail as _get_theme_beneficiary_detail

    return _get_theme_beneficiary_detail(theme_id)


def get_theme_scores() -> dict:
    from .theme_score import get_theme_scores as _get_theme_scores

    return _get_theme_scores()


def get_theme_score_detail(theme_id: str) -> dict:
    from .theme_score import get_theme_score_detail as _get_theme_score_detail

    return _get_theme_score_detail(theme_id)


def get_theme_portfolios() -> dict:
    from .portfolio import get_theme_portfolios as _get_theme_portfolios

    return _get_theme_portfolios()


def get_theme_portfolio_detail(portfolio_type: str) -> dict:
    from .portfolio import get_theme_portfolio_detail as _get_theme_portfolio_detail

    return _get_theme_portfolio_detail(portfolio_type)

__all__ = [
    "DiscoveryEngine",
    "LifecycleEngine",
    "ThemeIntelligenceAggregateService",
    "ThemeIntelligenceService",
    "get_theme_catalyst_detail",
    "get_theme_catalysts",
    "get_theme_bottleneck_detail",
    "get_theme_bottlenecks",
    "get_theme_beneficiaries",
    "get_theme_beneficiary_detail",
    "get_theme_scores",
    "get_theme_score_detail",
    "get_theme_portfolios",
    "get_theme_portfolio_detail",
    "get_theme_discovery",
    "get_theme_lifecycle",
    "get_theme_lifecycle_detail",
    "get_theme_intelligence",
    "get_theme_intelligence_detail",
    "get_theme_graph",
    "get_theme_graph_detail",
    "get_theme_overlap",
    "get_top_theme_intelligence",
]
