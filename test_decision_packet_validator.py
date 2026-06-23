from dataclasses import replace
from pathlib import Path

import pytest

from test_decision_packet_builder import packet_repository

from theme_intelligence.industrial_graph.decision_packet_builder import DecisionPacketBuilder
from theme_intelligence.industrial_graph.decision_packet_validator import (
    DecisionPacketValidationError,
    DecisionPacketValidator,
)
from theme_intelligence.industrial_graph.graph_repository import IndustrialGraphRepository


def test_validator_rejects_missing_paths(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    damaged = replace(
        build,
        packets=(replace(build.packets[0], paths=()), *build.packets[1:]),
    )
    with pytest.raises(DecisionPacketValidationError, match="missing reasoning paths"):
        DecisionPacketValidator().validate(damaged, IndustrialGraphRepository(repository))


def test_validator_rejects_lineage_mismatch(tmp_path: Path) -> None:
    repository, _, _, opportunity = packet_repository(tmp_path)
    build = DecisionPacketBuilder(repository).build(opportunity.opportunity_version)
    with pytest.raises(DecisionPacketValidationError, match="snapshot"):
        DecisionPacketValidator().validate(
            replace(build, graph_snapshot_id=build.graph_snapshot_id + 99),
            IndustrialGraphRepository(repository),
        )
