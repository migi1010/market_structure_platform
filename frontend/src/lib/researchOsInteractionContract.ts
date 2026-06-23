export const RESEARCH_OS_ENTITY_KINDS = [
  "theme",
  "sector",
  "company",
  "supply-chain-node",
  "scout-candidate",
  "pipeline-case",
  "decision-packet",
] as const;

export type ResearchOsEntityKind = (typeof RESEARCH_OS_ENTITY_KINDS)[number];
export type ResearchOsInteractionEvent = "hover" | "single_click" | "double_click" | "enter" | "escape";
export type ResearchOsInteractionEffect = "preview" | "context_dock" | "open_workspace" | "close_context";

export interface ResearchOsInteractionStep {
  event: ResearchOsInteractionEvent;
  effect: ResearchOsInteractionEffect;
}

const WORKSPACE_EVENT_EFFECTS: Record<ResearchOsInteractionEvent, ResearchOsInteractionEffect> = {
  hover: "preview",
  single_click: "context_dock",
  double_click: "open_workspace",
  enter: "open_workspace",
  escape: "close_context",
};

export function interactionForWorkspaceEvent(
  _kind: ResearchOsEntityKind,
  event: ResearchOsInteractionEvent,
): ResearchOsInteractionStep {
  return {
    event,
    effect: WORKSPACE_EVENT_EFFECTS[event],
  };
}

export function researchOsInteractionSequence(): ResearchOsInteractionStep[] {
  return [
    { event: "hover", effect: "preview" },
    { event: "single_click", effect: "context_dock" },
    { event: "double_click", effect: "open_workspace" },
  ];
}
