import type {
  ThemeAggregateSupplyChain,
  ThemeIndustrialController,
  ThemeIndustrialConstraint,
  ThemeIndustrialIntelligence,
  ThemeIndustrialNode,
  ThemeIndustrialOpportunity,
  ThemeIndustrialEdge,
  ThemeIndustrialPath,
  ThemeBeneficiaryRecord,
  ThemeLeader,
} from "@/types/stock";
import { safeArray, uniqueBy } from "./payloadSafety";

export interface SupplyStageView {
  id: string;
  role: string;
  roleZh: string;
  roleEn: string;
  leaders: ThemeLeader[];
  strength: number;
  status: "key" | "strong" | "watch" | "warming";
  hasBottleneck?: boolean;
}

export interface SupplyBeneficiaryView {
  rank: number;
  ticker: string;
  company: string;
  strength: number;
  role: string;
  isBottleneckController: boolean;
}

export interface SupplyRiskView {
  labelZh: string;
  labelEn: string;
  value: number;
  levelZh: "低" | "中" | "高";
  explanation?: string;
}

export interface SupplyDependencyView {
  path: string;
  strength: number;
  description: string;
  bottleneck: string;
}

export interface SupplyResolutionView {
  resolution: string;
  probability: number | null;
  impact: number | null;
  timeline?: string;
}

export interface SupplyChainIntelligenceView {
  theme: string;
  coverage: number;
  strength: number;
  capitalHeat: number;
  riskIndex: number;
  stages: SupplyStageView[];
  beneficiaries: SupplyBeneficiaryView[];
  risks: SupplyRiskView[];
  dependencies: SupplyDependencyView[];
  resolutions: SupplyResolutionView[];
  isFromAggregate: boolean;
}

export interface IndustrialSupplyLayer {
  nodeType: string;
  nodes: ThemeIndustrialNode[];
  coverage: number | null;
  availabilityState: string;
}

export interface IndustrialSupplyChainView {
  theme: string;
  hasGraph: boolean;
  emptyState: string | null;
  primaryBottleneck: ThemeIndustrialConstraint | null;
  secondaryBottlenecks: ThemeIndustrialConstraint[];
  layers: IndustrialSupplyLayer[];
  paths: ThemeIndustrialPath[];
  constraints: ThemeIndustrialIntelligence["constraints"];
  controllers: ThemeIndustrialController[];
  opportunities: ThemeIndustrialOpportunity[];
  evidenceCount: number;
  relationshipCount: number;
  overallCoverage: number;
  graphEdges: Array<{
    sourceKey: string;
    targetKey: string;
    relationshipType: string;
    evidenceIds: number[];
  }>;
}

export interface BottleneckCenteredSupplyMap {
  primarySurfaceOrder: string[];
  primaryBottleneckKey: string | null;
  dominantPath: ThemeIndustrialPath | null;
  summaryMetrics: Array<"coverage" | "constraint-count" | "controller-count" | "beneficiary-count">;
  secondaryPathsCollapsed: boolean;
  displayedEdges: Array<{
    sourceKey: string;
    targetKey: string;
    relationshipType: string;
    evidenceIds: number[];
    persistedInPath: boolean;
  }>;
  selectionPolicy: {
    selectedPathHighlights: boolean;
    dimUnrelatedPaths: boolean;
    selectedNodeDimsUnrelatedEdges: boolean;
  };
}

export interface InstitutionalSupplyFlowStage {
  kind: "controller" | "constraint" | "resolution" | "direct" | "indirect";
  labelZh: string;
  labelEn: string;
  items: Array<{ key: string; label: string; detail: string }>;
}

const ZH_LABELS: Record<string, string> = {
  "Upstream Materials": "上游材料",
  Equipment: "設備",
  Manufacturing: "製造 / 基板",
  "Packaging / Interposer": "封裝 / 中介層",
  Downstream: "下游應用",
  "Bottleneck Controllers": "瓶頸控制者",
  "Resolution Enablers": "解決方案推動者",
  "Valuation Risk": "估值風險",
  "Bubble Risk": "泡沫風險",
  "Crowding Risk": "擁擠風險",
  "Supply Bottleneck": "供應瓶頸",
  "Policy Risk": "政策風險",
};

function finite(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function status(strength: number): SupplyStageView["status"] {
  if (strength >= 90) return "key";
  if (strength >= 75) return "strong";
  if (strength >= 50) return "watch";
  return "warming";
}

function riskLevel(value: number): SupplyRiskView["levelZh"] {
  if (value >= 65) return "高";
  if (value >= 35) return "中";
  return "低";
}

const INDUSTRIAL_LAYER_ORDER = [
  "Theme",
  "Technology",
  "Process",
  "Material",
  "Equipment",
  "Constraint",
  "Company",
] as const;

export function selectPrimaryBottleneck(
  constraints: ThemeIndustrialConstraint[],
): { primaryBottleneck: ThemeIndustrialConstraint | null; secondaryBottlenecks: ThemeIndustrialConstraint[] } {
  const ranked = [...constraints].sort((left, right) => {
    const leftSeverity = finite(left.severity);
    const rightSeverity = finite(right.severity);
    if (leftSeverity !== null || rightSeverity !== null) {
      return (rightSeverity ?? -1) - (leftSeverity ?? -1)
        || right.evidence_count - left.evidence_count
        || left.canonical_key.localeCompare(right.canonical_key);
    }
    return right.evidence_count - left.evidence_count
      || left.canonical_key.localeCompare(right.canonical_key);
  });
  return {
    primaryBottleneck: ranked[0] ?? null,
    secondaryBottlenecks: ranked.slice(1),
  };
}

export function deriveIndustrialSupplyChain(
  industrial: ThemeIndustrialIntelligence | null | undefined,
): IndustrialSupplyChainView {
  if (!industrial) {
    return {
      theme: "Theme",
      hasGraph: false,
      emptyState: "Industrial intelligence is unavailable.",
      primaryBottleneck: null,
      secondaryBottlenecks: [],
      layers: [],
      paths: [],
      constraints: [],
      controllers: [],
      opportunities: [],
      evidenceCount: 0,
      relationshipCount: 0,
      overallCoverage: 0,
      graphEdges: [],
    };
  }

  const nodesByType = new Map<string, ThemeIndustrialNode[]>();
  industrial.graph.nodes.forEach((node) => {
    const nodes = nodesByType.get(node.node_type) ?? [];
    if (!nodes.some((item) => item.canonical_key === node.canonical_key)) {
      nodes.push(node);
      nodesByType.set(node.node_type, nodes);
    }
  });
  industrial.graph.dependency_paths.forEach((path) => {
    path.nodes.forEach((node) => {
      const nodes = nodesByType.get(node.node_type) ?? [];
      if (!nodes.some((item) => item.canonical_key === node.canonical_key)) {
        nodes.push(node);
        nodesByType.set(node.node_type, nodes);
      }
    });
  });

  const layers = INDUSTRIAL_LAYER_ORDER.map((nodeType) => {
    const metric = industrial.coverage.components[nodeType];
    return {
      nodeType,
      nodes: (nodesByType.get(nodeType) ?? []).sort((left, right) => (
        left.display_name.localeCompare(right.display_name)
      )),
      coverage: metric?.coverage ?? null,
      availabilityState: metric?.availability_state ?? "unavailable",
    };
  });
  const hasGraph = industrial.graph.nodes.length > 0
    || industrial.graph.edges.length > 0
    || industrial.graph.dependency_paths.length > 0;

  const { primaryBottleneck, secondaryBottlenecks } = selectPrimaryBottleneck(industrial.constraints);

  return {
    theme: industrial.identity.display_name,
    hasGraph,
    emptyState: hasGraph ? null : "No evidence-backed industrial graph paths are available.",
    primaryBottleneck,
    secondaryBottlenecks,
    layers,
    paths: industrial.graph.dependency_paths,
    constraints: industrial.constraints,
    controllers: industrial.controllers,
    opportunities: industrial.opportunities,
    evidenceCount: industrial.graph.evidence_count,
    relationshipCount: industrial.graph.edges.length,
    overallCoverage: industrial.coverage.overall_coverage,
    graphEdges: industrial.graph.edges.map((edge: ThemeIndustrialEdge) => ({
      sourceKey: edge.source_key,
      targetKey: edge.target_key,
      relationshipType: edge.relationship_type,
      evidenceIds: edge.evidence_ids,
    })),
  };
}

function persistedPathEdgeKeys(paths: ThemeIndustrialPath[]): Set<string> {
  const keys = new Set<string>();
  paths.forEach((path) => {
    safeArray(path.edges).forEach((edge) => {
      keys.add(`${edge.source_key}:${edge.relationship_type}:${edge.target_key}`);
    });
    for (let index = 0; index < path.nodes.length - 1; index += 1) {
      const source = path.nodes[index];
      const target = path.nodes[index + 1];
      if (source && target) keys.add(`${source.canonical_key}:*:${target.canonical_key}`);
    }
  });
  return keys;
}

export function deriveBottleneckCenteredSupplyMap(view: IndustrialSupplyChainView): BottleneckCenteredSupplyMap {
  const pathKeys = persistedPathEdgeKeys(view.paths);
  const displayedEdges = view.graphEdges.map((edge) => {
    const exactKey = `${edge.sourceKey}:${edge.relationshipType}:${edge.targetKey}`;
    const adjacencyKey = `${edge.sourceKey}:*:${edge.targetKey}`;
    const reverseAdjacencyKey = `${edge.targetKey}:*:${edge.sourceKey}`;
    return {
      ...edge,
      persistedInPath: pathKeys.has(exactKey) || pathKeys.has(adjacencyKey) || pathKeys.has(reverseAdjacencyKey),
    };
  });

  return {
    primarySurfaceOrder: ["primary-bottleneck", "controller", "beneficiary", "dependency-graph"],
    primaryBottleneckKey: view.primaryBottleneck?.canonical_key ?? null,
    dominantPath: null,
    summaryMetrics: ["coverage", "constraint-count", "controller-count", "beneficiary-count"],
    secondaryPathsCollapsed: true,
    displayedEdges,
    selectionPolicy: {
      selectedPathHighlights: true,
      dimUnrelatedPaths: true,
      selectedNodeDimsUnrelatedEdges: true,
    },
  };
}

function beneficiaryItems(rows: ThemeBeneficiaryRecord[]) {
  return safeArray(rows).map((row) => ({
    key: row.ticker,
    label: row.ticker,
    detail: row.company_name ?? row.company ?? row.role ?? "Persisted beneficiary",
  }));
}

export function deriveInstitutionalSupplyFlow(input: {
  industrial: ThemeIndustrialIntelligence;
  beneficiaries: {
    controllers: ThemeBeneficiaryRecord[];
    resolution_enablers: ThemeBeneficiaryRecord[];
    direct_beneficiaries: ThemeBeneficiaryRecord[];
    indirect_beneficiaries: ThemeBeneficiaryRecord[];
  };
}): InstitutionalSupplyFlowStage[] {
  return [
    {
      kind: "controller",
      labelZh: "控制者",
      labelEn: "Controller",
      items: input.industrial.controllers.map((row) => ({
        key: row.company_key,
        label: row.company_key.replace("company:", ""),
        detail: row.company_name,
      })),
    },
    {
      kind: "constraint",
      labelZh: "關鍵約束",
      labelEn: "Constraint",
      items: input.industrial.constraints.map((row) => ({
        key: row.canonical_key,
        label: row.display_name,
        detail: row.resolution_state,
      })),
    },
    {
      kind: "resolution",
      labelZh: "解決方案推動者",
      labelEn: "Resolution Enabler",
      items: beneficiaryItems(input.beneficiaries.resolution_enablers),
    },
    {
      kind: "direct",
      labelZh: "直接受益者",
      labelEn: "Direct Beneficiary",
      items: beneficiaryItems(input.beneficiaries.direct_beneficiaries),
    },
    {
      kind: "indirect",
      labelZh: "間接受益者",
      labelEn: "Indirect Beneficiary",
      items: beneficiaryItems(input.beneficiaries.indirect_beneficiaries),
    },
  ];
}

export function deriveSupplyChainIntelligence(input: {
  theme: string;
  aggregateSupplyChain?: ThemeAggregateSupplyChain | null;
}): SupplyChainIntelligenceView {
  const theme = input.theme.trim() || "Theme";
  const supplyChain = input.aggregateSupplyChain;
  if (!supplyChain) {
    return {
      theme,
      coverage: 0,
      strength: 0,
      capitalHeat: 0,
      riskIndex: 0,
      stages: [],
      beneficiaries: [],
      risks: [],
      dependencies: [],
      resolutions: [],
      isFromAggregate: false,
    };
  }

  const controllerTickers = new Set(safeArray(supplyChain.bottleneck_controllers).map((ticker) => ticker.toUpperCase()));
  const stages = safeArray(supplyChain.layers).map((layer, index): SupplyStageView => {
    const entities = safeArray(layer.entities);
    const leaders = uniqueBy(
      entities.map((entity) => ({
        ticker: entity.ticker.toUpperCase(),
        company_name: entity.company,
        role: entity.role,
        alpha_score: finite(entity.strength) ?? undefined,
        confidence_score: finite(entity.strength) ?? undefined,
      })),
      (leader) => leader.ticker,
    );
    const strength = leaders.length
      ? clamp(Math.round(leaders.reduce((sum, leader) => sum + (finite(leader.confidence_score) ?? 0), 0) / leaders.length))
      : 0;
    return {
      id: `${index}-${layer.layer_id}`,
      role: layer.layer_name,
      roleZh: ZH_LABELS[layer.layer_name] ?? layer.layer_name,
      roleEn: layer.layer_name,
      leaders,
      strength,
      status: status(strength),
      hasBottleneck: layer.has_bottleneck,
    };
  });

  const entities = safeArray(supplyChain.layers).flatMap((layer) => safeArray(layer.entities));
  const beneficiaries = uniqueBy(
    entities
      .filter((entity) => entity.ticker)
      .sort((left, right) => (finite(right.strength) ?? 0) - (finite(left.strength) ?? 0))
      .map((entity) => ({
        rank: 0,
        ticker: entity.ticker.toUpperCase(),
        company: entity.company || entity.ticker,
        strength: clamp(Math.round(finite(entity.strength) ?? 0)),
        role: entity.role,
        isBottleneckController: Boolean(entity.is_bottleneck_controller) || controllerTickers.has(entity.ticker.toUpperCase()),
      })),
    (entity) => entity.ticker,
  ).slice(0, 10).map((entity, index) => ({ ...entity, rank: index + 1 }));

  const risks = safeArray(supplyChain.risks).map((risk) => {
    const value = clamp(Math.round(finite(risk.value) ?? 0));
    return {
      labelZh: ZH_LABELS[risk.risk_type] ?? risk.risk_type,
      labelEn: risk.risk_type,
      value,
      levelZh: riskLevel(value),
      explanation: risk.explanation,
    };
  });
  const dependencies = safeArray(supplyChain.dependency_paths).map((dependency) => ({
    path: dependency.path,
    strength: clamp(Math.round(finite(dependency.strength) ?? 0)),
    description: dependency.explanation ?? "",
    bottleneck: dependency.risk ?? "",
  }));
  const resolutions = safeArray(supplyChain.resolutions).map((resolution) => ({
    resolution: resolution.resolution,
    probability: finite(resolution.resolution_probability),
    impact: finite(resolution.impact),
    timeline: resolution.timeline,
  }));
  const strength = stages.length
    ? clamp(Math.round(stages.reduce((sum, stage) => sum + stage.strength, 0) / stages.length))
    : 0;
  const riskIndex = risks.length
    ? clamp(Math.round(risks.reduce((sum, risk) => sum + risk.value, 0) / risks.length))
    : 0;

  return {
    theme,
    coverage: clamp(Math.round((stages.length / 5) * 100)),
    strength,
    capitalHeat: 0,
    riskIndex,
    stages,
    beneficiaries,
    risks,
    dependencies,
    resolutions,
    isFromAggregate: true,
  };
}
