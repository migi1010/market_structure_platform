import type { OmniboxTargetTab } from "@/types/stock";

export type TerminalModuleId = OmniboxTargetTab;
export type TerminalWorkspaceType = "stock" | "theme" | "sector" | "portfolio" | "alpha" | "general";
export type TerminalIconKey =
  | "activity"
  | "bell"
  | "bookmark"
  | "brain-circuit"
  | "briefcase"
  | "layout-dashboard"
  | "line-chart"
  | "newspaper"
  | "panels-top-left"
  | "radar"
  | "refresh-cw"
  | "scan-search"
  | "search"
  | "settings-2"
  | "star"
  | "waves";
export type TerminalRailGroup = "top" | "middle" | "bottom";

export interface TerminalModule {
  id: TerminalModuleId;
  title: string;
  shortTitle: string;
  labelZh: string;
  labelEn: string;
  description: string;
  iconKey: TerminalIconKey;
  railGroup: TerminalRailGroup;
  target_tab: OmniboxTargetTab;
  searchKeywords: string[];
  workspaceType: TerminalWorkspaceType;
  enabled: boolean;
  order: number;
}

export const terminalModules: TerminalModule[] = [
  {
    id: "theme-intelligence",
    title: "主題指揮中心 Theme Command Center",
    shortTitle: "Themes",
    labelZh: "主題",
    labelEn: "Command",
    description: "Theme leadership, capital flow, and beneficiary stock intelligence",
    iconKey: "layout-dashboard",
    railGroup: "top",
    target_tab: "theme-intelligence",
    searchKeywords: ["theme", "themes", "theme intelligence", "theme command center", "macro themes", "ai themes"],
    workspaceType: "theme",
    enabled: true,
    order: 10,
  },
  {
    id: "portfolio",
    title: "觀察名單 Portfolio",
    shortTitle: "Portfolio",
    labelZh: "觀察",
    labelEn: "Portfolio",
    description: "Institutional watchlist and portfolio command center",
    iconKey: "star",
    railGroup: "bottom",
    target_tab: "portfolio",
    searchKeywords: ["portfolio", "watchlist", "holdings", "positions"],
    workspaceType: "portfolio",
    enabled: true,
    order: 20,
  },
  {
    id: "theme-forecast",
    title: "主題預測 Forecast",
    shortTitle: "Forecast",
    labelZh: "預測",
    labelEn: "Forecast",
    description: "Forward theme leadership forecasts, regime overlays, and validation diagnostics",
    iconKey: "brain-circuit",
    railGroup: "middle",
    target_tab: "theme-forecast",
    searchKeywords: ["forecast", "theme forecast", "future themes", "theme ai", "regime forecast"],
    workspaceType: "theme",
    enabled: true,
    order: 25,
  },
  {
    id: "alpha-quant",
    title: "因子訊號 Signals",
    shortTitle: "Alpha",
    labelZh: "訊號",
    labelEn: "Signals",
    description: "Alpha ranking, factor scores, and quant recommendations",
    iconKey: "activity",
    railGroup: "middle",
    target_tab: "alpha-quant",
    searchKeywords: ["alpha", "alpha quant", "ranking", "rankings", "top alpha", "factors"],
    workspaceType: "alpha",
    enabled: true,
    order: 30,
  },
  {
    id: "market-intel",
    title: "板塊輪動 Rotation",
    shortTitle: "Sectors",
    labelZh: "輪動",
    labelEn: "Rotation",
    description: "Sector leadership, rotation, and relative strength analytics",
    iconKey: "refresh-cw",
    railGroup: "middle",
    target_tab: "market-intel",
    searchKeywords: ["sector", "sectors", "sector rotation", "market intel", "relative strength"],
    workspaceType: "sector",
    enabled: true,
    order: 40,
  },
  {
    id: "stock-analysis",
    title: "個股工作區 Workspace",
    shortTitle: "Stock",
    labelZh: "工作區",
    labelEn: "Workspace",
    description: "Single-stock intelligence workspace with quote, valuation, and regime context",
    iconKey: "panels-top-left",
    railGroup: "middle",
    target_tab: "stock-analysis",
    searchKeywords: ["stock", "stock analysis", "ticker", "equity", "quote"],
    workspaceType: "stock",
    enabled: true,
    order: 50,
  },
];

export const enabledTerminalModules = terminalModules
  .filter((module) => module.enabled)
  .sort((left, right) => left.order - right.order);

export function getTerminalModule(id: OmniboxTargetTab | string | undefined): TerminalModule | undefined {
  return terminalModules.find((module) => module.id === id);
}
