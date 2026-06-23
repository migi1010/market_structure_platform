from __future__ import annotations

from .bottleneck_models import BottleneckRecord

__all__ = [
    "BottleneckRecord",
    "get_theme_bottleneck_detail",
    "get_theme_bottlenecks",
]


def get_theme_bottlenecks() -> dict:
    from .bottleneck_engine import get_theme_bottlenecks as _get_theme_bottlenecks

    return _get_theme_bottlenecks()


def get_theme_bottleneck_detail(theme_id: str) -> dict:
    from .bottleneck_engine import get_theme_bottleneck_detail as _get_theme_bottleneck_detail

    return _get_theme_bottleneck_detail(theme_id)
