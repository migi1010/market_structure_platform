export type WorkspaceKey = "rotation" | "scout" | "theme" | "supplyChain" | "stock";

export interface WorkspaceSurfaceContract {
  question: string;
  primary: string[];
  forbidden: string[];
}

export type WorkspaceSurfaceContracts = Record<WorkspaceKey, WorkspaceSurfaceContract>;

export interface ResponsibilityAudit {
  duplicatePrimarySurfaces: string[];
  forbiddenPrimarySurfaces: Array<{ workspace: WorkspaceKey; surface: string }>;
}

export function buildWorkspacePrimarySurfaces(): WorkspaceSurfaceContracts {
  return {
    rotation: {
      question: "Where is capital moving?",
      primary: ["treemap", "market-diagnostics", "capital-flow-story", "selected-sector-intelligence", "theme-ranking"],
      forbidden: ["bottleneck", "controllers", "beneficiaries", "opportunities", "supply-chain-graph", "decision-packet"],
    },
    scout: {
      question: "What themes deserve research?",
      primary: ["top-themes-worth-research", "why-this-theme-matters", "research-queue", "evidence"],
      forbidden: ["industrial-graph", "controllers", "opportunity-ranking", "decision-packets"],
    },
    theme: {
      question: "Why does this theme matter?",
      primary: ["theme-selector", "thesis", "why-now", "catalysts", "risks", "research-gaps", "research-objects-summary"],
      forbidden: ["industrial-dependency-graph", "supply-chain-visualization", "pipeline-board", "decision-packet"],
    },
    supplyChain: {
      question: "How does this industry work?",
      primary: ["bottleneck", "constraint-network", "industrial-dependency-map"],
      forbidden: ["thesis", "conviction", "investment-memo", "decision-packet"],
    },
    stock: {
      question: "Which company benefits?",
      primary: [
        "company-header",
        "supply-chain-role",
        "theme-exposure",
        "investment-thesis",
        "evidence-chain",
        "research-completeness",
        "decision-support",
        "related-companies",
      ],
      forbidden: ["treemap", "capital-flow-story", "scout-queue", "theme-ranking-panel", "dependency-graph", "pipeline-board"],
    },
  };
}

export function assertWorkspaceResponsibilities(contracts: WorkspaceSurfaceContracts): ResponsibilityAudit {
  const ownership = new Map<string, WorkspaceKey>();
  const duplicatePrimarySurfaces: string[] = [];
  const forbiddenPrimarySurfaces: Array<{ workspace: WorkspaceKey; surface: string }> = [];

  (Object.entries(contracts) as Array<[WorkspaceKey, WorkspaceSurfaceContract]>).forEach(([workspace, contract]) => {
    contract.primary.forEach((surface) => {
      const owner = ownership.get(surface);
      if (owner && owner !== workspace && !duplicatePrimarySurfaces.includes(surface)) {
        duplicatePrimarySurfaces.push(surface);
      }
      ownership.set(surface, workspace);
      if (contract.forbidden.includes(surface)) {
        forbiddenPrimarySurfaces.push({ workspace, surface });
      }
    });
  });

  return {
    duplicatePrimarySurfaces,
    forbiddenPrimarySurfaces,
  };
}

export function buildDecisionMemoHierarchy() {
  return {
    primary: ["summary", "bull_case", "bear_case"],
    secondary: ["evidence_strength", "research_gaps"],
    tertiary: ["monitoring_triggers", "scenario_matrix", "open_questions", "lineage"],
  };
}

export function buildPipelineLifecycleHierarchy() {
  return {
    primary: ["current-stage", "progress", "key-bottleneck"],
    secondary: ["timeline"],
    tertiary: ["evidence-audit"],
  };
}

export function buildResearchOsVisualContract() {
  return {
    workspaceOrder: ["rotation", "scout", "themes", "supply-chain", "stock"],
    languagePriority: ["zh", "en"],
    layoutPrinciple: "task-specific-institutional-terminal",
  };
}
