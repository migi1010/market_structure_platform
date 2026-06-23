import { projectIndustrialGraph } from "./industrialGraphProjection";
import type { ThemeIndustrialIntelligence } from "@/types/stock";

const graph: ThemeIndustrialIntelligence["graph"] = {
  snapshot_id: 1,
  build_version: "test",
  nodes: [
    { node_type: "Company", canonical_key: "company:TSM", display_name: "TSMC", aliases: [], external_ids: {} },
    { node_type: "Constraint", canonical_key: "constraint:capacity", display_name: "Capacity", aliases: [], external_ids: {} },
    { node_type: "Process", canonical_key: "process:bonding", display_name: "Wafer Bonding", aliases: [], external_ids: {} },
    { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
    { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
  ],
  edges: [
    {
      source_type: "Theme",
      source_key: "theme:hbm",
      relationship_type: "USES_TECHNOLOGY",
      target_type: "Technology",
      target_key: "technology:tsv",
      evidence_ids: [11],
    },
    {
      source_type: "Technology",
      source_key: "technology:tsv",
      relationship_type: "REQUIRES_PROCESS",
      target_type: "Process",
      target_key: "process:bonding",
      evidence_ids: [12],
    },
    {
      source_type: "Process",
      source_key: "process:bonding",
      relationship_type: "PROCESS_LIMITED_BY_CONSTRAINT",
      target_type: "Constraint",
      target_key: "constraint:capacity",
      evidence_ids: [13],
    },
    {
      source_type: "Constraint",
      source_key: "constraint:capacity",
      relationship_type: "CONSTRAINT_RESOLVED_BY_COMPANY",
      target_type: "Company",
      target_key: "company:TSM",
      evidence_ids: [14],
    },
  ],
  evidence_count: 4,
  dependency_paths: [{
    path_id: "path-1",
    depth: 4,
    nodes: [
      { node_type: "Theme", canonical_key: "theme:hbm", display_name: "HBM", aliases: [], external_ids: {} },
      { node_type: "Technology", canonical_key: "technology:tsv", display_name: "TSV", aliases: [], external_ids: {} },
      { node_type: "Process", canonical_key: "process:bonding", display_name: "Wafer Bonding", aliases: [], external_ids: {} },
      { node_type: "Constraint", canonical_key: "constraint:capacity", display_name: "Capacity", aliases: [], external_ids: {} },
      { node_type: "Company", canonical_key: "company:TSM", display_name: "TSMC", aliases: [], external_ids: {} },
    ],
    evidence_ids: [11, 12, 13, 14],
  }],
  counts_by_type: { Theme: 1, Technology: 1, Process: 1, Constraint: 1, Company: 1 },
};

export function industrialGraphProjectionContractTest() {
  const projected = projectIndustrialGraph(graph);
  return {
    bottleneckCentered:
      projected.constraintAnchor?.node.canonical_key === "constraint:capacity"
      && projected.upstreamNodes.every((node) => node.x < projected.constraintAnchor!.x)
      && projected.companyGroups.flatMap((group) => group.nodes)
        .every((node) => node.x > projected.constraintAnchor!.x),
    focusPathDeterministic: projected.focusPathId === "path-1",
    persistedEdgesOnly: projected.edges.length === graph.edges.length,
    relationshipPreserved: projected.edges[0]?.relationshipType === "USES_TECHNOLOGY",
    evidencePreserved: projected.edges[0]?.evidenceIds.join(",") === "11",
    noPathAdjacencyEdge:
      !projected.edges.some((edge) => (
        edge.sourceKey === "technology:tsv" && edge.targetKey === "company:TSM"
      )),
  };
}
