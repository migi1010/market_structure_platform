from __future__ import annotations

from collections.abc import Iterable

from .theme_registry_models import ThemeRegistryEntry


STATUS_ORDER = {"ACTIVE": 0, "DISCOVERED": 1, "ARCHIVED": 2}
SOURCE_ORDER = {"GRAPH": 0, "SCOUT": 1, "MANUAL": 2}


class ThemeRegistryBuilder:
    def build(
        self,
        *,
        graph_entries: Iterable[ThemeRegistryEntry],
        scout_entries: Iterable[ThemeRegistryEntry],
        pipeline_entries: Iterable[ThemeRegistryEntry],
    ) -> list[ThemeRegistryEntry]:
        selected: dict[str, ThemeRegistryEntry] = {}
        for row in [*graph_entries, *scout_entries, *pipeline_entries]:
            current = selected.get(row.theme_id)
            if current is None or SOURCE_ORDER[row.source] < SOURCE_ORDER[current.source]:
                selected[row.theme_id] = row
            elif current is not None and row.source == current.source:
                selected[row.theme_id] = self._merge_same_source(current, row)
        return sorted(
            selected.values(),
            key=lambda row: (
                STATUS_ORDER[row.status],
                -float(row.rank),
                self._descending_timestamp(row.updated_at),
                row.theme_id,
            ),
        )

    @staticmethod
    def _merge_same_source(left: ThemeRegistryEntry, right: ThemeRegistryEntry) -> ThemeRegistryEntry:
        return ThemeRegistryEntry(
            theme_id=left.theme_id,
            theme_name=left.theme_name,
            status=left.status,
            source=left.source,
            theme_type=left.theme_type,
            rank=max(left.rank, right.rank),
            research_case_count=left.research_case_count + right.research_case_count,
            graph_snapshot_count=max(left.graph_snapshot_count, right.graph_snapshot_count),
            controller_count=max(left.controller_count, right.controller_count),
            opportunity_count=max(left.opportunity_count, right.opportunity_count),
            updated_at=max(left.updated_at, right.updated_at),
        )

    @staticmethod
    def _descending_timestamp(value: str) -> str:
        # Stable descending lexical order for ISO timestamps.
        return "".join(chr(255 - ord(char)) for char in value)
