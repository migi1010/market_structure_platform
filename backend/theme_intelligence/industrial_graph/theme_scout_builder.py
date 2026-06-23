from __future__ import annotations

from dataclasses import replace

from .graph_models import content_hash
from .theme_scout_models import (
    DEFAULT_SCOUT_WEIGHTS,
    ScoutEvidence,
    ThemeScoutBuild,
    ThemeScoutCandidate,
    ThemeScoutMetrics,
    ThemeScoutProposal,
    ThemeScoutReadiness,
    canonical_candidate_key,
)


class ThemeScoutBuilder:
    algorithm_version = "theme-scout-v1.1-novelty-pending"

    def build(
        self,
        evidence: tuple[ScoutEvidence, ...],
        proposal: ThemeScoutProposal,
        source_watermark: str,
    ) -> ThemeScoutBuild:
        evidence_by_id = {
            row.evidence_id: row
            for row in sorted(evidence, key=lambda item: item.evidence_id)
        }
        candidates: list[ThemeScoutCandidate] = []
        for proposed in proposal.candidates:
            referenced_ids = set(proposed.evidence_ids)
            referenced_ids.update(proposed.bottleneck_evidence_ids)
            for cluster in proposed.signal_clusters:
                referenced_ids.update(cluster.evidence_ids)
            for path in proposed.paths:
                referenced_ids.update(path.evidence_ids)
            for influence in proposed.influence_map:
                referenced_ids.update(influence.evidence_ids)
            unknown = sorted(referenced_ids - set(evidence_by_id))
            if unknown:
                raise ValueError(
                    f"unknown proposal evidence reference: {', '.join(unknown)}"
                )
            selected = tuple(
                evidence_by_id[evidence_id]
                for evidence_id in proposed.evidence_ids
            )
            selected = tuple(
                {row.evidence_id: row for row in selected}.values()
            )
            domains = {row.domain_type for row in selected if row.domain_type != "Other"}
            source_types = {row.source_type for row in selected}
            clusters = tuple(
                cluster
                for cluster in proposed.signal_clusters
            )
            bottleneck_ids = set(proposed.bottleneck_evidence_ids)
            bottleneck = min(
                100.0,
                60.0 * len(bottleneck_ids & set(proposed.evidence_ids))
                + 20.0 * len({
                    row.cluster_key for row in selected
                    if row.evidence_id in bottleneck_ids
                }),
            )
            confidence = min(
                100.0,
                40.0 * min(1.0, len(selected) / 4)
                + 30.0 * min(1.0, len(source_types) / 3)
                + 20.0 * min(1.0, len(clusters) / 2)
                + (10.0 if selected and all(row.citation for row in selected) else 0.0),
            )
            novelty = 0.0
            velocity = min(100.0, len({row.source_timestamp for row in selected}) * 20.0)
            breadth = len(domains) / 6 * 100.0
            capital = min(
                100.0,
                sum(
                    25.0
                    for row in selected
                    if any(
                        token in row.source_type.lower()
                        or token in str(row.source_value).lower()
                        for token in ("capital", "funding", "investment", "capex")
                    )
                ),
            )
            serendipity = min(
                100.0,
                (len(domains) / 6 * 100.0)
                * min(1.0, len(clusters) / 2)
                * min(1.0, len(source_types) / 3),
            )
            normalized = {
                "novelty": round(novelty, 4),
                "velocity": round(velocity, 4),
                "breadth": round(breadth, 4),
                "capital": round(capital, 4),
                "bottleneck": round(bottleneck, 4),
            }
            theme_score = sum(
                normalized[name] * weight
                for name, weight in DEFAULT_SCOUT_WEIGHTS.items()
            )
            coverage = len(domains) / 6 * 100.0
            metrics = ThemeScoutMetrics(
                confidence=round(confidence, 4),
                novelty=normalized["novelty"],
                velocity=normalized["velocity"],
                breadth=normalized["breadth"],
                capital=normalized["capital"],
                bottleneck=normalized["bottleneck"],
                serendipity=round(serendipity, 4),
                theme_score=round(theme_score, 4),
                coverage=round(coverage, 4),
                raw_values={
                    "unique_evidence": len(selected),
                    "unique_sources": len(source_types),
                    "domain_count": len(domains),
                    "cluster_count": len(clusters),
                    "bottleneck_evidence_count": len(bottleneck_ids),
                    "novelty_availability_state": "unavailable",
                    "novelty_methodology_state": "pending_methodology",
                },
                normalized_values=normalized,
                applied_weights=DEFAULT_SCOUT_WEIGHTS,
            )
            candidates.append(ThemeScoutCandidate(
                candidate_key=canonical_candidate_key(proposed.name),
                name=proposed.name,
                description=proposed.description,
                status=proposed.status,
                metrics=metrics,
                readiness=ThemeScoutReadiness.from_evidence(selected),
                evidence=selected,
                signal_clusters=clusters,
                paths=proposed.paths,
                influence_map=proposed.influence_map,
                rank=1,
                generated_summary=proposed.generated_summary,
            ))
        ordered = sorted(
            candidates,
            key=lambda row: (
                -row.metrics.bottleneck,
                -row.metrics.confidence,
                -row.metrics.coverage,
                -row.readiness.overall,
                row.candidate_key,
            ),
        )
        ranked = tuple(replace(row, rank=index) for index, row in enumerate(ordered, 1))
        return ThemeScoutBuild(
            algorithm_version=self.algorithm_version,
            provider_name=proposal.provider_name,
            provider_model=proposal.provider_model,
            prompt_version=proposal.prompt_version,
            source_watermark=source_watermark,
            evidence_bundle_checksum=content_hash([
                row.to_dict() for row in sorted(evidence_by_id.values(), key=lambda item: item.evidence_id)
            ]),
            proposal_checksum=content_hash(proposal.to_dict()),
            candidates=ranked,
            weights=DEFAULT_SCOUT_WEIGHTS,
        )
