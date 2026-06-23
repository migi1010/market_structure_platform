import {
  RESEARCH_OS_ENTITY_KINDS,
  interactionForWorkspaceEvent,
  researchOsInteractionSequence,
} from "./researchOsInteractionContract";

export function researchOsInteractionContractTest() {
  const sequence = researchOsInteractionSequence();

  return {
    allEntityKindsCovered:
      RESEARCH_OS_ENTITY_KINDS.join(">")
      === "theme>sector>company>supply-chain-node>scout-candidate>pipeline-case>decision-packet",
    workspaceHoverPreviews:
      interactionForWorkspaceEvent("theme", "hover").effect === "preview",
    workspaceSingleClickOpensDock:
      RESEARCH_OS_ENTITY_KINDS.every((kind) => interactionForWorkspaceEvent(kind, "single_click").effect === "context_dock"),
    workspaceDoubleClickNavigates:
      RESEARCH_OS_ENTITY_KINDS.every((kind) => interactionForWorkspaceEvent(kind, "double_click").effect === "open_workspace"),
    keyboardEnterMatchesDoubleClick:
      RESEARCH_OS_ENTITY_KINDS.every((kind) => (
        interactionForWorkspaceEvent(kind, "enter").effect
        === interactionForWorkspaceEvent(kind, "double_click").effect
      )),
    escapeClosesContext:
      RESEARCH_OS_ENTITY_KINDS.every((kind) => interactionForWorkspaceEvent(kind, "escape").effect === "close_context"),
    canonicalSequence:
      sequence.map((step) => `${step.event}:${step.effect}`).join(">")
      === "hover:preview>single_click:context_dock>double_click:open_workspace",
  };
}
