from __future__ import annotations

import math
from collections import Counter
from dataclasses import replace

from theme_intelligence.storage.theme_repository import ThemeRepository

from .controller_models import ControllerIntelligence
from .graph_models import NodeKey
from .graph_repository import IndustrialGraphRepository
from .opportunity_models import (
    OPPORTUNITY_TYPE_ORDER,
    OPPORTUNITY_WEIGHTS,
    MarketComponent,
    MarketSourceRecord,
    OpportunityBuild,
    OpportunityIntelligence,
)


def _rounded(value: float) -> float:
    return round(float(value), 6)


class OpportunityBuilder:
    ALGORITHM_VERSION = "opportunity-v1"
    MAX_REASONING_PATHS = 25

    def __init__(self, repository: ThemeRepository | None = None) -> None:
        self.repository = IndustrialGraphRepository(repository or ThemeRepository())

    def prepare_reasoning_paths(
        self, controller: ControllerIntelligence
    ) -> tuple[tuple[NodeKey, ...], ...]:
        paths: set[tuple[NodeKey, ...]] = set()
        for path in controller.reasoning_paths:
            theme_indexes = [
                index for index, node in enumerate(path) if node[0] == "Theme"
            ]
            if theme_indexes:
                theme_index = theme_indexes[-1]
                paths.add(tuple(reversed(path[: theme_index + 1])))
            else:
                paths.add(path)
        return tuple(
            sorted(
                paths,
                key=lambda path: (
                    len(path),
                    path[0][1] if path[0][0] == "Theme" else "",
                    path,
                ),
            )[: self.MAX_REASONING_PATHS]
        )

    def build(self, controller_version: str | None = None) -> OpportunityBuild:
        snapshot = (
            self.repository.get_controller_snapshot(controller_version)
            if controller_version
            else self.repository.get_active_controller_snapshot()
        )
        if snapshot is None or snapshot.id is None:
            raise ValueError("missing controller snapshot reference")
        graph_snapshot = self.repository.get_snapshot(snapshot.graph_build_version)
        if graph_snapshot is None or graph_snapshot.id != snapshot.graph_snapshot_id:
            raise ValueError("missing graph snapshot reference")
        graph = self.repository.export_to_networkx(snapshot.graph_build_version)
        controllers = self.repository.get_controller_metrics(snapshot.controller_version)
        opportunities = [
            self._build_opportunity(controller, graph)
            for controller in controllers
        ]
        ranked = sorted(
            opportunities,
            key=lambda row: (
                -row.opportunity_score,
                -row.coverage_confidence,
                -row.controller_component,
                -row.constraint_component,
                row.company_key,
            ),
        )
        ranked = [
            replace(row, rank=index)
            for index, row in enumerate(ranked, 1)
        ]
        return OpportunityBuild(
            controller_snapshot_id=snapshot.id,
            controller_version=snapshot.controller_version,
            graph_snapshot_id=snapshot.graph_snapshot_id,
            graph_build_version=snapshot.graph_build_version,
            algorithm_version=self.ALGORITHM_VERSION,
            opportunities=tuple(ranked),
        )

    def _build_opportunity(
        self,
        controller: ControllerIntelligence,
        graph,
    ) -> OpportunityIntelligence:
        prepared_paths = self.prepare_reasoning_paths(controller)
        theme_support = self._reachable_theme_support(controller.reasoning_paths)
        theme_names = {
            key: str(graph.nodes[key].get("display_name") or key[1])
            for key in theme_support
            if key in graph
        }
        ticker = controller.company_key[1].split(":", 1)[1]
        attention = self._market_attention(theme_support, theme_names)
        valuation = self._penalty_component(
            "valuation_component",
            "valuation_penalty",
            ticker,
            theme_support,
            theme_names,
        )
        bubble = self._penalty_component(
            "bubble_risk_component",
            "bubble_penalty",
            ticker,
            theme_support,
            theme_names,
        )
        available = {
            "controller_component": True,
            "constraint_component": True,
            "dependency_component": True,
            "resolution_component": True,
            "criticality_component": True,
            attention.name: attention.availability_state == "available",
            valuation.name: valuation.availability_state == "available",
            bubble.name: bubble.availability_state == "available",
        }
        available_total = sum(
            weight
            for name, weight in OPPORTUNITY_WEIGHTS.items()
            if available[name]
        )
        applied = {
            name: (weight / available_total if available[name] else 0.0)
            for name, weight in OPPORTUNITY_WEIGHTS.items()
        }
        correction_key = next(
            reversed([name for name in OPPORTUNITY_WEIGHTS if available[name]])
        )
        applied[correction_key] += 1.0 - sum(applied.values())
        attention = replace(attention, applied_weight=applied[attention.name])
        valuation = replace(valuation, applied_weight=applied[valuation.name])
        bubble = replace(bubble, applied_weight=applied[bubble.name])
        criticality = (
            controller.technology_control * 0.15
            + controller.process_control * 0.20
            + controller.material_control * 0.25
            + controller.equipment_control * 0.25
            + controller.supply_chain_influence * 0.15
        )
        components = {
            "controller_component": controller.controller_score,
            "constraint_component": controller.constraint_influence,
            "dependency_component": controller.dependency_score,
            "resolution_component": controller.resolution_influence,
            "criticality_component": criticality,
            "market_attention_component": attention.normalized_value,
            "valuation_component": valuation.normalized_value,
            "bubble_risk_component": bubble.normalized_value,
        }
        base_score = sum(
            float(components[name]) * applied[name]
            for name in OPPORTUNITY_WEIGHTS
            if components[name] is not None
        )
        coverage_component = available_total * 100.0
        industrial_confidence = (
            controller.coverage + controller.coverage_confidence
        ) / 2.0
        coverage_confidence = industrial_confidence * coverage_component / 100.0
        opportunity_score = base_score * (
            0.50 + 0.50 * coverage_confidence / 100.0
        )
        types = self._opportunity_types(controller, prepared_paths, graph)
        return OpportunityIntelligence(
            company_key=controller.company_key,
            company_name=controller.company_name,
            opportunity_types=types,
            controller_component=_rounded(controller.controller_score),
            constraint_component=_rounded(controller.constraint_influence),
            dependency_component=_rounded(controller.dependency_score),
            resolution_component=_rounded(controller.resolution_influence),
            criticality_component=_rounded(criticality),
            market_attention=attention,
            valuation=valuation,
            bubble_risk=bubble,
            coverage_component=_rounded(coverage_component),
            coverage_confidence=_rounded(coverage_confidence),
            base_score=_rounded(base_score),
            opportunity_score=_rounded(opportunity_score),
            configured_weights=OPPORTUNITY_WEIGHTS,
            applied_weights=applied,
            evidence_ids=controller.evidence_ids,
            reasoning_paths=prepared_paths,
        )

    @staticmethod
    def _reachable_theme_support(
        paths: tuple[tuple[NodeKey, ...], ...],
    ) -> Counter[NodeKey]:
        support: Counter[NodeKey] = Counter()
        for path in set(paths):
            for theme in {node for node in path if node[0] == "Theme"}:
                support[theme] += 1
        return support

    def _market_attention(
        self,
        support: Counter[NodeKey],
        theme_names: dict[NodeKey, str],
    ) -> MarketComponent:
        rows = self._discovery_rows(theme_names.values())
        admitted: list[tuple[NodeKey, float, MarketSourceRecord]] = []
        for key in sorted(support):
            row = rows.get(theme_names.get(key, ""))
            if row is None:
                continue
            value = float(row["crowding_proxy"])
            self._validate_market_value(value, "crowding_proxy")
            if not str(row["updated_at"] or "").strip():
                continue
            admitted.append((
                key,
                value,
                MarketSourceRecord(
                    source_table="theme_discovery_scores",
                    source_record_key={
                        "id": str(row["id"]),
                        "theme_name": str(row["theme_name"]),
                    },
                    source_timestamp=str(row["updated_at"]),
                    source_value=value,
                ),
            ))
        if not admitted:
            return self._unavailable(
                "market_attention_component",
                "incomplete_reasoning_path" if not support else "missing_row",
            )
        denominator = sum(support[key] for key, _, _ in admitted)
        raw = sum(value * support[key] / denominator for key, value, _ in admitted)
        return MarketComponent(
            name="market_attention_component",
            raw_value=_rounded(raw),
            normalized_value=_rounded(100.0 - raw),
            availability_state="available",
            configured_weight=OPPORTUNITY_WEIGHTS["market_attention_component"],
            applied_weight=0.0,
            source_records=tuple(source for _, _, source in admitted),
        )

    def _penalty_component(
        self,
        component_name: str,
        column_name: str,
        ticker: str,
        support: Counter[NodeKey],
        theme_names: dict[NodeKey, str],
    ) -> MarketComponent:
        rows = self._beneficiary_rows(ticker, theme_names.values())
        selected: list[tuple[NodeKey, float, MarketSourceRecord]] = []
        ambiguous_zero = False
        for key in sorted(support):
            candidates = rows.get(theme_names.get(key, ""), ())
            valid: list = []
            for row in candidates:
                value = float(row[column_name])
                self._validate_market_value(value, column_name)
                if value == 0:
                    ambiguous_zero = True
                    continue
                if not str(row["updated_at"] or "").strip():
                    continue
                valid.append(row)
            if not valid:
                continue
            row = sorted(
                valid,
                key=lambda item: (-float(item[column_name]), int(item["id"])),
            )[0]
            value = float(row[column_name])
            selected.append((
                key,
                value,
                MarketSourceRecord(
                    source_table="theme_beneficiary_scores",
                    source_record_key={
                        "id": str(row["id"]),
                        "theme_name": str(row["theme_name"]),
                        "ticker": str(row["ticker"]),
                        "beneficiary_type": str(row["beneficiary_type"]),
                    },
                    source_timestamp=str(row["updated_at"]),
                    source_value=value,
                ),
            ))
        if not selected:
            reason = (
                "incomplete_reasoning_path"
                if not support
                else "ambiguous_zero" if ambiguous_zero else "missing_row"
            )
            return self._unavailable(component_name, reason)
        denominator = sum(support[key] for key, _, _ in selected)
        raw = sum(value * support[key] / denominator for key, value, _ in selected)
        return MarketComponent(
            name=component_name,
            raw_value=_rounded(raw),
            normalized_value=_rounded(100.0 - raw),
            availability_state="available",
            configured_weight=OPPORTUNITY_WEIGHTS[component_name],
            applied_weight=0.0,
            source_records=tuple(source for _, _, source in selected),
        )

    @staticmethod
    def _validate_market_value(value: float, name: str) -> None:
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")

    @staticmethod
    def _unavailable(name: str, reason: str) -> MarketComponent:
        return MarketComponent(
            name=name,
            raw_value=None,
            normalized_value=None,
            availability_state="unavailable",
            configured_weight=OPPORTUNITY_WEIGHTS[name],
            applied_weight=0.0,
            source_records=(),
            unavailable_reason=reason,
        )

    def _discovery_rows(self, theme_names) -> dict[str, object]:
        names = sorted(set(theme_names))
        if not names:
            return {}
        placeholders = ",".join("?" for _ in names)
        with self.repository.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, theme_name, crowding_proxy, updated_at
                FROM theme_discovery_scores
                WHERE theme_name IN ({placeholders})
                ORDER BY theme_name, id
                """,
                names,
            ).fetchall()
        return {str(row["theme_name"]): row for row in rows}

    def _beneficiary_rows(self, ticker: str, theme_names) -> dict[str, tuple]:
        names = sorted(set(theme_names))
        if not names:
            return {}
        placeholders = ",".join("?" for _ in names)
        with self.repository.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, theme_name, ticker, beneficiary_type,
                       valuation_penalty, bubble_penalty, updated_at
                FROM theme_beneficiary_scores
                WHERE ticker=? AND theme_name IN ({placeholders})
                ORDER BY theme_name, beneficiary_type, updated_at, id
                """,
                (ticker, *names),
            ).fetchall()
        grouped: dict[str, list] = {}
        for row in rows:
            grouped.setdefault(str(row["theme_name"]), []).append(row)
        return {key: tuple(value) for key, value in grouped.items()}

    @staticmethod
    def _opportunity_types(
        controller: ControllerIntelligence,
        paths: tuple[tuple[NodeKey, ...], ...],
        graph,
    ) -> tuple[str, ...]:
        node_types = {node[0] for path in paths for node in path}
        types: list[str] = []
        if controller.technology_control > 0 and "Technology" in node_types:
            types.append("Technology Opportunity")
        if controller.process_control > 0 and "Process" in node_types:
            types.append("Process Opportunity")
        if controller.material_control > 0 and "Material" in node_types:
            types.append("Material Opportunity")
        if controller.equipment_control > 0 and "Equipment" in node_types:
            types.append("Equipment Opportunity")
        if "Capacity Controller" in controller.controller_types:
            capacity = any(
                node[0] == "Constraint"
                and node in graph
                and graph.nodes[node].get("external_ids", {}).get("category")
                == "Capacity Constraint"
                for path in paths
                for node in path
            )
            if capacity:
                types.append("Capacity Opportunity")
        if controller.constraint_influence > 0 and "Constraint" in node_types:
            types.append("Constraint Opportunity")
        if (
            controller.supply_chain_influence > 0
            and "Supply Chain Controller" in controller.controller_types
        ):
            types.append("Supply Chain Opportunity")
        if len(types) >= 2:
            types.append("Hybrid Opportunity")
        return tuple(item for item in OPPORTUNITY_TYPE_ORDER if item in types)
