from __future__ import annotations

from collections import defaultdict
from typing import Any

from theme_intelligence.discovery.discovery_models import theme_id
from theme_intelligence.seeds.theme_seed_data import TARGET_SEED_THEMES
from theme_intelligence.storage.theme_repository import ThemeRepository


# Canonical supply-chain layers used to group theme_entities by entity_type.
# Ordered upstream → downstream.
_SUPPLY_CHAIN_LAYERS: list[tuple[str, str, list[str]]] = [
    ("upstream_materials", "Upstream Materials",  ["upstream_materials", "materials", "upstream"]),
    ("equipment",          "Equipment",            ["equipment", "tools", "inspection", "metrology"]),
    ("manufacturing",      "Manufacturing",        ["manufacturing", "capacity_owner", "foundry", "memory_suppliers", "optical_components"]),
    ("packaging",          "Packaging / Interposer",["packaging", "osat", "interposer", "substrate", "substrates", "switching", "networking"]),
    ("downstream",         "Downstream",           ["downstream", "cloud", "devices", "processors", "integrators", "automation",
                                                    "datacenter_power", "thermal", "electrical", "electrical_equipment",
                                                    "datacenter_cooling", "operators", "utilities"]),
]

# Also map special aggregate entity_type values (controller / resolution_enabler)
# into separate display buckets appended after the main layers when present.
_ROLE_LAYERS: list[tuple[str, str, list[str]]] = [
    ("bottleneck_controllers", "Bottleneck Controllers", ["controller"]),
    ("resolution_enablers",    "Resolution Enablers",   ["resolution_enabler"]),
]


class ThemeIntelligenceAggregateService:
    def __init__(
        self,
        repository: ThemeRepository | None = None,
        graph_engine: Any | None = None,
        industrial_projection: Any | None = None,
    ) -> None:
        self.repository = repository or ThemeRepository()
        if graph_engine is None:
            from theme_intelligence.graph.graph_engine import GraphEngine

            graph_engine = GraphEngine(self.repository)
        self.graph_engine = graph_engine
        self.industrial_projection = industrial_projection
        if industrial_projection is None and isinstance(self.repository, ThemeRepository):
            from theme_intelligence.industrial_graph.theme_industrial_projection import (
                ThemeIndustrialProjectionService,
            )

            self.industrial_projection = ThemeIndustrialProjectionService(self.repository)

    def get_theme(self, theme_id_value: str) -> dict[str, Any]:
        self.repository.initialize()
        industrial = (
            self.industrial_projection.get_theme(theme_id_value)
            if self.industrial_projection is not None
            else self._empty_industrial_projection(theme_id_value)
        )
        identity = industrial["identity"]
        normalized_id = str(identity["canonical_theme_key"])
        discovery_rows = self._filtered_rows("get_discovery_scores", limit=1, theme_id=normalized_id)
        discovery_name = self._match_name(discovery_rows, normalized_id)
        canonical_hint = (
            discovery_name
            or str(identity["display_name"])
            or normalized_id.replace("_", " ").title()
        )
        scores = self._filtered_rows("get_final_scores", limit=1, theme_name=canonical_hint)
        catalysts = self._filtered_rows("get_catalysts", theme_name=canonical_hint)
        bottlenecks = self._filtered_rows("get_bottlenecks", theme_name=canonical_hint)
        beneficiaries = self._filtered_rows("get_beneficiary_scores", theme_name=canonical_hint)
        portfolios = self.repository.get_portfolios(limit=20)
        entities = self._filtered_rows("get_entities", theme_name=canonical_hint)

        score = self._match_score(scores, normalized_id)
        canonical_name = (
            str(identity["display_name"])
            if identity.get("resolution_state") != "unresolved"
            else getattr(score, "theme_name", "")
            or self._match_name(discovery_rows, normalized_id)
            or normalized_id.replace("_", " ").title()
        )
        discovery = self._match_discovery(discovery_rows, normalized_id)
        lifecycle = self._lifecycle(canonical_name, discovery, score)
        supply_chain = self._supply_chain(
            canonical_name,
            entities,
            bottlenecks,
            beneficiaries,
            discovery,
            score,
        )
        supply_chain["dependency_paths"] = self._legacy_dependency_paths(industrial)
        return {
            "theme_id": normalized_id,
            "name": canonical_name,
            "score": score.to_api() if score else {},
            "discovery": discovery,
            "lifecycle": lifecycle,
            "catalysts": self._catalysts(canonical_name, catalysts),
            "bottlenecks": self._bottlenecks(canonical_name, bottlenecks),
            "beneficiaries": self._beneficiaries(canonical_name, beneficiaries),
            "portfolio_context": self._portfolio_context(canonical_name, portfolios),
            "supply_chain": supply_chain,
            "relationship_intelligence": self.graph_engine.relationship_intelligence(canonical_name),
            "industrial_intelligence": industrial,
        }

    @staticmethod
    def _empty_industrial_projection(theme_value: str) -> dict[str, Any]:
        normalized = normalize_theme_id(theme_value)
        return {
            "identity": {
                "requested_theme_id": normalized,
                "canonical_theme_key": normalized,
                "display_name": normalized.replace("_", " ").title(),
                "aliases": [],
                "resolution_state": "unresolved",
            },
            "lineage": {
                "graph_snapshot_id": None,
                "graph_build_version": None,
                "controller_snapshot_id": None,
                "controller_version": None,
                "opportunity_snapshot_id": None,
                "opportunity_version": None,
                "packet_family_version": None,
                "packet_family_revision": None,
                "lineage_state": "unavailable",
            },
            "graph": {
                "snapshot_id": None,
                "build_version": None,
                "nodes": [],
                "edges": [],
                "evidence_count": 0,
                "dependency_paths": [],
                "counts_by_type": {},
            },
            "constraints": [],
            "controllers": [],
            "opportunities": [],
            "decision_packets": {
                "family": None,
                "theme_packets": [],
                "company_packets": [],
                "opportunity_packets": [],
                "packet_count": 0,
                "evidence_count": 0,
                "path_count": 0,
                "risk_count": 0,
            },
            "coverage": {
                "overall": 0.0,
                "evidence": {"covered": 0, "total": 0, "percentage": 0.0},
                "by_type": {},
            },
            "research_gaps": [],
        }

    @staticmethod
    def _legacy_dependency_paths(
        industrial: dict[str, Any],
    ) -> list[dict[str, Any]]:
        paths = industrial.get("graph", {}).get("dependency_paths", [])
        rows = []
        for path in paths:
            names = [
                str(node.get("display_name") or "")
                for node in path.get("nodes", [])
                if node.get("display_name")
            ]
            if len(names) < 2:
                continue
            rows.append({
                "path": " \u2192 ".join(names),
                "depth": int(path.get("depth") or 0),
                "evidence_ids": list(path.get("evidence_ids") or []),
            })
        return rows

    def _filtered_rows(self, method_name: str, **kwargs: Any) -> list[Any]:
        method = getattr(self.repository, method_name)
        try:
            return method(**kwargs)
        except TypeError:
            fallback_kwargs = {"limit": kwargs["limit"]} if "limit" in kwargs else {}
            return method(**fallback_kwargs)

    @staticmethod
    def _match_score(scores: list[Any], normalized_id: str) -> Any | None:
        for row in scores:
            if normalize_theme_id(getattr(row, "theme_name", "")) == normalized_id:
                return row
        return None

    @staticmethod
    def _match_name(rows: list[dict[str, Any]], normalized_id: str) -> str:
        for row in rows:
            name = str(row.get("name") or row.get("theme") or "")
            if normalize_theme_id(name) == normalized_id or normalize_theme_id(str(row.get("theme_id", ""))) == normalized_id:
                return name
        return ""

    @staticmethod
    def _match_discovery(rows: list[dict[str, Any]], normalized_id: str) -> dict[str, Any]:
        for row in rows:
            if normalize_theme_id(str(row.get("name") or row.get("theme") or "")) == normalized_id or normalize_theme_id(str(row.get("theme_id", ""))) == normalized_id:
                return row
        return {}

    def _lifecycle(self, theme_name: str, discovery: dict[str, Any], score: Any | None) -> dict[str, Any]:
        history = self.repository.get_score_history(theme_name)
        components = getattr(score, "score_components", {}) if score else {}
        get_lifecycle = getattr(self.repository, "get_lifecycle", None)
        persisted = get_lifecycle(theme_name) if callable(get_lifecycle) else None
        seed_hint = next(
            (theme.lifecycle_hint for theme in TARGET_SEED_THEMES if normalize_theme_id(theme.name) == normalize_theme_id(theme_name)),
            None,
        )

        raw_stage = (
            (persisted or {}).get("lifecycle_stage")
            or discovery.get("lifecycle_stage")
            or components.get("lifecycle_stage")
            or (seed_hint.stage if seed_hint else None)
        )
        raw_confidence = (
            (persisted or {}).get("lifecycle_confidence")
            if (persisted or {}).get("lifecycle_confidence") is not None
            else discovery.get("lifecycle_confidence")
            if discovery.get("lifecycle_confidence") is not None
            else components.get("lifecycle_confidence")
            if components.get("lifecycle_confidence") is not None
            else seed_hint.confidence if seed_hint else None
        )
        raw_next = (
            (persisted or {}).get("expected_next_stage")
            or discovery.get("expected_next_stage")
            or components.get("expected_next_stage")
            or (seed_hint.expected_next_stage if seed_hint else None)
        )
        source = (
            "persisted"
            if persisted
            else "discovery"
            if discovery.get("lifecycle_stage")
            else "score_components"
            if components.get("lifecycle_stage")
            else "seed_hint"
            if seed_hint
            else None
        )

        return {
            "theme_id": normalize_theme_id(theme_name),
            "name": theme_name,
            # Return None when no real stage is available — frontend renders honest empty state.
            "lifecycle_stage": raw_stage if raw_stage else None,
            "lifecycle_confidence": raw_confidence if raw_confidence is not None else None,
            "expected_next_stage": raw_next if raw_next else None,
            "time_window": discovery.get("time_window") or None,
            "stage_reason": discovery.get("lifecycle_reason") or (seed_hint.rationale if seed_hint else None),
            "source": source,
            "history": history,
        }

    @staticmethod
    def _catalysts(theme_name: str, catalysts: list[Any]) -> dict[str, Any]:
        rows = [row for row in catalysts if normalize_theme_id(getattr(row, "theme_name", "")) == normalize_theme_id(theme_name)]
        payloads = [row.to_api() if hasattr(row, "to_api") else {} for row in rows]
        top = sorted(payloads, key=lambda item: float(item.get("catalyst_strength", item.get("impact_score", 0)) or 0), reverse=True)
        return {
            "top_catalysts": top[:5],
            "future_catalysts": [row for row in top if row.get("timeline_status") == "future"][:5],
            "key_blockers": [row for row in top if row.get("polarity") == "risk"][:5],
        }

    @staticmethod
    def _bottlenecks(theme_name: str, bottlenecks: list[Any]) -> dict[str, Any]:
        rows = [row for row in bottlenecks if normalize_theme_id(getattr(row, "theme_name", "")) == normalize_theme_id(theme_name)]
        payloads = [row.to_api() if hasattr(row, "to_api") else {} for row in rows]
        ranked = sorted(payloads, key=lambda item: float(item.get("bottleneck_strength", 0) or 0), reverse=True)
        primary = ranked[0] if ranked else None
        controllers = []
        beneficiaries = []
        if primary:
            controllers = list(primary.get("controllers") or [])
            beneficiaries = list(primary.get("beneficiaries") or [])
        return {
            "primary_bottleneck": primary,
            "secondary_bottlenecks": ranked[1:5],
            "controllers": controllers,
            "beneficiaries": beneficiaries,
            "what_fixes_it": list(primary.get("what_fixes_it") or []) if primary else [],
            "what_to_monitor": list(primary.get("what_to_monitor") or []) if primary else [],
        }

    @staticmethod
    def _beneficiaries(theme_name: str, beneficiaries: list[Any]) -> dict[str, Any]:
        rows = [row for row in beneficiaries if normalize_theme_id(getattr(row, "theme_name", "")) == normalize_theme_id(theme_name)]
        payloads = [row.to_api() if hasattr(row, "to_api") else {} for row in rows]
        ranked = sorted(payloads, key=lambda item: float(item.get("allocation_score", item.get("beneficiary_score", 0)) or 0), reverse=True)
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in ranked:
            by_type[str(row.get("beneficiary_type") or "Other")].append(row)
        return {
            "top_beneficiaries": ranked[:8],
            "controllers": by_type.get("Bottleneck Controller", [])[:5],
            "resolution_enablers": by_type.get("Resolution Enabler", [])[:5],
            "direct_beneficiaries": by_type.get("Direct Beneficiary", [])[:5],
            "indirect_beneficiaries": by_type.get("Indirect Beneficiary", [])[:5],
        }

    @staticmethod
    def _portfolio_context(theme_name: str, portfolios: list[Any]) -> dict[str, Any]:
        rows = []
        normalized = normalize_theme_id(theme_name)
        for portfolio in portfolios:
            for allocation in getattr(portfolio, "themes", []):
                if normalize_theme_id(getattr(allocation, "theme", "")) == normalized or normalize_theme_id(getattr(allocation, "theme_id", "")) == normalized:
                    rows.append(
                        {
                            "portfolio_type": portfolio.portfolio_type,
                            "portfolio_name": portfolio.portfolio_name,
                            "weight": allocation.weight,
                            "risk_profile": portfolio.risk_profile,
                            "portfolio_score": portfolio.portfolio_score,
                            "allocation_rationale": allocation.allocation_rationale,
                        }
                    )
        return {"portfolios": rows}

    @staticmethod
    def _supply_chain(
        theme_name: str,
        entities: list[Any],
        bottlenecks: list[Any],
        beneficiaries: list[Any],
        discovery: dict[str, Any],
        score: Any | None,
    ) -> dict[str, Any]:
        """Build 5-layer supply chain from theme_entities, grouped by entity_type.

        Returns a dict with a ``layers`` list.  Each layer contains:
        - layer_id       canonical layer id
        - layer_name     English layer name
        - entity_type    raw entity_type stored in DB
        - entities       list of {ticker, company, role, strength}
        - bottleneck     True if this layer has a known bottleneck controller
        """
        normalized = normalize_theme_id(theme_name)
        theme_entities = [e for e in entities if normalize_theme_id(getattr(e, "theme_name", "")) == normalized]

        # Build lookup: entity_type → list of entity records
        by_type: dict[str, list[Any]] = defaultdict(list)
        for entity in theme_entities:
            by_type[str(getattr(entity, "entity_type", "") or "").lower()].append(entity)

        # Build lookup of controller tickers for bottleneck marking
        theme_bottlenecks = [b for b in bottlenecks if normalize_theme_id(getattr(b, "theme_name", "")) == normalized]
        theme_beneficiaries = [b for b in beneficiaries if normalize_theme_id(getattr(b, "theme_name", "")) == normalized]
        controller_tickers: set[str] = set()
        for b in theme_bottlenecks:
            for ctrl in getattr(b, "controller_entities", []) or []:
                if isinstance(ctrl, dict):
                    ticker = str(ctrl.get("ticker") or "").upper()
                    if ticker:
                        controller_tickers.add(ticker)

        def _entity_row(e: Any) -> dict[str, Any]:
            ticker = str(getattr(e, "ticker", "") or "").upper()
            return {
                "ticker": ticker,
                "company": str(getattr(e, "company", "") or ticker),
                "role": str(getattr(e, "entity_type", "") or ""),
                "strength": float(getattr(e, "relationship_strength", 0) or 0),
                "is_bottleneck_controller": ticker in controller_tickers,
            }

        layers: list[dict[str, Any]] = []

        # Canonical ordered layers
        for layer_id, layer_name, type_keys in _SUPPLY_CHAIN_LAYERS:
            layer_entities: list[dict[str, Any]] = []
            seen_tickers: set[str] = set()
            for key in type_keys:
                for e in by_type.get(key, []):
                    row = _entity_row(e)
                    if row["ticker"] and row["ticker"] not in seen_tickers:
                        seen_tickers.add(row["ticker"])
                        layer_entities.append(row)
            if not layer_entities:
                continue
            layer_entities.sort(key=lambda r: r["strength"], reverse=True)
            layers.append({
                "layer_id": layer_id,
                "layer_name": layer_name,
                "entities": layer_entities[:6],
                "has_bottleneck": any(r["is_bottleneck_controller"] for r in layer_entities),
            })

        # Special role layers (controller / resolution_enabler)
        for layer_id, layer_name, type_keys in _ROLE_LAYERS:
            layer_entities = []
            seen_tickers = set()
            for key in type_keys:
                for e in by_type.get(key, []):
                    row = _entity_row(e)
                    if row["ticker"] and row["ticker"] not in seen_tickers:
                        seen_tickers.add(row["ticker"])
                        layer_entities.append(row)
            if not layer_entities:
                continue
            layer_entities.sort(key=lambda r: r["strength"], reverse=True)
            layers.append({
                "layer_id": layer_id,
                "layer_name": layer_name,
                "entities": layer_entities[:6],
                "has_bottleneck": layer_id == "bottleneck_controllers",
            })

        primary_bottleneck = max(
            theme_bottlenecks,
            key=lambda row: float(getattr(row, "bottleneck_strength", 0) or 0),
            default=None,
        )
        components = getattr(score, "score_components", {}) if score else {}
        risk_penalties = components.get("risk_penalties", {}) if isinstance(components.get("risk_penalties"), dict) else {}
        risks = [
            {
                "risk_type": "Valuation Risk",
                "value": max((float(getattr(row, "valuation_penalty", 0) or 0) for row in theme_beneficiaries), default=0.0),
                "explanation": "Maximum persisted beneficiary valuation penalty.",
            },
            {
                "risk_type": "Bubble Risk",
                "value": max((float(getattr(row, "bubble_penalty", 0) or 0) for row in theme_beneficiaries), default=0.0),
                "explanation": "Maximum persisted beneficiary bubble penalty.",
            },
            {
                "risk_type": "Crowding Risk",
                "value": float(risk_penalties.get("crowding_penalty", discovery.get("crowding_proxy", 0)) or 0),
                "explanation": "Theme Score Engine crowding output.",
            },
        ]
        if primary_bottleneck is not None:
            risks.append(
                {
                    "risk_type": "Supply Bottleneck",
                    "value": float(getattr(primary_bottleneck, "bottleneck_strength", 0) or 0),
                    "explanation": str(getattr(primary_bottleneck, "description", "") or "Persisted bottleneck evidence."),
                }
            )
            if str(getattr(primary_bottleneck, "bottleneck_type", "")) == "Regulatory Constraint":
                risks.append(
                    {
                        "risk_type": "Policy Risk",
                        "value": float(getattr(primary_bottleneck, "severity_score", 0) or 0),
                        "explanation": str(getattr(primary_bottleneck, "description", "") or "Persisted regulatory constraint."),
                    }
                )
        resolutions = []
        if primary_bottleneck is not None:
            primary_payload = primary_bottleneck.to_api()
            resolutions = [
                {
                    "resolution": item,
                    "resolution_probability": float(getattr(primary_bottleneck, "resolution_probability", 0) or 0),
                    "impact": float(getattr(primary_bottleneck, "impact_score", 0) or 0),
                    "timeline": str(getattr(primary_bottleneck, "timeline_status", "") or ""),
                }
                for item in primary_payload.get("what_fixes_it", [])
            ]
        return {
            "layers": layers,
            "bottleneck_controllers": list(controller_tickers),
            "dependency_paths": [],
            "risks": risks,
            "resolutions": resolutions,
        }


def normalize_theme_id(value: str) -> str:
    normalized = theme_id(str(value or ""))
    return "_".join(part for part in normalized.split("_") if part)


def get_theme_intelligence_detail(theme_id_value: str) -> dict[str, Any]:
    return ThemeIntelligenceAggregateService().get_theme(theme_id_value)
