from __future__ import annotations

from .theme_scout_models import ThemeScoutBuild, candidate_checksum, scout_build_checksum


class ThemeScoutValidator:
    def validate(self, build: ThemeScoutBuild) -> None:
        errors: list[str] = []
        keys = [row.candidate_key for row in build.candidates]
        ranks = [row.rank for row in build.candidates]
        if len(keys) != len(set(keys)):
            errors.append("duplicate candidate identity")
        if len(ranks) != len(set(ranks)):
            errors.append("duplicate candidate rank")
        for candidate in build.candidates:
            evidence_ids = {row.evidence_id for row in candidate.evidence}
            cluster_keys = {row.cluster_key for row in candidate.signal_clusters}
            for row in candidate.signal_clusters:
                if not set(row.evidence_ids) <= evidence_ids:
                    errors.append(f"cluster missing evidence:{candidate.candidate_key}")
            for row in candidate.paths:
                if not set(row.evidence_ids) <= evidence_ids:
                    errors.append(f"path missing evidence:{candidate.candidate_key}")
            for row in candidate.influence_map:
                if not set(row.evidence_ids) <= evidence_ids:
                    errors.append(f"influence missing evidence:{candidate.candidate_key}")
                if not set(row.cluster_keys) <= cluster_keys:
                    errors.append(f"influence missing cluster:{candidate.candidate_key}")
                if row.hypothesis_state != "hypothesis":
                    errors.append(f"influence is not hypothetical:{candidate.candidate_key}")
            if not candidate_checksum(candidate):
                errors.append(f"candidate checksum missing:{candidate.candidate_key}")
        if not scout_build_checksum(build):
            errors.append("snapshot checksum missing")
        if errors:
            raise ValueError("; ".join(sorted(set(errors))))
