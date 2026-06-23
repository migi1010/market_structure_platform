export const GLOBAL_SEARCH_KEYBOARD_EVENTS = ["enter", "escape", "arrow_down", "arrow_up"] as const;

export type GlobalSearchEvent = "single_click" | "double_click" | "enter" | "escape" | "arrow_down" | "arrow_up";
export type GlobalSearchEffect = "preview" | "open_workspace" | "close_search" | "move_selection";

export interface GlobalSearchAction {
  event: GlobalSearchEvent;
  effect: GlobalSearchEffect;
  navigates: boolean;
  opensContextDock: boolean;
}

const SEARCH_ACTIONS: Record<GlobalSearchEvent, GlobalSearchAction> = {
  single_click: { event: "single_click", effect: "preview", navigates: false, opensContextDock: false },
  double_click: { event: "double_click", effect: "open_workspace", navigates: true, opensContextDock: false },
  enter: { event: "enter", effect: "open_workspace", navigates: true, opensContextDock: false },
  escape: { event: "escape", effect: "close_search", navigates: false, opensContextDock: false },
  arrow_down: { event: "arrow_down", effect: "move_selection", navigates: false, opensContextDock: false },
  arrow_up: { event: "arrow_up", effect: "move_selection", navigates: false, opensContextDock: false },
};

export function globalSearchActionForEvent(event: GlobalSearchEvent): GlobalSearchAction {
  return SEARCH_ACTIONS[event];
}

export function globalSearchContract() {
  return {
    summary: "single_click:preview;double_click:open_workspace;enter:open_workspace;escape:close_search",
    actions: SEARCH_ACTIONS,
  };
}
