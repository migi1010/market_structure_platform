from __future__ import annotations

from datetime import UTC, datetime

from theme_intelligence.storage.theme_repository import ThemeRepository

from .theme_registry_builder import ThemeRegistryBuilder
from .theme_registry_repository import ThemeRegistryRepository


def export_theme_registry(repository: ThemeRepository | None = None) -> dict:
    registry_repository = ThemeRegistryRepository(repository)
    builder = ThemeRegistryBuilder()
    entries = builder.build(
        graph_entries=registry_repository.graph_themes(),
        scout_entries=registry_repository.scout_themes(),
        pipeline_entries=registry_repository.pipeline_themes(),
    )
    return {
        "available": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_priority": ["GRAPH", "SCOUT", "MANUAL"],
        "themes": [entry.to_dict() for entry in entries],
    }
