from __future__ import annotations

from dataclasses import replace

from theme_intelligence.storage.theme_repository import ThemeRepository

from .graph_models import utc_now
from .theme_scout_builder import ThemeScoutBuilder
from .theme_scout_models import (
    ScoutEvidence,
    ThemeScoutBuild,
    ThemeScoutProposalProvider,
    ThemeScoutSnapshot,
)
from .theme_scout_repository import ThemeScoutRepository
from .theme_scout_validator import ThemeScoutValidator
from .theme_scout_manifest import (
    ThemeScoutEvidenceManifest,
    export_active_graph_evidence_manifest,
)


class ThemeScoutProviderUnavailable(RuntimeError):
    pass


class ThemeScoutEngine:
    def __init__(
        self,
        repository: ThemeRepository | None = None,
        *,
        provider: ThemeScoutProposalProvider | None = None,
    ) -> None:
        self.theme_repository = repository or ThemeRepository()
        self.repository = ThemeScoutRepository(self.theme_repository)
        self.provider = provider
        self.builder = ThemeScoutBuilder()
        self.validator = ThemeScoutValidator()

    def _persisted_evidence(self, source_watermark: str) -> tuple[ScoutEvidence, ...]:
        self.theme_repository.initialize()
        with self.theme_repository._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_type, source_record_id, content_hash,
                       citation, observed_date, review_status
                FROM graph_evidence
                WHERE review_status='approved'
                  AND citation<>''
                  AND observed_date IS NOT NULL
                  AND observed_date<=?
                ORDER BY source_type, source_record_id, content_hash
                """,
                (source_watermark,),
            ).fetchall()
        return tuple(
            ScoutEvidence(
                evidence_id=f"graph_evidence:{row['id']}",
                source_table="graph_evidence",
                source_record_id=str(row["id"]),
                source_type=str(row["source_type"]),
                source_timestamp=str(row["observed_date"]),
                source_identifier=str(row["source_record_id"]),
                citation=str(row["citation"]),
                domain_type="Other",
                cluster_key="persisted-graph-evidence",
                source_value={
                    "source_record_id": str(row["source_record_id"]),
                    "review_status": str(row["review_status"]),
                },
                content_hash=str(row["content_hash"]),
            )
            for row in rows
        )

    def build(
        self,
        source_watermark: str | None = None,
        *,
        manifest: ThemeScoutEvidenceManifest | None = None,
    ) -> ThemeScoutBuild:
        if self.provider is None:
            raise ThemeScoutProviderUnavailable(
                "Theme Scout proposal provider is not configured"
            )
        if manifest is None:
            try:
                manifest = export_active_graph_evidence_manifest(self.theme_repository)
            except ValueError:
                manifest = None
        watermark = (
            source_watermark
            or (manifest.source_watermark if manifest else utc_now())
        )
        evidence = (
            manifest.evidence
            if manifest is not None
            else self._persisted_evidence(watermark)
        )
        document = getattr(self.provider, "document", None)
        build_proposal = getattr(self.provider, "build_proposal", None)
        if callable(build_proposal) and manifest is not None:
            document = build_proposal(manifest)
        if document is not None and manifest is not None:
            if document.graph_build_version != manifest.graph_build_version:
                raise ValueError("proposal graph build version mismatch")
            if document.evidence_bundle_checksum != manifest.evidence_bundle_checksum:
                raise ValueError("proposal evidence checksum mismatch")
        proposal = document.proposal if document is not None else self.provider.propose(evidence)
        build = self.builder.build(evidence, proposal, watermark)
        if document is not None:
            build = replace(build, proposal_checksum=document.checksum)
        if manifest is not None and build.evidence_bundle_checksum != manifest.evidence_bundle_checksum:
            raise ValueError("built evidence checksum mismatch")
        self.validator.validate(build)
        return build

    def build_and_activate(
        self, source_watermark: str | None = None
    ) -> ThemeScoutSnapshot:
        build = self.build(source_watermark)
        staged = self.repository.stage(build)
        return self.repository.activate(staged.scout_version)
