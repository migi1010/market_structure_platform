from __future__ import annotations

import sqlite3
from dataclasses import replace
from statistics import mean
from typing import Any

from theme_intelligence.beneficiaries.beneficiary_models import BeneficiaryScoreRecord
from theme_intelligence.bottlenecks.bottleneck_models import BottleneckRecord
from theme_intelligence.discovery.discovery_ranking import rank_discovery_themes
from theme_intelligence.graph.graph_engine import GraphEngine
from theme_intelligence.industrial_graph.controller_engine import ControllerEngine
from theme_intelligence.industrial_graph.decision_packet_engine import DecisionPacketEngine
from theme_intelligence.industrial_graph.graph_snapshot import IndustrialGraphSnapshotService
from theme_intelligence.industrial_graph.opportunity_engine import OpportunityEngine
from theme_intelligence.models import CatalystRecord, ThemeBeneficiary, ThemeEntity, clamp_score, utc_now_iso
from theme_intelligence.portfolio.portfolio_engine import PortfolioEngine
from theme_intelligence.storage.theme_repository import ThemeRepository
from theme_intelligence.theme_score.theme_score_engine import ThemeScoreEngine

from .seed_validator import validate_theme_seeds
from .theme_seed_data import TARGET_SEED_THEMES
from .theme_seed_models import SeedBeneficiary, SeedBottleneck, SeedCatalyst, ThemeSeed


SEED_SOURCE = "seed:curated"
SEED_VERSION = "10.11.1"


class ThemeSeedLoader:
    def __init__(self, repository: ThemeRepository | None = None, themes: tuple[ThemeSeed, ...] = TARGET_SEED_THEMES) -> None:
        self.repository = repository or ThemeRepository()
        self.themes = themes

    def load(self, recompute: bool = True, build_industrial_graph: bool = True) -> dict[str, Any]:
        errors = validate_theme_seeds(self.themes)
        if errors:
            raise ValueError("; ".join(errors))
        self.repository.initialize()
        entities = self._entities()
        beneficiaries = self._beneficiaries()
        catalysts = self._catalysts()
        bottlenecks = self._bottlenecks()
        beneficiary_scores = self._beneficiary_scores()
        entities = self._preserve_entity_timestamps(entities)
        beneficiaries = self._preserve_beneficiary_timestamps(beneficiaries)
        catalysts = self._preserve_catalyst_timestamps(catalysts)
        bottlenecks = self._preserve_bottleneck_timestamps(bottlenecks)
        beneficiary_scores = self._preserve_beneficiary_score_timestamps(beneficiary_scores)
        self.repository.save_entities(entities)
        self.repository.save_beneficiaries(beneficiaries)
        self.repository.save_catalysts(catalysts)
        self.repository.save_bottlenecks(bottlenecks)
        self.repository.save_beneficiary_scores(beneficiary_scores)
        if recompute:
            self._recompute_outputs()
        graph_result = GraphEngine(self.repository).rebuild()
        phase12_result: dict[str, Any] = {}
        if build_industrial_graph:
            phase12_result = self._activate_phase12_lineage()
        invalidated = self.invalidate_theme_caches()
        return {
            "themes_loaded": len(self.themes),
            "entities": len(entities),
            "beneficiaries": len(beneficiaries),
            "catalysts": len(catalysts),
            "bottlenecks": len(bottlenecks),
            "beneficiary_scores": len(beneficiary_scores),
            "graph_edges": graph_result["edge_count"],
            "theme_overlaps": graph_result["overlap_count"],
            "cache_keys_invalidated": invalidated,
            "source": SEED_SOURCE,
            "seed_version": SEED_VERSION,
            **phase12_result,
        }

    def _activate_phase12_lineage(self) -> dict[str, Any]:
        graph = IndustrialGraphSnapshotService(self.repository).build_and_activate()
        try:
            controller = ControllerEngine(self.repository).build_and_activate(
                graph.build_version
            )
        except Exception as exc:
            raise RuntimeError(
                f"Phase 12 Controller activation failed for graph snapshot {graph.id}: {exc}"
            ) from exc
        try:
            opportunity = OpportunityEngine(self.repository).build_and_activate(
                controller.controller_version
            )
        except Exception as exc:
            raise RuntimeError(
                f"Phase 12 Opportunity activation failed for controller snapshot {controller.id}: {exc}"
            ) from exc
        try:
            packet_family = DecisionPacketEngine(self.repository).build_and_activate(
                opportunity.opportunity_version
            )
        except Exception as exc:
            raise RuntimeError(
                f"Phase 12 Decision Packet activation failed for opportunity snapshot {opportunity.id}: {exc}"
            ) from exc
        return {
            "phase12_status": "ready",
            "graph_snapshot_id": graph.id,
            "graph_build_version": graph.build_version,
            "controller_snapshot_id": controller.id,
            "controller_version": controller.controller_version,
            "opportunity_snapshot_id": opportunity.id,
            "opportunity_version": opportunity.opportunity_version,
            "packet_family_version": packet_family.packet_family_version,
            "decision_packet_count": packet_family.packet_count,
        }

    def _entities(self) -> list[ThemeEntity]:
        rows: list[ThemeEntity] = []
        now = utc_now_iso()
        seen: set[tuple[str, str, str]] = set()
        for theme in self.themes:
            for role, beneficiaries in theme.supply_chain_roles.items():
                for item in beneficiaries:
                    key = (theme.name, role, item.ticker.upper())
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(ThemeEntity(theme.name, role, item.company_name, item.ticker.upper(), item.relationship_strength, now))
            for item in [*theme.controllers, *theme.resolution_enablers]:
                entity_type = "controller" if item.beneficiary_type == "Bottleneck Controller" else "resolution_enabler"
                key = (theme.name, entity_type, item.ticker.upper())
                if key in seen:
                    continue
                seen.add(key)
                rows.append(ThemeEntity(theme.name, entity_type, item.company_name, item.ticker.upper(), item.relationship_strength, now))
        return rows

    def _beneficiaries(self) -> list[ThemeBeneficiary]:
        rows: list[ThemeBeneficiary] = []
        now = utc_now_iso()
        seen: set[tuple[str, str]] = set()
        for theme in self.themes:
            for item in [*theme.seed_beneficiaries, *theme.controllers, *theme.resolution_enablers]:
                key = (theme.name, item.ticker.upper())
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    ThemeBeneficiary(
                        theme.name,
                        item.ticker.upper(),
                        item.company_name,
                        item.relationship_strength,
                        item.relationship_strength,
                        now,
                    )
                )
        return rows

    def _catalysts(self) -> list[CatalystRecord]:
        rows: list[CatalystRecord] = []
        now = utc_now_iso()
        for theme in self.themes:
            for item in theme.seed_catalysts:
                strength = _catalyst_strength(item)
                rows.append(
                    CatalystRecord(
                        theme_name=theme.name,
                        catalyst_name=item.name,
                        catalyst_type=item.catalyst_type,
                        source=SEED_SOURCE,
                        impact_score=item.impact_score,
                        confidence_score=item.confidence_score,
                        description=item.description,
                        novelty_score=item.novelty_score,
                        duration_score=item.duration_score,
                        stage_relevance=item.stage_relevance,
                        catalyst_strength=strength,
                        cluster_key=_cluster_key(theme.theme_id, item.name, item.catalyst_type),
                        timeline_status=item.timeline_status,
                        polarity=item.polarity,
                        created_at=now,
                        updated_at=now,
                    )
                )
        return rows

    def _bottlenecks(self) -> list[BottleneckRecord]:
        rows: list[BottleneckRecord] = []
        now = utc_now_iso()
        for theme in self.themes:
            controllers = [_beneficiary_api(row) for row in theme.controllers]
            beneficiary_payload = [_beneficiary_api(row) for row in theme.seed_beneficiaries[:5]]
            for item in theme.seed_bottlenecks:
                rows.append(
                    BottleneckRecord(
                        theme_name=theme.name,
                        bottleneck_name=item.name,
                        bottleneck_type=item.bottleneck_type,
                        severity_score=item.severity_score,
                        duration_score=item.duration_score,
                        resolution_probability=item.resolution_probability,
                        impact_score=item.impact_score,
                        bottleneck_strength=_bottleneck_strength(item),
                        controller_entities=controllers,
                        beneficiaries=beneficiary_payload,
                        timeline_status=item.timeline_status,
                        description=item.description,
                        evidence=[{"source": SEED_SOURCE, "description": item.description}],
                        updated_at=now,
                    )
                )
        return rows

    def _beneficiary_scores(self) -> list[BeneficiaryScoreRecord]:
        rows: list[BeneficiaryScoreRecord] = []
        now = utc_now_iso()
        seen: set[tuple[str, str, str]] = set()
        for theme in self.themes:
            for item in [*theme.seed_beneficiaries, *theme.controllers, *theme.resolution_enablers]:
                key = (theme.name, item.ticker.upper(), item.beneficiary_type)
                if key in seen:
                    continue
                seen.add(key)
                exposure = clamp_score(item.relationship_strength)
                leverage = clamp_score(item.relationship_strength + (8 if item.beneficiary_type in {"Bottleneck Controller", "Resolution Enabler"} else 0))
                dependency = clamp_score(item.relationship_strength + (5 if theme.name.lower() in item.role.lower() else 0))
                beneficiary_score = clamp_score(exposure * 0.45 + leverage * 0.30 + dependency * 0.25)
                allocation_score = clamp_score(beneficiary_score * 0.90)
                rows.append(
                    BeneficiaryScoreRecord(
                        theme_name=theme.name,
                        ticker=item.ticker.upper(),
                        company_name=item.company_name,
                        beneficiary_type=item.beneficiary_type,
                        exposure_score=exposure,
                        leverage_score=leverage,
                        dependency_score=dependency,
                        valuation_penalty=0.0,
                        bubble_penalty=0.0,
                        beneficiary_score=beneficiary_score,
                        allocation_score=allocation_score,
                        role=f"{item.role} ({SEED_SOURCE})",
                        updated_at=now,
                        why_benefits=f"{item.company_name} is curated as {item.role} for {theme.name}.",
                        risk_factors=list(theme.risk_notes[:2]),
                        allocation_reason="Curated seed relationship; allocation score remains engine-derived downstream.",
                    )
                )
        return rows

    def _recompute_outputs(self) -> None:
        catalysts = self.repository.get_catalysts()
        entities = self.repository.get_entities()
        beneficiaries = self.repository.get_beneficiaries()
        bottlenecks = self.repository.get_bottlenecks()
        beneficiary_scores = self.repository.get_beneficiary_scores()
        ranked = [row.to_api() for row in rank_discovery_themes([], catalysts, entities, beneficiaries, bottlenecks=bottlenecks, beneficiary_scores=beneficiary_scores)]
        lifecycle_hints = {theme.name: theme.lifecycle_hint for theme in self.themes}
        for row in ranked:
            hint = lifecycle_hints.get(row["name"])
            if hint is None:
                continue
            row["lifecycle_stage"] = hint.stage
            row["lifecycle_confidence"] = clamp_score(hint.confidence)
            row["expected_next_stage"] = hint.expected_next_stage
            row["lifecycle_reason"] = hint.rationale
        self.repository.upsert_discovery_scores(ranked)
        for row in ranked:
            self.repository.update_lifecycle(row["name"], row)
            self.repository.append_score_history(
                row["name"],
                {
                    "timestamp": row["updated_at"],
                    "lifecycle_stage": row["lifecycle_stage"],
                    "lifecycle_confidence": row["lifecycle_confidence"],
                    "expected_next_stage": row["expected_next_stage"],
                    "final_ai_score": row["ai_score"],
                    "emerging_score": row["emerging_score"],
                    "catalyst_score": row["catalyst_score"],
                    "entity_strength_score": row["entity_strength_score"],
                    "crowding_proxy": row["crowding_proxy"],
                    "source": SEED_SOURCE,
                },
            )
        ThemeScoreEngine(repository=self.repository).get_scores()
        PortfolioEngine(repository=self.repository).get_portfolios(use_cache=False)

    def _preserve_entity_timestamps(self, rows: list[ThemeEntity]) -> list[ThemeEntity]:
        existing = {(row.theme_name, row.entity_type, row.ticker): row for row in self.repository.get_entities()}
        return [
            replace(row, updated_at=prior.updated_at)
            if (prior := existing.get((row.theme_name, row.entity_type, row.ticker)))
            and self._same(prior, row, {"updated_at"})
            else row
            for row in rows
        ]

    def _preserve_beneficiary_timestamps(self, rows: list[ThemeBeneficiary]) -> list[ThemeBeneficiary]:
        existing = {(row.theme_name, row.ticker): row for row in self.repository.get_beneficiaries()}
        return [
            replace(row, updated_at=prior.updated_at)
            if (prior := existing.get((row.theme_name, row.ticker)))
            and self._same(prior, row, {"updated_at"})
            else row
            for row in rows
        ]

    def _preserve_catalyst_timestamps(self, rows: list[CatalystRecord]) -> list[CatalystRecord]:
        existing = {
            (row.theme_name, row.cluster_key, row.catalyst_type, row.source): row
            for row in self.repository.get_catalysts()
        }
        return [
            replace(row, created_at=prior.created_at, updated_at=prior.updated_at)
            if (prior := existing.get((row.theme_name, row.cluster_key, row.catalyst_type, row.source)))
            and self._same(prior, row, {"created_at", "updated_at"})
            else row
            for row in rows
        ]

    def _preserve_bottleneck_timestamps(self, rows: list[BottleneckRecord]) -> list[BottleneckRecord]:
        existing = {
            (row.theme_name, row.bottleneck_name, row.bottleneck_type): row
            for row in self.repository.get_bottlenecks()
        }
        return [
            replace(row, updated_at=prior.updated_at)
            if (prior := existing.get((row.theme_name, row.bottleneck_name, row.bottleneck_type)))
            and self._same(prior, row, {"updated_at"})
            else row
            for row in rows
        ]

    def _preserve_beneficiary_score_timestamps(self, rows: list[BeneficiaryScoreRecord]) -> list[BeneficiaryScoreRecord]:
        existing = {
            (row.theme_name, row.ticker, row.beneficiary_type): row
            for row in self.repository.get_beneficiary_scores()
        }
        persisted_fields = {
            "theme_name", "ticker", "company_name", "beneficiary_type", "exposure_score",
            "leverage_score", "dependency_score", "valuation_penalty", "bubble_penalty",
            "beneficiary_score", "allocation_score", "role",
        }
        return [
            replace(row, updated_at=prior.updated_at)
            if (prior := existing.get((row.theme_name, row.ticker, row.beneficiary_type)))
            and all(getattr(prior, field) == getattr(row, field) for field in persisted_fields)
            else row
            for row in rows
        ]

    @staticmethod
    def _same(left: Any, right: Any, excluded: set[str]) -> bool:
        left_values = {key: value for key, value in vars(left).items() if key not in excluded}
        right_values = {key: value for key, value in vars(right).items() if key not in excluded}
        return left_values == right_values

    def invalidate_theme_caches(self) -> int:
        try:
            with sqlite3.connect(self.repository.db_path) as conn:
                rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'kv_cache'").fetchall()
                if not rows:
                    return 0
                before = int(conn.execute("SELECT COUNT(*) FROM kv_cache").fetchone()[0])
                conn.execute("DELETE FROM kv_cache WHERE cache_key LIKE '%theme_%' OR cache_key LIKE '%theme:%' OR cache_key LIKE '%theme%'")
                conn.commit()
                after = int(conn.execute("SELECT COUNT(*) FROM kv_cache").fetchone()[0])
                return max(0, before - after)
        except sqlite3.Error:
            return 0


def _catalyst_strength(item: SeedCatalyst) -> float:
    return clamp_score(item.impact_score * 0.35 + item.confidence_score * 0.25 + item.novelty_score * 0.20 + item.duration_score * 0.15 + item.stage_relevance * 0.05)


def _bottleneck_strength(item: SeedBottleneck) -> float:
    return clamp_score(item.severity_score * 0.35 + item.duration_score * 0.25 + item.impact_score * 0.25 + (100.0 - item.resolution_probability) * 0.15)


def _cluster_key(theme_id: str, name: str, item_type: str) -> str:
    return f"{theme_id}:{_slug(name)}:{_slug(item_type)}"


def _slug(value: str) -> str:
    return "_".join(part for part in value.lower().replace("/", " ").replace("-", " ").split() if part)


def _beneficiary_api(row: SeedBeneficiary) -> dict[str, Any]:
    return {
        "ticker": row.ticker.upper(),
        "company_name": row.company_name,
        "role": row.role,
        "beneficiary_type": row.beneficiary_type,
        "relationship_strength": clamp_score(row.relationship_strength),
        "source": SEED_SOURCE,
    }


def load_theme_seed_data(repository: ThemeRepository | None = None, recompute: bool = True) -> dict[str, Any]:
    return ThemeSeedLoader(repository=repository).load(recompute=recompute)
