import {
  DECISION_INTELLIGENCE_SECTION_ORDER,
  buildDecisionIntelligenceMemoHierarchy,
  decisionIntelligenceEvidenceState,
  decisionIntelligenceContainsForbiddenLanguage,
  summarizeDecisionIntelligencePacket,
} from "./decisionIntelligence";
import type { DecisionIntelligencePacket } from "@/types/stock";

const packet: DecisionIntelligencePacket = {
  packet_id: "decision-intelligence:research-case-1",
  title: "AI Infrastructure Constraint Watch",
  theme_id: "ai_infrastructure",
  status: "DISCOVERED",
  checksum: "checksum",
  lineage: {
    scout_candidate_id: "candidate:ai",
    research_case_id: "research-case-1",
    theme_id: "ai_infrastructure",
    graph_snapshot_id: 1,
    controller_snapshot_id: 2,
    opportunity_snapshot_id: 3,
    decision_packet_family_version: "packet-v1",
    decision_packet_family_revision: 1,
    evidence_ids: ["graph_evidence:148"],
  },
  answers: {
    currently_known: [{ label: "Theme", value: "AI Infrastructure" }],
    still_unknown: [{ question: "Which resolver is evidenced?" }],
    supporting_evidence: [{ label: "Evidence references", value: 1 }],
    invalidation_conditions: [{ label: "Constraint removed" }],
  },
  sections: {
    summary: [{ label: "Theme", value: "AI Infrastructure" }],
    bull_case: [{ label: "Controller path", evidence_ids: ["graph_evidence:148"] }],
    bear_case: [{ label: "Coverage gap", state: "unresolved" }],
    evidence_strength: [{ label: "Evidence references", value: 1 }],
    research_gaps: [{ label: "Missing opportunity evidence" }],
    monitoring_triggers: [{ label: "Constraint removed" }],
    scenario_matrix: [{ scenario: "BASE", condition: "Evidence unchanged" }],
    open_questions: [{ question: "Which resolver is evidenced?" }],
    lineage: [{ research_case_id: "research-case-1" }],
  },
};

export function decisionIntelligenceContractTest() {
  const summary = summarizeDecisionIntelligencePacket(packet);
  const hierarchy = buildDecisionIntelligenceMemoHierarchy();
  return {
    sectionOrder:
      DECISION_INTELLIGENCE_SECTION_ORDER.join(">") ===
      "summary>bull_case>bear_case>evidence_strength>research_gaps>monitoring_triggers>scenario_matrix>open_questions>lineage",
    lineageVisible: summary.lineageLabel.includes("research-case-1") && summary.lineageLabel.includes("packet-v1"),
    evidenceVisible: summary.evidenceCount === 1,
    gapsVisible: summary.gapCount === 1,
    triggersVisible: summary.triggerCount === 1,
    primaryMemoHierarchy:
      hierarchy.primary.join(">") === "summary>bull_case>bear_case",
    secondaryMemoHierarchy:
      hierarchy.secondary.join(">") === "evidence_strength>research_gaps",
    tertiaryMemoHierarchy:
      hierarchy.tertiary.join(">") === "monitoring_triggers>scenario_matrix>open_questions>lineage",
    forbiddenWorkspaceSurfacesExcluded:
      hierarchy.excludedWorkspaceSurfaces.includes("treemap")
      && hierarchy.excludedWorkspaceSurfaces.includes("supply-chain-graph")
      && hierarchy.excludedWorkspaceSurfaces.includes("research-queue"),
    forbiddenLanguageRejected: decisionIntelligenceContainsForbiddenLanguage({
      ...packet,
      sections: { ...packet.sections, summary: [{ recommendation: "accumulate" }] },
    }),
    cleanPacketAllowed: !decisionIntelligenceContainsForbiddenLanguage(packet),
    zeroEvidenceIsResearchIncomplete:
      decisionIntelligenceEvidenceState(0) === "Research Incomplete"
      && decisionIntelligenceEvidenceState(3) === "Evidence Available",
  };
}
