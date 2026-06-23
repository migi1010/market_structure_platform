from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from fastapi.testclient import TestClient

import main
from theme_intelligence.aggregate import ThemeIntelligenceAggregateService
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository
from theme_intelligence.seeds import ThemeSeedLoader
from theme_intelligence.seeds import seed_loader as seed_loader_module
from theme_intelligence.storage.theme_repository import ThemeRepository


def test_seed_loader_idempotently_populates_existing_evidence_tables(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed.sqlite3")
    repository.initialize()
    loader = ThemeSeedLoader(repository=repository)

    first = loader.load()
    second = loader.load()

    catalysts = repository.get_catalysts()
    bottlenecks = repository.get_bottlenecks()
    beneficiaries = repository.get_beneficiary_scores()
    entities = repository.get_entities()

    assert first["themes_loaded"] == 10
    assert second["themes_loaded"] == 10
    assert len(catalysts) >= 20
    assert len(bottlenecks) >= 10
    assert len(beneficiaries) >= 40
    assert len(entities) >= 40
    assert len({(row.theme_name, row.catalyst_name, row.catalyst_type, row.source) for row in catalysts}) == len(catalysts)
    assert len({(row.theme_name, row.bottleneck_name, row.bottleneck_type) for row in bottlenecks}) == len(bottlenecks)


def test_seed_loader_marks_curated_source_and_improves_aggregate_sections(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_aggregate.sqlite3")
    repository.initialize()
    ThemeSeedLoader(repository=repository).load(recompute=False)

    payload = ThemeIntelligenceAggregateService(repository=repository).get_theme("glass_substrate")

    assert payload["theme_id"] == "glass_substrate"
    assert payload["catalysts"]["top_catalysts"]
    assert payload["bottlenecks"]["primary_bottleneck"] is not None
    assert payload["beneficiaries"]["top_beneficiaries"]
    assert all(row["source"] == "seed:curated" for row in payload["catalysts"]["top_catalysts"])


def test_seed_loader_applies_validated_lifecycle_hints_on_seed_only_recompute(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_lifecycle.sqlite3")
    ThemeSeedLoader(repository=repository).load()
    aggregate = ThemeIntelligenceAggregateService(repository=repository)

    assert aggregate.get_theme("hbm")["lifecycle"]["lifecycle_stage"] == "Growth"
    assert aggregate.get_theme("glass_substrate")["lifecycle"]["lifecycle_stage"] == "Early"
    assert aggregate.get_theme("ai_infrastructure")["lifecycle"]["lifecycle_stage"] == "Growth"
    assert aggregate.get_theme("hbm")["lifecycle"]["lifecycle_confidence"] == 70


def test_seed_reload_preserves_existing_seed_timestamps(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_timestamps.sqlite3")
    loader = ThemeSeedLoader(repository=repository)
    loader.load()
    first_catalyst = repository.get_catalysts()[0]
    first_entity = repository.get_entities()[0]

    loader.load()
    second_catalyst = repository.get_catalysts()[0]
    second_entity = repository.get_entities()[0]

    assert second_catalyst.created_at == first_catalyst.created_at
    assert second_catalyst.updated_at == first_catalyst.updated_at
    assert second_entity.updated_at == first_entity.updated_at


def test_seed_loader_builds_active_industrial_graph_snapshot(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_industrial_graph.sqlite3")

    result = ThemeSeedLoader(repository=repository).load(recompute=False)
    graph_repository = IndustrialGraphRepository(repository)
    snapshot = graph_repository.get_active_snapshot()

    assert result["themes_loaded"] == 10
    assert snapshot is not None
    assert snapshot.status == "active"
    assert snapshot.node_count > 0
    assert snapshot.edge_count > 0


def test_seed_loader_activates_complete_phase12_lineage(tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_phase12.sqlite3")

    result = ThemeSeedLoader(repository=repository).load(recompute=False)
    graph_repository = IndustrialGraphRepository(repository)
    graph = graph_repository.get_active_snapshot()
    controller = graph_repository.get_active_controller_snapshot()
    opportunity = graph_repository.get_active_opportunity_snapshot()
    packet_family = graph_repository.get_active_packet_family()

    assert graph is not None
    assert controller is not None
    assert opportunity is not None
    assert packet_family is not None
    assert controller.graph_snapshot_id == graph.id
    assert opportunity.graph_snapshot_id == graph.id
    assert opportunity.controller_snapshot_id == controller.id
    assert packet_family.graph_snapshot_id == graph.id
    assert packet_family.controller_snapshot_id == controller.id
    assert packet_family.opportunity_snapshot_id == opportunity.id
    assert result["phase12_status"] == "ready"
    assert result["graph_snapshot_id"] == graph.id
    assert result["controller_snapshot_id"] == controller.id
    assert result["opportunity_snapshot_id"] == opportunity.id
    assert result["packet_family_version"] == packet_family.packet_family_version


def test_seed_loader_reports_controller_failure_and_keeps_graph_active(
    tmp_path: Path, monkeypatch
) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_phase12_failure.sqlite3")

    class FailingControllerEngine:
        def __init__(self, _repository: ThemeRepository) -> None:
            pass

        def build_and_activate(self, _graph_build_version: str):
            raise ValueError("controller evidence invalid")

    monkeypatch.setattr(seed_loader_module, "ControllerEngine", FailingControllerEngine)

    with pytest.raises(
        RuntimeError,
        match="Phase 12 Controller activation failed.*controller evidence invalid",
    ):
        ThemeSeedLoader(repository=repository).load(recompute=False)

    graph_repository = IndustrialGraphRepository(repository)
    assert graph_repository.get_active_snapshot() is not None
    assert graph_repository.get_active_controller_snapshot() is None
    assert graph_repository.get_active_opportunity_snapshot() is None
    assert graph_repository.get_active_packet_family() is None


def test_startup_runs_seed_loader_before_accepting_requests(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main, "initialize_cache", lambda: calls.append("cache"))
    monkeypatch.setattr(main, "_run_seed_loader", lambda recompute=True: calls.append("seed"))
    monkeypatch.setattr(main.BACKGROUND_EXECUTOR, "submit", lambda *args, **kwargs: calls.append("background"))

    async def exercise_lifespan() -> None:
        async with main.lifespan(main.app):
            calls.append("ready")

    asyncio.run(exercise_lifespan())

    assert calls[:3] == ["cache", "seed", "ready"]
    assert "background" not in calls


def test_admin_seed_status_contract(monkeypatch, tmp_path: Path) -> None:
    repository = ThemeRepository(tmp_path / "theme_seed_admin.sqlite3")
    result = ThemeSeedLoader(repository=repository).load()
    monkeypatch.setattr(main, "ThemeRepository", lambda: repository, raising=False)
    monkeypatch.setitem(main._SEED_STATE, "loaded", True)
    monkeypatch.setitem(main._SEED_STATE, "loaded_at", "2026-06-11T00:00:00Z")
    monkeypatch.setitem(main._SEED_STATE, "result", result)

    response = TestClient(main.app).get("/api/theme/admin/seed/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["seeded_themes"] == 10
    assert payload["seed_version"]
    assert payload["last_loaded"] == "2026-06-11T00:00:00Z"
    assert payload["coverage"]["catalysts"] >= 20
    assert payload["coverage"]["bottlenecks"] >= 10
    assert payload["coverage"]["beneficiaries"] >= 40
