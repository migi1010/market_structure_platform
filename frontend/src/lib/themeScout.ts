import type { ThemeScoutCandidate } from "@/types/stock";

export const SCOUT_LABELS = {
  bottleneckHeat: { zh: "瓶頸熱度", en: "Bottleneck Heat" },
  researchReadiness: { zh: "研究成熟度", en: "Research Readiness" },
  coverageRadar: { zh: "覆蓋雷達", en: "Coverage Radar" },
  evidenceDistribution: { zh: "證據分布", en: "Evidence Distribution" },
  signalClusters: { zh: "訊號叢集", en: "Signal Clusters" },
  themeEvolution: { zh: "主題演化路徑", en: "Theme Evolution" },
  researchProgress: { zh: "研究進度", en: "Research Progress" },
  evidenceCompanies: { zh: "證據關聯公司", en: "Evidence-linked Companies" },
  candidateHealth: { zh: "候選主題健康度", en: "Candidate Health" },
  researchQueue: { zh: "研究佇列", en: "Research Queue" },
  lifecycleTimeline: { zh: "生命週期時間軸", en: "Lifecycle Timeline" },
} as const;

export const SCOUT_WORKFLOW_ORDER = [
  "top-themes",
  "why-it-matters",
  "research-queue",
  "evidence",
] as const;

export interface ScoutVisualModel {
  bottlenecks: Array<{
    label: string;
    evidenceCount: number;
    evidenceIds: string[];
    relativeHeat: number;
  }>;
  coverageRadar: Array<{ label: string; value: number }>;
  evidenceDistribution: Array<{ label: string; count: number }>;
  clusters: Array<{ key: string; label: string; evidenceCount: number }>;
  companies: Array<{ canonicalKey: string; displayName: string; citation: string; evidenceId: string }>;
  health: {
    coverage: number;
    researchReadiness: number;
    evidenceQuality: null;
    constraintDensity: null;
  };
  researchQueue: Array<{ label: string; state: string; evidenceIds: string[] }>;
  lifecycle: Array<{ status: string; active: boolean }>;
  compactMetadata: {
    coverage: number;
    readiness: number;
    novelty: number | null;
  };
}

export interface ScoutWorkspacePriority {
  primary: string[];
  metadataTier: "secondary";
  candidateDisplay: {
    minimum: 3;
    maximum: 5;
    source: "theme-registry";
  };
  companyPresentation: {
    primary: "displayName";
    secondary: "evidenceMetadata";
  };
}

export const THEME_SCOUT_EXAMPLES = [
  "Reusable Rockets",
  "Starlink Economy",
  "AI Power Grid",
  "Nuclear SMR",
  "Humanoid Robotics",
  "Defense Drones",
] as const;

export function compareThemeScoutCandidates(
  left: ThemeScoutCandidate,
  right: ThemeScoutCandidate,
): number {
  return (
    right.metrics.bottleneck - left.metrics.bottleneck
    || right.metrics.confidence - left.metrics.confidence
    || right.metrics.coverage - left.metrics.coverage
    || right.readiness.overall - left.readiness.overall
    || left.candidate_key.localeCompare(right.candidate_key)
  );
}

export function scoutScore(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(0)
    : "Unavailable";
}

function companyDisplayName(sourceIdentifier: string, citation: string): string {
  const canonical = sourceIdentifier.startsWith("company:")
    ? sourceIdentifier.slice(8)
    : sourceIdentifier;
  const citationMatch = citation.match(/classification:\s*([^.,]+?)\s+is\s+/i)
    ?? citation.match(/^\s*([^.,]+?)\s+is\s+/i);
  if (citationMatch?.[1]?.trim()) return citationMatch[1].trim();
  const parts = canonical.split(":").filter(Boolean);
  const ticker = parts.find((part) => /^[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?$/.test(part));
  return (ticker ?? canonical).toUpperCase();
}

export function buildScoutVisualModel(candidate: ThemeScoutCandidate): ScoutVisualModel {
  const bottleneckPaths = candidate.paths.filter((path) => path.path_type === "POTENTIAL_BOTTLENECK");
  const maximumEvidence = Math.max(1, ...bottleneckPaths.map((path) => path.evidence_ids.length));
  const evidenceCounts = new Map<string, number>();
  candidate.evidence.forEach((item) => {
    evidenceCounts.set(item.domain_type, (evidenceCounts.get(item.domain_type) ?? 0) + 1);
  });

  return {
    bottlenecks: bottleneckPaths
      .map((path) => ({
        label: path.label,
        evidenceCount: path.evidence_ids.length,
        evidenceIds: path.evidence_ids,
        relativeHeat: (path.evidence_ids.length / maximumEvidence) * 100,
      }))
      .sort((left, right) => (
        right.evidenceCount - left.evidenceCount || left.label.localeCompare(right.label)
      )),
    coverageRadar: [
      { label: "Technology", value: candidate.readiness.technology },
      { label: "Process", value: candidate.readiness.process },
      { label: "Material", value: candidate.readiness.material },
      { label: "Equipment", value: candidate.readiness.equipment },
      { label: "Constraint", value: candidate.readiness.constraint },
      { label: "Company", value: candidate.readiness.company },
    ],
    evidenceDistribution: Array.from(evidenceCounts.entries())
      .map(([label, count]) => ({ label, count }))
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label)),
    clusters: candidate.signal_clusters.map((cluster) => ({
      key: cluster.cluster_key,
      label: cluster.label,
      evidenceCount: cluster.evidence_ids.length,
    })),
    companies: candidate.evidence
      .filter((item) => item.domain_type === "Company")
      .map((item) => ({
        canonicalKey: item.source_identifier,
        displayName: companyDisplayName(item.source_identifier, item.citation),
        citation: item.citation,
        evidenceId: item.evidence_id,
      })),
    health: {
      coverage: candidate.metrics.coverage,
      researchReadiness: candidate.readiness.overall,
      evidenceQuality: null,
      constraintDensity: null,
    },
    researchQueue: bottleneckPaths.map((path) => ({
      label: `Validate: ${path.label}`,
      state: "pending_research",
      evidenceIds: path.evidence_ids,
    })),
    lifecycle: ["DISCOVERED", "OBSERVING", "VALIDATING", "APPROVED", "REJECTED"].map((status) => ({
      status,
      active: candidate.status === status,
    })),
    compactMetadata: {
      coverage: candidate.metrics.coverage,
      readiness: candidate.readiness.overall,
      novelty: candidate.metrics.raw_values?.novelty_availability_state === "unavailable"
        ? null
        : candidate.metrics.novelty,
    },
  };
}

export function buildScoutWorkspacePriority(_visual: ScoutVisualModel): ScoutWorkspacePriority {
  return {
    primary: [...SCOUT_WORKFLOW_ORDER],
    metadataTier: "secondary",
    candidateDisplay: {
      minimum: 3,
      maximum: 5,
      source: "theme-registry",
    },
    companyPresentation: {
      primary: "displayName",
      secondary: "evidenceMetadata",
    },
  };
}
