import type { SectorRotation, ThemeAggregateResponse, ThemeScoutCandidate } from "@/types/stock";
import {
  NARRATIVE_LABELS,
  buildDependencyStory,
  buildRotationStory,
  buildScoutHypothesisNarrative,
  buildThemeNarrative,
} from "./researchNarrative";

const aggregate = {
  name: "HBM",
  discovery: {
    brief: { why_now: "Accelerator attach rates are increasing." },
  },
  catalysts: {
    top_catalysts: [
      { name: "AI cluster demand", description: "Demand for memory bandwidth.", source: "theme_catalysts" },
    ],
  },
  beneficiaries: {
    direct_beneficiaries: [{ ticker: "000660.KS", company_name: "SK Hynix", beneficiary_type: "Direct Beneficiary" }],
    resolution_enablers: [{ ticker: "AMAT", company_name: "Applied Materials", beneficiary_type: "Resolution Enabler" }],
    indirect_beneficiaries: [],
    top_beneficiaries: [],
    controllers: [],
  },
  industrial_intelligence: {
    constraints: [
      {
        canonical_key: "constraint:hbm-capacity",
        display_name: "HBM Capacity Constraint",
        severity: 72,
        evidence_count: 2,
        evidence_ids: [201, 202],
        resolution_state: "unresolved",
        resolver_company_keys: [],
        exposed_company_keys: [],
        coverage: 100,
      },
    ],
    controllers: [
      {
        company_key: "company:AMAT",
        company_name: "Applied Materials",
        rank: 1,
        controller_score: 71.2,
        coverage: 90,
        coverage_confidence: 80,
        controller_types: ["Equipment Controller"],
        evidence_count: 2,
        evidence_ids: [301, 302],
        reasoning_paths: [],
      },
    ],
    opportunities: [
      {
        company_key: "company:AMAT",
        company_name: "Applied Materials",
        rank: 1,
        opportunity_score: 68.4,
        coverage_confidence: 75,
        coverage_component: 80,
        controller_contribution: 70,
        constraint_contribution: 66,
        opportunity_types: ["Constraint Resolution"],
        evidence_count: 1,
        evidence_ids: [401],
        availability_states: {},
        reasoning_paths: [],
      },
    ],
    graph: {
      snapshot_id: 1,
      build_version: "test",
      evidence_count: 4,
      counts_by_type: {},
      nodes: [
        { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
        { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
        { node_type: "Constraint", canonical_key: "constraint:hbm-capacity", display_name: "HBM Capacity Constraint", aliases: [], external_ids: {} },
        { node_type: "Company", canonical_key: "company:AMAT", display_name: "Applied Materials", aliases: [], external_ids: {} },
      ],
      edges: [
        { source_type: "Theme", source_key: "theme:hbm", relationship_type: "USES_TECHNOLOGY", target_type: "Technology", target_key: "technology:tsv", evidence_ids: [11] },
        { source_type: "Technology", source_key: "technology:tsv", relationship_type: "TECHNOLOGY_LIMITED_BY_CONSTRAINT", target_type: "Constraint", target_key: "constraint:hbm-capacity", evidence_ids: [12] },
        { source_type: "Constraint", source_key: "constraint:hbm-capacity", relationship_type: "CONSTRAINT_RESOLVED_BY_COMPANY", target_type: "Company", target_key: "company:AMAT", evidence_ids: [13] },
      ],
      dependency_paths: [
        {
          path_id: "path:hbm",
          depth: 3,
          evidence_ids: [11, 12, 13],
          nodes: [
            { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
            { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
            { node_type: "Constraint", canonical_key: "constraint:hbm-capacity", display_name: "HBM Capacity Constraint", aliases: [], external_ids: {} },
            { node_type: "Company", canonical_key: "company:AMAT", display_name: "Applied Materials", aliases: [], external_ids: {} },
          ],
        },
      ],
    },
  },
} as unknown as ThemeAggregateResponse;

const candidate = {
  candidate_key: "candidate:ai-infrastructure-watch",
  name: "AI Infrastructure Constraint Watch",
  status: "DISCOVERED",
  metrics: { confidence: 70, coverage: 80, novelty: 0, velocity: 0, breadth: 0, capital: 0, bottleneck: 75, serendipity: 0, theme_score: 0 },
  readiness: { technology: 50, process: 50, material: 50, equipment: 50, constraint: 70, company: 70, overall: 62 },
  signal_clusters: [{ cluster_key: "power", label: "Power Infrastructure", evidence_ids: ["graph_evidence:148"] }],
  evidence: [{ evidence_id: "graph_evidence:148", citation: "Persisted graph evidence", domain_type: "Constraint" }],
  paths: [{ path_type: "POTENTIAL_BOTTLENECK", label: "Power Availability", evidence_ids: ["graph_evidence:148"], steps: [] }],
  influence_map: [{ target_type: "Constraint", target_label: "Power Availability", evidence_ids: ["graph_evidence:148"], cluster_keys: ["power"], hypothesis_state: "hypothesis" }],
} as unknown as ThemeScoutCandidate;

export function researchNarrativeContractTest() {
  const theme = buildThemeNarrative(aggregate);
  const dependency = buildDependencyStory(aggregate.industrial_intelligence.graph);
  const scout = buildScoutHypothesisNarrative(candidate);
  const rotation = buildRotationStory({
    sector: "Technology",
    score: 72,
    momentum: 2.4,
    flow: 51,
    linked_themes: ["AI Infrastructure"],
    companies: [],
    relative_strength: 70,
  } as SectorRotation);
  const unsupportedRotation = buildRotationStory({
    sector: "Financials",
    score: 48,
    momentum: -1,
    flow: 9,
    companies: [],
    relative_strength: 44,
  } as SectorRotation);

  return {
    themeUsesOnlyApprovedStages: theme.steps.map((step) => step.kind).join(">") === "driver>constraint>controller>resolution>beneficiary>opportunity",
    themePreservesEvidence: theme.steps.flatMap((step) => step.evidenceIds).join(",") === "201,202,301,302,401",
    themeNoSyntheticUnavailable: buildThemeNarrative({ ...aggregate, industrial_intelligence: { ...aggregate.industrial_intelligence, opportunities: [] } }).steps.every((step) => String(step.availabilityState) !== "synthetic"),
    dependencyUsesPersistedEdgesOnly: dependency.edges.every((edge) => aggregate.industrial_intelligence.graph.edges.some((source) => (
      source.source_key === edge.sourceKey
      && source.target_key === edge.targetKey
      && source.relationship_type === edge.relationshipType
    ))),
    dependencyPreservesEvidence: dependency.edges.flatMap((edge) => edge.evidenceIds).join(",") === "11,12,13",
    scoutLabelsHypothesis: scout.steps.some((step) => step.kind === "constraint" && step.labelEn.includes("Hypothesis")),
    scoutNeverRecommends: !scout.steps.map((step) => `${step.labelZh} ${step.labelEn} ${step.value}`).join(" ").match(/buy|sell|target|recommend/i),
    rotationUsesPersistedFields: rotation.steps.map((step) => step.sourceField).join(",") === "rotation_state,rotation_momentum,rotation_flow,linked_themes",
    rotationInsufficientEvidence: unsupportedRotation.steps.at(-1)?.availabilityState === "unavailable",
    chineseFirstLabels:
      NARRATIVE_LABELS.researchNarrative.zh === "研究敘事"
      && NARRATIVE_LABELS.currentDriver.zh === "目前驅動"
      && NARRATIVE_LABELS.evidenceChain.zh === "證據鏈"
      && NARRATIVE_LABELS.insufficientEvidence.zh === "證據不足",
  };
}
