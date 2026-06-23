import {
  GLOBAL_SEARCH_KEYBOARD_EVENTS,
  globalSearchActionForEvent,
  globalSearchContract,
} from "./researchOsSearchContract";

export function researchOsSearchContractTest() {
  const contract = globalSearchContract();

  return {
    singleClickPreviewsOnly:
      globalSearchActionForEvent("single_click").effect === "preview"
      && globalSearchActionForEvent("single_click").opensContextDock === false
      && globalSearchActionForEvent("single_click").navigates === false,
    doubleClickNavigates:
      globalSearchActionForEvent("double_click").effect === "open_workspace"
      && globalSearchActionForEvent("double_click").navigates === true,
    enterNavigates:
      globalSearchActionForEvent("enter").effect === "open_workspace"
      && globalSearchActionForEvent("enter").navigates === true,
    escapeClosesSearch:
      globalSearchActionForEvent("escape").effect === "close_search",
    keyboardEventsComplete:
      GLOBAL_SEARCH_KEYBOARD_EVENTS.join(">")
      === "enter>escape>arrow_down>arrow_up",
    contractSummary:
      contract.summary
      === "single_click:preview;double_click:open_workspace;enter:open_workspace;escape:close_search",
  };
}
