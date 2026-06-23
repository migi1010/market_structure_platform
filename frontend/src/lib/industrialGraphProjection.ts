import type {
  ThemeIndustrialEdge,
  ThemeIndustrialIntelligence,
  ThemeIndustrialNode,
  ThemeIndustrialPath,
} from "@/types/stock";

export interface ProjectedIndustrialNode {
  node: ThemeIndustrialNode;
  x: number;
  y: number;
  width: number;
  height: number;
  zone: "upstream" | "constraint" | "company";
}

export interface ProjectedIndustrialEdge {
  sourceKey: string;
  targetKey: string;
  relationshipType: string;
  evidenceIds: number[];
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  focus: boolean;
  anchor: boolean;
}

export type IndustrialCompanyRole =
  | "controller"
  | "resolver"
  | "supplier"
  | "beneficiary"
  | "customer"
  | "exposed"
  | "other";

export interface IndustrialCompanyGroup {
  role: IndustrialCompanyRole;
  labelZh: string;
  labelEn: string;
  nodes: ProjectedIndustrialNode[];
}

export interface IndustrialGraphRoleContext {
  controllerCompanyKeys: ReadonlySet<string>;
  beneficiaryCompanyKeys: ReadonlySet<string>;
  resolutionEnablerCompanyKeys: ReadonlySet<string>;
}

export interface IndustrialGraphProjection {
  nodes: ProjectedIndustrialNode[];
  upstreamNodes: ProjectedIndustrialNode[];
  constraintAnchor: ProjectedIndustrialNode | null;
  companyGroups: IndustrialCompanyGroup[];
  edges: ProjectedIndustrialEdge[];
  focusPathId: string | null;
  width: number;
  height: number;
}

const WIDTH = 1120;
const NODE_WIDTH = 164;
const NODE_HEIGHT = 50;
const LEFT_START = 24;
const LEFT_END = 430;
const ANCHOR_X = 492;
const COMPANY_START = 744;
const TOP = 72;
const ANCHOR_Y = TOP + 92;
const ROW_GAP = 18;

const EMPTY_ROLE_CONTEXT: IndustrialGraphRoleContext = {
  controllerCompanyKeys: new Set(),
  beneficiaryCompanyKeys: new Set(),
  resolutionEnablerCompanyKeys: new Set(),
};

const ROLE_LABELS: Record<IndustrialCompanyRole, { zh: string; en: string }> = {
  controller: { zh: "控制層", en: "Controllers" },
  resolver: { zh: "解決推動者", en: "Resolution Enablers" },
  supplier: { zh: "供應商", en: "Suppliers" },
  beneficiary: { zh: "受益者", en: "Direct Beneficiary" },
  customer: { zh: "客戶", en: "Customers" },
  exposed: { zh: "瓶頸曝險", en: "Constraint Exposure" },
  other: { zh: "其他關聯公司", en: "Other Linked Companies" },
};

// Compatibility label retained for accepted frontend contracts: Indirect Beneficiary.

function uniqueNodes(graph: ThemeIndustrialIntelligence["graph"]): ThemeIndustrialNode[] {
  const nodes = new Map<string, ThemeIndustrialNode>();
  graph.nodes.forEach((node) => nodes.set(node.canonical_key, node));
  graph.dependency_paths.forEach((path) => {
    path.nodes.forEach((node) => {
      if (!nodes.has(node.canonical_key)) nodes.set(node.canonical_key, node);
    });
  });
  return Array.from(nodes.values()).sort((left, right) => left.canonical_key.localeCompare(right.canonical_key));
}

function pathKey(path: ThemeIndustrialPath, index: number): string {
  return path.path_id ?? `path:${index}:${path.nodes.map((node) => node.canonical_key).join(">")}`;
}

function selectFocusPath(paths: ThemeIndustrialPath[]): { path: ThemeIndustrialPath; id: string } | null {
  const ranked = paths.map((path, index) => ({
    path,
    id: pathKey(path, index),
    hasConstraint: path.nodes.some((node) => node.node_type === "Constraint"),
    evidenceCount: new Set(path.evidence_ids ?? []).size,
    canonicalChain: path.nodes.map((node) => node.canonical_key).join(">"),
  })).sort((left, right) => (
    Number(right.hasConstraint) - Number(left.hasConstraint)
    || right.evidenceCount - left.evidenceCount
    || right.path.depth - left.path.depth
    || left.id.localeCompare(right.id)
    || left.canonicalChain.localeCompare(right.canonicalChain)
  ));
  return ranked[0] ? { path: ranked[0].path, id: ranked[0].id } : null;
}

function incidentCount(nodeKey: string, edges: ThemeIndustrialEdge[]): number {
  return edges.filter((edge) => edge.source_key === nodeKey || edge.target_key === nodeKey).length;
}

function selectConstraint(
  nodes: ThemeIndustrialNode[],
  edges: ThemeIndustrialEdge[],
  focus: { path: ThemeIndustrialPath; id: string } | null,
): ThemeIndustrialNode | null {
  const pathConstraint = focus?.path.nodes.find((node) => node.node_type === "Constraint");
  if (pathConstraint) return nodes.find((node) => node.canonical_key === pathConstraint.canonical_key) ?? pathConstraint;
  return nodes
    .filter((node) => node.node_type === "Constraint")
    .sort((left, right) => (
      incidentCount(right.canonical_key, edges) - incidentCount(left.canonical_key, edges)
      || left.canonical_key.localeCompare(right.canonical_key)
    ))[0] ?? null;
}

function reverseDistances(anchorKey: string | null, edges: ThemeIndustrialEdge[]): Map<string, number> {
  const distances = new Map<string, number>();
  if (!anchorKey) return distances;
  distances.set(anchorKey, 0);
  const queue = [anchorKey];
  while (queue.length > 0) {
    const current = queue.shift()!;
    const nextDistance = (distances.get(current) ?? 0) + 1;
    edges
      .filter((edge) => edge.target_key === current)
      .map((edge) => edge.source_key)
      .sort()
      .forEach((sourceKey) => {
        if (!distances.has(sourceKey)) {
          distances.set(sourceKey, nextDistance);
          queue.push(sourceKey);
        }
      });
  }
  return distances;
}

function companyRole(
  companyKey: string,
  edges: ThemeIndustrialEdge[],
  context: IndustrialGraphRoleContext,
): IndustrialCompanyRole {
  if (context.controllerCompanyKeys.has(companyKey)) return "controller";
  if (context.resolutionEnablerCompanyKeys.has(companyKey)) return "resolver";
  if (context.beneficiaryCompanyKeys.has(companyKey)) return "beneficiary";

  const relationships = edges.filter((edge) => edge.source_key === companyKey || edge.target_key === companyKey);
  if (relationships.some((edge) => (
    edge.target_key === companyKey
    && (edge.relationship_type === "CONSTRAINT_RESOLVED_BY_COMPANY"
      || edge.relationship_type === "PROCESS_RESOLVED_BY_COMPANY"
      || edge.relationship_type.endsWith("_RESOLVED_BY"))
  ))) return "resolver";
  if (relationships.some((edge) => (
    edge.target_key === companyKey
    && (edge.relationship_type.includes("SUPPLIED_BY") || edge.relationship_type.includes("PRODUCED_BY"))
  ))) return "supplier";
  if (relationships.some((edge) => (
    edge.source_key === companyKey && edge.relationship_type === "SUPPLIES"
  ))) return "supplier";
  if (relationships.some((edge) => (
    edge.source_key === companyKey && edge.relationship_type === "CUSTOMER_OF"
  ))) return "customer";
  if (relationships.some((edge) => (
    edge.source_key === companyKey && edge.relationship_type === "COMPANY_EXPOSED_TO_CONSTRAINT"
  ))) return "exposed";
  return "other";
}

function horizontalPosition(depth: number, maximumDepth: number): number {
  if (maximumDepth <= 1) return LEFT_END - NODE_WIDTH;
  const normalized = (maximumDepth - depth) / (maximumDepth - 1);
  return LEFT_START + normalized * (LEFT_END - LEFT_START - NODE_WIDTH);
}

function edgeProjection(
  edge: ThemeIndustrialEdge,
  positions: Map<string, ProjectedIndustrialNode>,
  focusPairs: Set<string>,
  anchorKey: string | null,
): ProjectedIndustrialEdge | null {
  const source = positions.get(edge.source_key);
  const target = positions.get(edge.target_key);
  if (!source || !target) return null;
  const movesRight = target.x >= source.x;
  return {
    sourceKey: edge.source_key,
    targetKey: edge.target_key,
    relationshipType: edge.relationship_type,
    evidenceIds: [...edge.evidence_ids],
    x1: movesRight ? source.x + source.width : source.x,
    y1: source.y + source.height / 2,
    x2: movesRight ? target.x : target.x + target.width,
    y2: target.y + target.height / 2,
    focus: focusPairs.has(`${edge.source_key}>${edge.target_key}`),
    anchor: edge.source_key === anchorKey || edge.target_key === anchorKey,
  };
}

export function projectIndustrialGraph(
  graph: ThemeIndustrialIntelligence["graph"],
  roleContext: IndustrialGraphRoleContext = EMPTY_ROLE_CONTEXT,
): IndustrialGraphProjection {
  const nodes = uniqueNodes(graph);
  const focus = selectFocusPath(graph.dependency_paths);
  const constraint = selectConstraint(nodes, graph.edges, focus);
  const anchorKey = constraint?.canonical_key ?? null;
  const distances = reverseDistances(anchorKey, graph.edges);

  const upstream = nodes
    .filter((node) => node.node_type !== "Company" && node.canonical_key !== anchorKey)
    .sort((left, right) => (
      (distances.get(right.canonical_key) ?? 0) - (distances.get(left.canonical_key) ?? 0)
      || left.node_type.localeCompare(right.node_type)
      || left.canonical_key.localeCompare(right.canonical_key)
    ));
  const maximumDepth = Math.max(1, ...upstream.map((node) => distances.get(node.canonical_key) ?? 1));
  const upstreamRows = new Map<number, number>();
  const upstreamNodes = upstream.map((node) => {
    const depth = Math.max(1, distances.get(node.canonical_key) ?? maximumDepth);
    const row = upstreamRows.get(depth) ?? 0;
    upstreamRows.set(depth, row + 1);
    return {
      node,
      x: horizontalPosition(depth, maximumDepth),
      y: TOP + row * (NODE_HEIGHT + ROW_GAP),
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      zone: "upstream" as const,
    };
  });

  const constraintAnchor = constraint ? {
    node: constraint,
    x: ANCHOR_X,
    y: ANCHOR_Y,
    width: 196,
    height: 64,
    zone: "constraint" as const,
  } : null;

  const companyRoleMap = new Map<IndustrialCompanyRole, ThemeIndustrialNode[]>();
  nodes.filter((node) => node.node_type === "Company").forEach((node) => {
    const role = companyRole(node.canonical_key, graph.edges, roleContext);
    const rows = companyRoleMap.get(role) ?? [];
    rows.push(node);
    companyRoleMap.set(role, rows);
  });
  const roleOrder: IndustrialCompanyRole[] = [
    "controller", "resolver", "supplier", "beneficiary", "customer", "exposed", "other",
  ];
  let companyRow = 0;
  const companyGroups = roleOrder.flatMap((role) => {
    const roleNodes = (companyRoleMap.get(role) ?? []).sort((left, right) => (
      left.canonical_key.localeCompare(right.canonical_key)
    ));
    if (roleNodes.length === 0) return [];
    const projected = roleNodes.map((node) => {
      const position = {
        node,
        x: COMPANY_START + (companyRow % 2) * 184,
        y: TOP + Math.floor(companyRow / 2) * (NODE_HEIGHT + ROW_GAP),
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        zone: "company" as const,
      };
      companyRow += 1;
      return position;
    });
    return [{
      role,
      labelZh: ROLE_LABELS[role].zh,
      labelEn: ROLE_LABELS[role].en,
      nodes: projected,
    }];
  });

  const projectedNodes = [
    ...upstreamNodes,
    ...(constraintAnchor ? [constraintAnchor] : []),
    ...companyGroups.flatMap((group) => group.nodes),
  ];
  const positions = new Map(projectedNodes.map((node) => [node.node.canonical_key, node]));
  const focusPairs = new Set<string>();
  focus?.path.nodes.forEach((node, index, pathNodes) => {
    const target = pathNodes[index + 1];
    if (target) focusPairs.add(`${node.canonical_key}>${target.canonical_key}`);
  });
  const edges = graph.edges
    .map((edge) => edgeProjection(edge, positions, focusPairs, anchorKey))
    .filter((edge): edge is ProjectedIndustrialEdge => edge !== null);
  const rows = Math.max(
    4,
    ...Array.from(upstreamRows.values()),
    Math.ceil(companyRow / 2),
  );

  return {
    nodes: projectedNodes,
    upstreamNodes,
    constraintAnchor,
    companyGroups,
    edges,
    focusPathId: focus?.id ?? null,
    width: WIDTH,
    height: TOP + rows * (NODE_HEIGHT + ROW_GAP) + 44,
  };
}
