import type { ThemeIndustrialIntelligence } from "@/types/stock";
import {
  deriveBottleneckCenteredSupplyMap,
  deriveIndustrialSupplyChain,
  deriveInstitutionalSupplyFlow,
  deriveSupplyChainIntelligence,
} from "./supplyChainIntelligence";

const industrial: ThemeIndustrialIntelligence = {
  identity: {
    requested_theme_id: "HBM",
    canonical_theme_key: "theme:hbm",
    display_name: "HBM",
    aliases: [],
    resolution_state: "resolved",
  },
  lineage: {
    graph_snapshot_id: 31,
    graph_build_version: "graph-v1",
    controller_snapshot_id: 15,
    controller_version: "controller-v1",
    opportunity_snapshot_id: 15,
    opportunity_version: "opportunity-v1",
    packet_family_version: "packet-v1",
    packet_family_revision: 1,
    lineage_state: "complete",
  },
  graph: {
    snapshot_id: 31,
    build_version: "graph-v1",
    nodes: [
      { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
      { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
      { node_type: "Process", canonical_key: "process:tsv-etching", display_name: "TSV Etching", aliases: [], external_ids: {} },
      { node_type: "Company", canonical_key: "company:AMAT", display_name: "Applied Materials", aliases: [], external_ids: {} },
    ],
    edges: [{
      source_type: "Theme",
      source_key: "theme:hbm",
      relationship_type: "USES_TECHNOLOGY",
      target_type: "Technology",
      target_key: "technology:tsv",
      evidence_ids: [1],
    }],
    evidence_count: 3,
    dependency_paths: [{
      path_id: "hbm-tsv-etch",
      depth: 2,
      nodes: [
        { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
        { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
        { node_type: "Process", canonical_key: "process:tsv-etching", display_name: "TSV Etching", aliases: [], external_ids: {} },
      ],
      evidence_ids: [1, 2],
    }],
    counts_by_type: { Theme: 1, Technology: 1, Process: 1, Company: 1 },
  },
  constraints: [],
  controllers: [{
    company_key: "company:AMAT",
    company_name: "Applied Materials",
    rank: 1,
    controller_score: 72,
    coverage: 80,
    coverage_confidence: 80,
    controller_types: ["Equipment Controller"],
    evidence_count: 2,
    evidence_ids: [2, 3],
    reasoning_paths: [],
  }],
  opportunities: [],
  decision_packets: { family: null, theme_packet: null, matching_packets: [] },
  coverage: {
    overall_coverage: 67,
    components: {
      Technology: { numerator: 1, denominator: 1, coverage: 100, availability_state: "available" },
      Process: { numerator: 1, denominator: 1, coverage: 100, availability_state: "available" },
    },
  },
  research_gaps: [],
};

export function supplyChainIntelligenceContractTest() {
  const view = deriveSupplyChainIntelligence({
    theme: "Glass Substrate",
    aggregateSupplyChain: {
      layers: [
        {
          layer_id: "upstream_materials",
          layer_name: "Upstream Materials",
          entities: [{ ticker: "GLW", company: "Corning", role: "glass materials", strength: 72, is_bottleneck_controller: false }],
          has_bottleneck: false,
        },
        {
          layer_id: "equipment",
          layer_name: "Equipment",
          entities: [{ ticker: "AMAT", company: "Applied Materials", role: "packaging equipment", strength: 67, is_bottleneck_controller: false }],
          has_bottleneck: false,
        },
      ],
      bottleneck_controllers: ["TSM"],
      dependency_paths: [],
      risks: [],
      resolutions: [],
    },
  });
  const malformed = deriveSupplyChainIntelligence({ theme: "HBM", aggregateSupplyChain: null });
  const industrialView = deriveIndustrialSupplyChain(industrial);
  const bottleneckMap = deriveBottleneckCenteredSupplyMap({
    ...industrialView,
    primaryBottleneck: {
      canonical_key: "constraint:hbm-capacity",
      display_name: "HBM Capacity",
      constraint_type: "Capacity",
      severity: 80,
      evidence_count: 2,
      resolution_state: "unresolved",
      resolver_company_keys: ["company:AMAT"],
      exposed_company_keys: ["company:MU"],
      coverage: 50,
    },
    paths: [{
      path_id: "constraint-control-beneficiary",
      depth: 3,
      nodes: [
        { node_type: "Constraint", canonical_key: "constraint:hbm-capacity", display_name: "HBM Capacity", aliases: [], external_ids: {} },
        { node_type: "Company", canonical_key: "company:AMAT", display_name: "Applied Materials", aliases: [], external_ids: {} },
        { node_type: "Company", canonical_key: "company:MU", display_name: "Micron", aliases: [], external_ids: {} },
      ],
      edges: [
        { source_type: "Constraint", source_key: "constraint:hbm-capacity", relationship_type: "CONSTRAINT_RESOLVED_BY_COMPANY", target_type: "Company", target_key: "company:AMAT", evidence_ids: [2] },
        { source_type: "Company", source_key: "company:MU", relationship_type: "COMPANY_EXPOSED_TO_CONSTRAINT", target_type: "Constraint", target_key: "constraint:hbm-capacity", evidence_ids: [3] },
      ],
      evidence_ids: [2, 3],
    }],
    graphEdges: [
      { sourceKey: "constraint:hbm-capacity", relationshipType: "CONSTRAINT_RESOLVED_BY_COMPANY", targetKey: "company:AMAT", evidenceIds: [2] },
      { sourceKey: "company:MU", relationshipType: "COMPANY_EXPOSED_TO_CONSTRAINT", targetKey: "constraint:hbm-capacity", evidenceIds: [3] },
    ],
  });
  const institutionalFlow = deriveInstitutionalSupplyFlow({
    industrial,
    beneficiaries: {
      controllers: [{ ticker: "AMAT", company_name: "Applied Materials" }],
      resolution_enablers: [{ ticker: "KLAC", company_name: "KLA" }],
      direct_beneficiaries: [{ ticker: "MU", company_name: "Micron" }],
      indirect_beneficiaries: [{ ticker: "NVDA", company_name: "NVIDIA" }],
    },
  });

  return {
    rendersVerifiedStagesOnly: view.stages.length === 2,
    usesRoleConstituents: view.stages[0].leaders[0]?.ticker === "GLW",
    noInventedDependencies: view.dependencies.length === 0,
    noInventedRisks: view.risks.length === 0,
    malformedSafe: malformed.stages.length === 0 && malformed.beneficiaries.length === 0,
    industrialGraphPresent: industrialView.hasGraph,
    industrialPathGrouped:
      industrialView.layers.find((layer) => layer.nodeType === "Technology")?.nodes[0]?.display_name === "TSV",
    industrialControllerPresent: industrialView.controllers[0]?.company_key === "company:AMAT",
    noFalseEmptyState: industrialView.emptyState === null,
    persistedGraphEdges:
      industrialView.graphEdges[0]?.sourceKey === "theme:hbm"
      && industrialView.graphEdges[0]?.targetKey === "technology:tsv",
    bottleneckFirst:
      bottleneckMap.primarySurfaceOrder.join(">")
      === "primary-bottleneck>controller>beneficiary>dependency-graph",
    dominantPathRemoved:
      bottleneckMap.dominantPath === null
      && !bottleneckMap.primarySurfaceOrder.includes("dominant-dependency-path"),
    userFacingMetricsReplaceDeveloperCounters:
      bottleneckMap.summaryMetrics.join(">")
      === "coverage>constraint-count>controller-count>beneficiary-count",
    secondaryPathsCollapsed: bottleneckMap.secondaryPathsCollapsed,
    persistedEdgesOnly: bottleneckMap.displayedEdges.every((edge) => edge.persistedInPath),
    selectedPathDimsUnrelated:
      bottleneckMap.selectionPolicy.selectedPathHighlights && bottleneckMap.selectionPolicy.dimUnrelatedPaths,
    connectedInstitutionalFlow:
      institutionalFlow.map((stage) => stage.kind).join(",")
      === "controller,constraint,resolution,direct,indirect",
  };
}
