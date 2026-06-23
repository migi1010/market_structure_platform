import type {
  DecisionIntelligencePacket,
  DecisionIntelligenceRow,
  DecisionIntelligenceSectionKey,
} from "@/types/stock";

export const DECISION_INTELLIGENCE_SECTION_ORDER: DecisionIntelligenceSectionKey[] = [
  "summary",
  "bull_case",
  "bear_case",
  "evidence_strength",
  "research_gaps",
  "monitoring_triggers",
  "scenario_matrix",
  "open_questions",
  "lineage",
];

export function buildDecisionIntelligenceMemoHierarchy() {
  return {
    primary: ["summary", "bull_case", "bear_case"] as DecisionIntelligenceSectionKey[],
    secondary: ["evidence_strength", "research_gaps"] as DecisionIntelligenceSectionKey[],
    tertiary: ["monitoring_triggers", "scenario_matrix", "open_questions", "lineage"] as DecisionIntelligenceSectionKey[],
    excludedWorkspaceSurfaces: ["treemap", "supply-chain-graph", "research-queue"],
  };
}

const FORBIDDEN_LANGUAGE = [
  "buy",
  "sell",
  "hold",
  "target price",
  "target_price",
  "allocation",
  "portfolio weight",
  "recommendation",
  "valuation model",
  "fair value",
];

export function decisionIntelligenceContainsForbiddenLanguage(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(decisionIntelligenceContainsForbiddenLanguage);
  if (!value || typeof value !== "object") return false;
  return Object.entries(value as Record<string, unknown>).some(([key, item]) => {
    const normalizedKey = key.toLowerCase().replace(/[_-]+/g, " ");
    return FORBIDDEN_LANGUAGE.includes(normalizedKey) || decisionIntelligenceContainsForbiddenLanguage(item);
  });
}

export function summarizeDecisionIntelligencePacket(packet: DecisionIntelligencePacket) {
  return {
    packetId: packet.packet_id,
    title: packet.title,
    themeId: packet.theme_id,
    status: packet.status,
    evidenceCount: packet.lineage.evidence_ids.length,
    gapCount: packet.sections.research_gaps.length,
    triggerCount: packet.sections.monitoring_triggers.length,
    lineageLabel: [
      packet.lineage.research_case_id,
      packet.lineage.decision_packet_family_version,
      packet.lineage.graph_snapshot_id ? `graph:${packet.lineage.graph_snapshot_id}` : "",
    ].filter(Boolean).join(" / "),
  };
}

export function rowLabel(row: DecisionIntelligenceRow): string {
  return String(row.label ?? row.question ?? row.scenario ?? row.value ?? "Structured row");
}

export function rowMeta(row: DecisionIntelligenceRow): string {
  return String(row.source ?? row.state ?? row.condition ?? "");
}

export function decisionIntelligenceEvidenceState(evidenceCount: number): "Research Incomplete" | "Evidence Available" {
  return evidenceCount > 0 ? "Evidence Available" : "Research Incomplete";
}
