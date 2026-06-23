import {
  buildScoutVisualModel,
  buildScoutWorkspacePriority,
  compareThemeScoutCandidates,
  SCOUT_LABELS,
  SCOUT_WORKFLOW_ORDER,
  THEME_SCOUT_EXAMPLES,
} from "./themeScout";
import type { ThemeScoutCandidate } from "@/types/stock";

function candidate(name: string, bottleneck: number, novelty: number): ThemeScoutCandidate {
  return {
    candidate_key: `candidate:${name.toLowerCase().replace(/\s+/g, "-")}`,
    name,
    description: "candidate",
    status: "DISCOVERED",
    metrics: {
      confidence: 50,
      novelty,
      velocity: 50,
      breadth: 50,
      capital: 50,
      bottleneck,
      serendipity: 50,
      theme_score: 50,
      coverage: 50,
    },
    readiness: {
      technology: 0, process: 0, material: 0, equipment: 0,
      constraint: 0, company: 0, overall: 0,
    },
    evidence: [],
    signal_clusters: [],
    paths: [],
    influence_map: [],
    rank: 1,
    generated_summary: "",
    signal_count: 0,
    evidence_count: 0,
    source_count: 0,
  };
}

export function themeScoutContractTest() {
  const highNovelty = candidate("Novel", 20, 100);
  const bottleneck = candidate("Bottleneck", 90, 20);
  const visual = buildScoutVisualModel({
    ...bottleneck,
    readiness: {
      technology: 0,
      process: 0,
      material: 0,
      equipment: 0,
      constraint: 80,
      company: 60,
      overall: 23,
    },
    paths: [{
      path_type: "POTENTIAL_BOTTLENECK",
      label: "Power Availability",
      evidence_ids: ["graph_evidence:1"],
      steps: [],
    }],
    evidence: [{
      evidence_id: "graph_evidence:1",
      source_table: "graph_evidence",
      source_record_id: "1",
      source_type: "curated",
      source_timestamp: "2026-06-14T00:00:00Z",
      source_identifier: "company:VRT",
      citation: "Persisted evidence",
      domain_type: "Company",
      cluster_key: "power",
      availability_state: "available",
    }],
  });
  const priority = buildScoutWorkspacePriority(visual);
  return {
    examplesAreLabelsOnly: THEME_SCOUT_EXAMPLES.length === 6,
    bottleneckRanksFirst:
      [highNovelty, bottleneck].sort(compareThemeScoutCandidates)[0].name === "Bottleneck",
    influenceMapStartsEmpty: bottleneck.influence_map.length === 0,
    noveltyDoesNotAffectRanking:
      [candidate("Z Candidate", 50, 100), candidate("A Candidate", 50, 0)]
        .sort(compareThemeScoutCandidates)[0].name === "A Candidate",
    chineseFirstLabels:
      SCOUT_LABELS.bottleneckHeat.zh === "瓶頸熱度"
      && SCOUT_LABELS.researchReadiness.zh === "研究成熟度"
      && SCOUT_LABELS.evidenceDistribution.zh === "證據分布",
    visualPanelsPresent:
      visual.bottlenecks.length === 1
      && visual.evidenceDistribution[0]?.label === "Company",
    evidenceFirstWorkspace:
      visual.researchQueue.length > 0
      && visual.lifecycle[0]?.status === "DISCOVERED"
      && visual.compactMetadata.readiness === 23,
    workflowOrder:
      SCOUT_WORKFLOW_ORDER.join(">")
      === "top-themes>why-it-matters>research-queue>evidence",
    researchQueueOutranksMetadata:
      priority.primary[0] === "top-themes"
      && priority.primary[2] === "research-queue"
      && priority.metadataTier === "secondary",
    scoutSupportsThreeToFiveThemes:
      priority.candidateDisplay.minimum === 3
      && priority.candidateDisplay.maximum === 5
      && priority.candidateDisplay.source === "theme-registry",
    evidenceLinkedCompanies: visual.companies[0]?.canonicalKey === "company:VRT",
    companyNamesPrimaryEvidenceSecondary:
      visual.companies[0]?.displayName === "VRT"
      && priority.companyPresentation.primary === "displayName"
      && priority.companyPresentation.secondary === "evidenceMetadata",
    unavailableMetricsRemainUnavailable:
      visual.health.evidenceQuality === null
      && visual.health.constraintDensity === null,
  };
}
