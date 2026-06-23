import type {
  SectorRotation,
  ThemeAggregateResponse,
  ThemeIndustrialEdge,
  ThemeIndustrialIntelligence,
  ThemeScoutCandidate,
} from "@/types/stock";

export type NarrativeAvailability = "available" | "unavailable";
export type NarrativeStepKind =
  | "driver"
  | "constraint"
  | "controller"
  | "resolution"
  | "beneficiary"
  | "opportunity"
  | "signal"
  | "cluster"
  | "research"
  | "sector-state"
  | "momentum"
  | "capital-flow"
  | "linked-theme";

export interface NarrativeLabel {
  zh: string;
  en: string;
}

export interface NarrativeStep {
  kind: NarrativeStepKind;
  labelZh: string;
  labelEn: string;
  value: string;
  sourceField: string;
  sourceType: string;
  evidenceIds: Array<number | string>;
  availabilityState: NarrativeAvailability;
}

export interface DependencyStoryEdge {
  sourceKey: string;
  sourceLabel: string;
  relationshipType: string;
  targetKey: string;
  targetLabel: string;
  evidenceIds: number[];
  sourceField: string;
  sourceType: string;
  availabilityState: NarrativeAvailability;
}

export interface DependencyStory {
  pathId: string | null;
  steps: NarrativeStep[];
  edges: DependencyStoryEdge[];
}

export interface ResearchNarrative {
  title: NarrativeLabel;
  steps: NarrativeStep[];
}

export const NARRATIVE_LABELS = {
  researchNarrative: { zh: "研究敘事", en: "Research Narrative" },
  currentDriver: { zh: "目前驅動", en: "Current Driver" },
  constraint: { zh: "關鍵瓶頸", en: "Constraint" },
  controller: { zh: "控制層", en: "Controller" },
  resolution: { zh: "解決路徑", en: "Resolution Path" },
  beneficiary: { zh: "受益者", en: "Beneficiary" },
  opportunity: { zh: "機會", en: "Opportunity" },
  evidenceChain: { zh: "證據鏈", en: "Evidence Chain" },
  researchHypothesis: { zh: "研究假設", en: "Research Hypothesis" },
  capitalFlowStory: { zh: "資金流敘事", en: "Capital Flow Story" },
  insufficientEvidence: { zh: "證據不足", en: "Insufficient evidence" },
} as const satisfies Record<string, NarrativeLabel>;

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function evidenceNumbers(values: unknown): number[] {
  return Array.isArray(values)
    ? values.map((value) => Number(value)).filter((value) => Number.isInteger(value))
    : [];
}

function step(
  kind: NarrativeStepKind,
  label: NarrativeLabel,
  value: string | null,
  sourceField: string,
  sourceType: string,
  evidenceIds: Array<number | string> = [],
): NarrativeStep {
  return {
    kind,
    labelZh: label.zh,
    labelEn: label.en,
    value: value ?? NARRATIVE_LABELS.insufficientEvidence.zh,
    sourceField,
    sourceType,
    evidenceIds,
    availabilityState: value ? "available" : "unavailable",
  };
}

function companyFromKey(value: string): string {
  return value.startsWith("company:") ? value.slice("company:".length) : value;
}

function firstBeneficiary(aggregate: ThemeAggregateResponse): string | null {
  const row = [
    ...aggregate.beneficiaries.direct_beneficiaries,
    ...aggregate.beneficiaries.resolution_enablers,
    ...aggregate.beneficiaries.indirect_beneficiaries,
  ][0];
  if (!row) return null;
  return text(row.company_name) ?? text(row.company) ?? text(row.ticker);
}

export function buildThemeNarrative(aggregate: ThemeAggregateResponse): ResearchNarrative {
  const catalyst = aggregate.catalysts.top_catalysts[0];
  const constraint = aggregate.industrial_intelligence.constraints[0];
  const controller = aggregate.industrial_intelligence.controllers[0];
  const opportunity = aggregate.industrial_intelligence.opportunities[0];
  const driver =
    text(aggregate.discovery.brief?.why_now)
    ?? text(catalyst?.name)
    ?? text(catalyst?.catalyst_name);
  const resolutionValue = opportunity?.company_name
    ?? (constraint?.resolver_company_keys[0] ? companyFromKey(constraint.resolver_company_keys[0]) : null);
  const steps = [
    step("driver", NARRATIVE_LABELS.currentDriver, driver, "discovery.brief.why_now", "theme_aggregate"),
    step("constraint", NARRATIVE_LABELS.constraint, constraint?.display_name ?? null, "industrial_intelligence.constraints", "industrial_graph", evidenceNumbers((constraint as { evidence_ids?: unknown } | undefined)?.evidence_ids)),
    step("controller", NARRATIVE_LABELS.controller, controller?.company_name ?? null, "industrial_intelligence.controllers", "controller_snapshot", controller?.evidence_ids ?? []),
    step("resolution", NARRATIVE_LABELS.resolution, resolutionValue, "industrial_intelligence.opportunities", "opportunity_snapshot", opportunity?.evidence_ids ?? []),
    step("beneficiary", NARRATIVE_LABELS.beneficiary, firstBeneficiary(aggregate), "beneficiaries", "theme_aggregate"),
    step("opportunity", NARRATIVE_LABELS.opportunity, opportunity?.company_name ?? null, "industrial_intelligence.opportunities", "opportunity_snapshot", opportunity?.evidence_ids ?? []),
  ].filter((item) => item.availabilityState === "available");
  return { title: NARRATIVE_LABELS.researchNarrative, steps };
}

function nodeLabel(nodes: ThemeIndustrialIntelligence["graph"]["nodes"], key: string): string {
  return nodes.find((node) => node.canonical_key === key)?.display_name ?? key;
}

function edgeKey(edge: Pick<ThemeIndustrialEdge, "source_key" | "target_key" | "relationship_type">): string {
  return `${edge.source_key}>${edge.relationship_type}>${edge.target_key}`;
}

export function buildDependencyStory(graph: ThemeIndustrialIntelligence["graph"]): DependencyStory {
  const persistedEdges = new Map(graph.edges.map((edge) => [edgeKey(edge), edge]));
  const focusPath = [...graph.dependency_paths].sort((left, right) => (
    (right.evidence_ids?.length ?? 0) - (left.evidence_ids?.length ?? 0)
    || right.depth - left.depth
    || (left.path_id ?? "").localeCompare(right.path_id ?? "")
  ))[0];
  const storyEdges = (focusPath?.edges ?? graph.edges)
    .map((edge) => persistedEdges.get(edgeKey(edge)))
    .filter((edge): edge is ThemeIndustrialEdge => Boolean(edge))
    .map((edge) => ({
      sourceKey: edge.source_key,
      sourceLabel: nodeLabel(graph.nodes, edge.source_key),
      relationshipType: edge.relationship_type,
      targetKey: edge.target_key,
      targetLabel: nodeLabel(graph.nodes, edge.target_key),
      evidenceIds: [...edge.evidence_ids],
      sourceField: "industrial_intelligence.graph.edges",
      sourceType: "industrial_graph",
      availabilityState: "available" as const,
    }));
  const steps = storyEdges.map((edge) => step(
    "constraint",
    NARRATIVE_LABELS.evidenceChain,
    `${edge.sourceLabel} → ${edge.targetLabel}`,
    "industrial_intelligence.graph.dependency_paths",
    "industrial_graph",
    edge.evidenceIds,
  ));
  return {
    pathId: focusPath?.path_id ?? null,
    steps,
    edges: storyEdges,
  };
}

export function buildScoutHypothesisNarrative(candidate: ThemeScoutCandidate): ResearchNarrative {
  const cluster = candidate.signal_clusters[0];
  const bottleneck = candidate.paths.find((path) => path.path_type === "POTENTIAL_BOTTLENECK");
  const influence = candidate.influence_map[0];
  return {
    title: NARRATIVE_LABELS.researchHypothesis,
    steps: [
      step("signal", { zh: "訊號出現", en: "Signal Appeared" }, candidate.evidence[0]?.citation ?? null, "evidence", "scout_snapshot", candidate.evidence[0] ? [candidate.evidence[0].evidence_id] : []),
      step("cluster", { zh: "叢集形成", en: "Cluster Formed" }, cluster?.label ?? null, "signal_clusters", "scout_snapshot", cluster?.evidence_ids ?? []),
      step("constraint", { zh: "瓶頸假設", en: "Constraint Hypothesis" }, bottleneck?.label ?? influence?.target_label ?? null, "paths.POTENTIAL_BOTTLENECK", "scout_snapshot", bottleneck?.evidence_ids ?? influence?.evidence_ids ?? []),
      step("research", { zh: "研究待辦", en: "Research Required" }, candidate.status, "status", "scout_snapshot"),
    ].filter((item) => item.availabilityState === "available"),
  };
}

export function buildRotationStory(sector: SectorRotation | null): ResearchNarrative {
  if (!sector) {
    return {
      title: NARRATIVE_LABELS.capitalFlowStory,
      steps: [step("sector-state", NARRATIVE_LABELS.insufficientEvidence, null, "sector", "rotation_snapshot")],
    };
  }
  const score = typeof sector.score === "number" && Number.isFinite(sector.score) ? `${sector.score.toFixed(0)} score` : null;
  const momentum = typeof sector.momentum === "number" && Number.isFinite(sector.momentum) ? `${sector.momentum >= 0 ? "+" : ""}${sector.momentum.toFixed(2)} momentum` : null;
  const flow = typeof sector.flow === "number" && Number.isFinite(sector.flow) ? `${sector.flow >= 0 ? "+" : ""}${sector.flow.toFixed(0)} flow` : null;
  const linkedThemes = Array.isArray(sector.linked_themes) && sector.linked_themes.length > 0
    ? sector.linked_themes.join(", ")
    : null;
  return {
    title: NARRATIVE_LABELS.capitalFlowStory,
    steps: [
      step("sector-state", { zh: "板塊狀態", en: "Sector State" }, sector.rotation_state ?? score, "rotation_state", "rotation_snapshot"),
      step("momentum", { zh: "動量", en: "Momentum" }, momentum, "rotation_momentum", "rotation_snapshot"),
      step("capital-flow", { zh: "資金流", en: "Capital Flow" }, flow, "rotation_flow", "rotation_snapshot"),
      step("linked-theme", { zh: "連結主題", en: "Linked Themes" }, linkedThemes, "linked_themes", "rotation_snapshot"),
    ],
  };
}
