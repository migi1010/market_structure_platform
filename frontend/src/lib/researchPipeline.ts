import type {
  ResearchPipelineCaseDetail,
  ResearchPipelineLinkedType,
  ResearchPipelineLink,
  ResearchPipelineProgress,
  ResearchPipelineStatus,
} from "@/types/stock";

export const PIPELINE_STATUSES: ResearchPipelineStatus[] = [
  "DISCOVERED",
  "OBSERVING",
  "RESEARCHING",
  "VALIDATING",
  "REVIEW_READY",
  "APPROVED_RESEARCH",
  "MONITORING",
  "ARCHIVED",
];

export const PIPELINE_BOARD_COLUMNS: ResearchPipelineStatus[] = [
  "DISCOVERED",
  "OBSERVING",
  "RESEARCHING",
  "VALIDATING",
  "REVIEW_READY",
  "MONITORING",
];

export const PIPELINE_STAGE_LABELS: Record<ResearchPipelineStatus, { zh: string; en: string }> = {
  DISCOVERED: { zh: "已發現", en: "Discovered" },
  OBSERVING: { zh: "觀察中", en: "Observing" },
  RESEARCHING: { zh: "研究中", en: "Researching" },
  VALIDATING: { zh: "驗證中", en: "Validating" },
  REVIEW_READY: { zh: "待審閱", en: "Review Ready" },
  APPROVED_RESEARCH: { zh: "研究核准", en: "Approved Research" },
  MONITORING: { zh: "監控中", en: "Monitoring" },
  ARCHIVED: { zh: "已封存", en: "Archived" },
};

const PROGRESS_SECTIONS: Array<{
  key: keyof ResearchPipelineProgress["sections"];
  types: ResearchPipelineLinkedType[];
}> = [
  { key: "theme_narrative", types: ["THEME"] },
  { key: "supply_chain_validation", types: ["SUPPLY_CHAIN_VALIDATION", "GRAPH_SNAPSHOT"] },
  { key: "controller_review", types: ["CONTROLLER"] },
  { key: "opportunity_review", types: ["OPPORTUNITY"] },
  { key: "decision_packet_link", types: ["DECISION_PACKET"] },
];

export function calculatePipelineProgress(links: ResearchPipelineLink[]): ResearchPipelineProgress {
  const linkedTypes = new Set(links.map((link) => link.linked_type));
  const sections = PROGRESS_SECTIONS.reduce((acc, section) => {
    acc[section.key] = section.types.some((type) => linkedTypes.has(type));
    return acc;
  }, {} as ResearchPipelineProgress["sections"]);
  return {
    sections,
    percent: Object.values(sections).filter(Boolean).length * 20,
  };
}

export function buildPipelineBoard(details: ResearchPipelineCaseDetail[]) {
  return PIPELINE_BOARD_COLUMNS.reduce((board, status) => {
    board[status] = details
      .filter((detail) => detail.case.status === status)
      .sort((left, right) => left.case.updated_at.localeCompare(right.case.updated_at) * -1);
    return board;
  }, {} as Record<(typeof PIPELINE_BOARD_COLUMNS)[number], ResearchPipelineCaseDetail[]>);
}

export function nextPipelineStatus(status: ResearchPipelineStatus): ResearchPipelineStatus | null {
  if (status === "MONITORING" || status === "ARCHIVED") return null;
  if (status === "APPROVED_RESEARCH") return "MONITORING";
  const index = PIPELINE_STATUSES.indexOf(status);
  const next = PIPELINE_STATUSES[index + 1];
  return next && next !== "ARCHIVED" ? next : null;
}

export function evidenceCount(detail: ResearchPipelineCaseDetail): number {
  return detail.links.filter((link) => link.linked_type !== "SCOUT_CANDIDATE").length;
}

export function primaryBottleneck(detail: ResearchPipelineCaseDetail): string {
  const explicit = detail.links.find((link) => link.linked_type === "SUPPLY_CHAIN_VALIDATION");
  return explicit?.linked_id.replace(/^constraint:/, "").replaceAll("_", " ") || "Pending validation";
}

export function buildPipelineWorkspaceHierarchy() {
  return {
    primary: ["current-stage", "progress", "key-bottleneck"],
    secondary: ["timeline"],
    tertiary: ["evidence-audit"],
    forbidden: ["theme-memo", "supply-chain-graph", "decision-memo", "treemap"],
  };
}
