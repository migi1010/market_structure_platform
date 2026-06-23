import {
  PIPELINE_BOARD_COLUMNS,
  buildPipelineBoard,
  buildPipelineWorkspaceHierarchy,
  calculatePipelineProgress,
  nextPipelineStatus,
} from "./researchPipeline";
import type { ResearchPipelineCaseDetail } from "@/types/stock";

const detail: ResearchPipelineCaseDetail = {
  case: {
    case_id: "research-case-1",
    source_type: "SCOUT_CANDIDATE",
    source_id: "candidate:ai-infrastructure-constraint-watch",
    theme_id: "ai_infrastructure",
    title: "AI Infrastructure Constraint Watch",
    status: "RESEARCHING",
    created_at: "2026-06-19T00:00:00Z",
    updated_at: "2026-06-19T00:00:00Z",
    activated_at: null,
    archived_at: null,
    lineage_checksum: "checksum",
  },
  timeline: [],
  links: [
    { link_id: "link-1", case_id: "research-case-1", linked_type: "THEME", linked_id: "ai_infrastructure", created_at: "2026-06-19T00:00:00Z" },
    { link_id: "link-2", case_id: "research-case-1", linked_type: "CONTROLLER", linked_id: "controller:1", created_at: "2026-06-19T00:00:00Z" },
  ],
  progress: {
    percent: 40,
    sections: {
      theme_narrative: true,
      supply_chain_validation: false,
      controller_review: true,
      opportunity_review: false,
      decision_packet_link: false,
    },
  },
};

export function researchPipelineContractTest() {
  const board = buildPipelineBoard([detail]);
  const hierarchy = buildPipelineWorkspaceHierarchy();
  return {
    boardColumns:
      PIPELINE_BOARD_COLUMNS.join(">") === "DISCOVERED>OBSERVING>RESEARCHING>VALIDATING>REVIEW_READY>MONITORING",
    researchingColumnContainsCase: board.RESEARCHING[0]?.case.case_id === "research-case-1",
    archivedExcludedFromBoard: buildPipelineBoard([{ ...detail, case: { ...detail.case, status: "ARCHIVED" } }]).ARCHIVED === undefined,
    progressUsesCompletionOnly: calculatePipelineProgress(detail.links).percent === 40,
    lifecycleNextStep: nextPipelineStatus("RESEARCHING") === "VALIDATING",
    monitoringHasNoAutomaticNextStep: nextPipelineStatus("MONITORING") === null,
    lifecycleOnlyHierarchy:
      hierarchy.primary.join(">") === "current-stage>progress>key-bottleneck"
      && hierarchy.secondary.join(">") === "timeline"
      && hierarchy.tertiary.join(">") === "evidence-audit"
      && hierarchy.forbidden.includes("theme-memo")
      && hierarchy.forbidden.includes("supply-chain-graph"),
  };
}
