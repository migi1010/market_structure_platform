from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from theme_intelligence.storage.theme_repository import ThemeRepository

from .graph_models import content_hash
from .theme_scout_models import ScoutEvidence


MANIFEST_SCHEMA_VERSION = "theme-scout-evidence-manifest-v1"
DOMAIN_PRECEDENCE = (
    "Constraint", "Equipment", "Material", "Process", "Technology", "Company",
)


def derive_evidence_domain(node_types: Iterable[str]) -> str:
    values = set(node_types)
    return next((domain for domain in DOMAIN_PRECEDENCE if domain in values), "Other")


@dataclass(frozen=True)
class ThemeScoutEvidenceManifest:
    schema_version: str
    graph_build_version: str
    graph_checksum: str
    source_watermark: str
    evidence_bundle_checksum: str
    evidence: tuple[ScoutEvidence, ...]

    def recalculate_checksum(self) -> str:
        return content_hash([row.to_dict() for row in self.evidence])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "graph_build_version": self.graph_build_version,
            "graph_checksum": self.graph_checksum,
            "source_watermark": self.source_watermark,
            "evidence_bundle_checksum": self.evidence_bundle_checksum,
            "evidence": [row.to_dict() for row in self.evidence],
        }


def export_active_graph_evidence_manifest(
    repository: ThemeRepository,
) -> ThemeScoutEvidenceManifest:
    repository.initialize()
    with repository._connect() as conn:
        snapshot = conn.execute(
            """
            SELECT build_version, checksum, created_at
            FROM graph_snapshots
            WHERE status='active'
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        if snapshot is None:
            raise ValueError("active graph snapshot is required")
        rows = conn.execute(
            """
            SELECT ge.id evidence_id, ge.source_type, ge.source_record_id,
                   ge.content_hash, ge.citation, ge.observed_date,
                   e.relationship_type,
                   source.node_type source_node_type,
                   source.canonical_key source_node_key,
                   source.display_name source_node_name,
                   target.node_type target_node_type,
                   target.canonical_key target_node_key,
                   target.display_name target_node_name
            FROM graph_evidence ge
            JOIN graph_edge_evidence gee ON gee.evidence_id=ge.id
            JOIN graph_edges e ON e.id=gee.edge_id
            JOIN graph_nodes source ON source.id=e.source_node_id
            JOIN graph_nodes target ON target.id=e.target_node_id
            WHERE e.build_version=?
              AND ge.review_status='approved'
              AND ge.citation<>''
              AND ge.observed_date IS NOT NULL
            ORDER BY ge.id, e.relationship_type, source.canonical_key,
                     target.canonical_key
            """,
            (str(snapshot["build_version"]),),
        ).fetchall()

    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        key = int(row["evidence_id"])
        item = grouped.setdefault(key, {"row": row, "contexts": []})
        item["contexts"].append({
            "relationship_type": str(row["relationship_type"]),
            "source_node": {
                "type": str(row["source_node_type"]),
                "key": str(row["source_node_key"]),
                "name": str(row["source_node_name"]),
            },
            "target_node": {
                "type": str(row["target_node_type"]),
                "key": str(row["target_node_key"]),
                "name": str(row["target_node_name"]),
            },
        })

    evidence: list[ScoutEvidence] = []
    for evidence_id, item in sorted(grouped.items()):
        row = item["row"]
        contexts = tuple(item["contexts"])
        node_types = {
            context[side]["type"]
            for context in contexts
            for side in ("source_node", "target_node")
        }
        relationships = sorted({context["relationship_type"] for context in contexts})
        evidence.append(ScoutEvidence(
            evidence_id=f"graph_evidence:{evidence_id}",
            source_table="graph_evidence",
            source_record_id=str(evidence_id),
            source_type=str(row["source_type"]),
            source_timestamp=str(row["observed_date"]),
            source_identifier=str(row["source_record_id"]),
            citation=str(row["citation"]),
            domain_type=derive_evidence_domain(node_types),
            cluster_key=relationships[0].lower() if relationships else "graph-evidence",
            source_value={
                "graph_build_version": str(snapshot["build_version"]),
                "relationships": relationships,
                "contexts": list(contexts),
            },
            content_hash=str(row["content_hash"]),
        ))
    ordered = tuple(sorted(evidence, key=lambda value: value.evidence_id))
    checksum = content_hash([row.to_dict() for row in ordered])
    return ThemeScoutEvidenceManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        graph_build_version=str(snapshot["build_version"]),
        graph_checksum=str(snapshot["checksum"]),
        source_watermark=str(snapshot["created_at"]),
        evidence_bundle_checksum=checksum,
        evidence=ordered,
    )


def load_evidence_manifest(path: Path | str) -> ThemeScoutEvidenceManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = {
        "schema_version", "graph_build_version", "graph_checksum",
        "source_watermark", "evidence_bundle_checksum", "evidence",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unsupported manifest fields: {', '.join(unknown)}")
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported evidence manifest schema")
    evidence = tuple(ScoutEvidence(
        evidence_id=str(row["evidence_id"]),
        source_table=str(row["source_table"]),
        source_record_id=str(row["source_record_id"]),
        source_type=str(row["source_type"]),
        source_timestamp=str(row["source_timestamp"]),
        source_identifier=str(row["source_identifier"]),
        citation=str(row["citation"]),
        domain_type=str(row["domain_type"]),
        cluster_key=str(row["cluster_key"]),
        source_value=dict(row["source_value"]),
        content_hash=str(row["content_hash"]),
        availability_state=str(row.get("availability_state", "available")),
    ) for row in payload.get("evidence", []))
    manifest = ThemeScoutEvidenceManifest(
        schema_version=str(payload["schema_version"]),
        graph_build_version=str(payload["graph_build_version"]),
        graph_checksum=str(payload["graph_checksum"]),
        source_watermark=str(payload["source_watermark"]),
        evidence_bundle_checksum=str(payload["evidence_bundle_checksum"]),
        evidence=evidence,
    )
    if manifest.recalculate_checksum() != manifest.evidence_bundle_checksum:
        raise ValueError("evidence manifest checksum mismatch")
    return manifest


def write_evidence_manifest(
    manifest: ThemeScoutEvidenceManifest, path: Path | str
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

