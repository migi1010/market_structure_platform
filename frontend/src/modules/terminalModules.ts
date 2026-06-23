import type { OmniboxTargetTab } from "@/types/stock";

export type TerminalModuleId = OmniboxTargetTab;
export type TerminalWorkspaceType = "stock" | "theme" | "sector" | "portfolio" | "alpha" | "general";
export type TerminalIconKey =
  | "activity" | "bell" | "bookmark" | "brain-circuit" | "briefcase" | "bar-chart-3"
  | "layout-dashboard" | "line-chart" | "network" | "newspaper" | "panels-top-left"
  | "radar" | "refresh-cw" | "scan-search" | "search" | "settings-2" | "shield-alert"
  | "star" | "waves";
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
  primaryNav?: boolean;
  order: number;
}

export const terminalModules: TerminalModule[] = [
  {
    id: "market-intel",
    title: "資金輪動 Rotation",
    shortTitle: "Rotation",
    labelZh: "資金輪動",
    labelEn: "Rotation",
    description: "Primary market discovery through capital rotation, breadth, relative strength, and sector leadership",
    iconKey: "refresh-cw",
    railGroup: "top",
    target_tab: "market-intel",
    searchKeywords: ["market", "rotation", "sector", "sectors", "sector rotation", "market intel", "relative strength", "capital rotation", "capital flow"],
    workspaceType: "sector",
    enabled: true,
    primaryNav: true,
    order: 10,
  },
  {
    id: "theme-intelligence",
    title: "主題研究 Themes",
    shortTitle: "Themes",
    labelZh: "主題研究",
    labelEn: "Themes",
    description: "Theme intelligence, narratives, beneficiaries, flow, and forecast context",
    iconKey: "layout-dashboard",
    railGroup: "top",
    target_tab: "theme-intelligence",
    searchKeywords: ["theme", "themes", "command", "theme research", "theme intelligence", "narratives", "beneficiaries"],
    workspaceType: "theme",
    enabled: true,
    primaryNav: true,
    order: 30,
  },
  {
    id: "theme-scout",
    title: "主題偵察 Scout",
    shortTitle: "Scout",
    labelZh: "主題偵察",
    labelEn: "Scout",
    description: "Evidence-backed emerging industrial theme candidates and research priorities",
    iconKey: "radar",
    railGroup: "top",
    target_tab: "theme-scout",
    searchKeywords: ["scout", "theme scout", "emerging themes", "theme candidates", "research queue"],
    workspaceType: "theme",
    enabled: true,
    primaryNav: true,
    order: 20,
  },
  {
    id: "theme-supply-chain",
    title: "產業鏈 Supply Chain",
    shortTitle: "Supply",
    labelZh: "產業鏈",
    labelEn: "Supply Chain",
    description: "Dependency intelligence, supply-chain roles, constituents, and exposure mapping",
    iconKey: "network",
    railGroup: "top",
    target_tab: "theme-supply-chain",
    searchKeywords: ["supply chain", "supply-chain", "suppliers", "constituents", "beneficiaries", "theme map", "dependency"],
    workspaceType: "theme",
    enabled: true,
    primaryNav: true,
    order: 40,
  },
  {
    id: "stock-analysis",
    title: "股票研究 Stock",
    shortTitle: "Stock",
    labelZh: "股票研究",
    labelEn: "Stock",
    description: "Institutional single-company research memo for theme exposure, role evidence, and decision support",
    iconKey: "bar-chart-3",
    railGroup: "middle",
    target_tab: "stock-analysis",
    searchKeywords: ["stock", "stock analysis", "ticker", "equity", "quote", "chart"],
    workspaceType: "stock",
    enabled: true,
    primaryNav: true,
    order: 50,
  },
  {
    id: "alpha-quant",
    title: "篩選器 Screener",
    shortTitle: "Screener",
    labelZh: "篩選器",
    labelEn: "Screener",
    description: "Institutional discovery, alpha ranking, factor scores, and quant recommendations",
    iconKey: "scan-search",
    railGroup: "middle",
    target_tab: "alpha-quant",
    searchKeywords: ["screener", "screening", "alpha", "alpha quant", "ranking", "rankings", "top alpha", "factors"],
    workspaceType: "alpha",
    enabled: true,
    primaryNav: false,
    order: 50,
  },
  {
    id: "portfolio",
    title: "觀察清單 Watchlist",
    shortTitle: "Watchlist",
    labelZh: "觀察清單",
    labelEn: "Watchlist",
    description: "Institutional watchlist and portfolio workspace",
    iconKey: "panels-top-left",
    railGroup: "bottom",
    target_tab: "portfolio",
    searchKeywords: ["workspace", "portfolio", "watchlist", "holdings", "positions"],
    workspaceType: "portfolio",
    enabled: true,
    primaryNav: false,
    order: 60,
  },
  {
    id: "theme-risk",
    title: "風險 Alerts",
    shortTitle: "Alerts",
    labelZh: "風險",
    labelEn: "Alerts",
    description: "Contextual risk overlay retained for routing compatibility",
    iconKey: "shield-alert",
    railGroup: "bottom",
    target_tab: "theme-risk",
    searchKeywords: ["risk", "risk overlay", "bubble", "crowding", "overheating", "drawdown", "defensive", "participation"],
    workspaceType: "general",
    enabled: true,
    primaryNav: false,
    order: 70,
  },
  {
    id: "theme-forecast",
    title: "主題預測 Forecast",
    shortTitle: "Forecast",
    labelZh: "主題預測",
    labelEn: "Forecast",
    description: "Forward theme leadership forecasts, drivers, horizons, and validation diagnostics",
    iconKey: "brain-circuit",
    railGroup: "top",
    target_tab: "theme-forecast",
    searchKeywords: ["forecast", "theme forecast", "future themes", "theme ai", "regime forecast"],
    workspaceType: "theme",
    enabled: true,
    primaryNav: false,
    order: 80,
  },
  {
    id: "theme-stocks",
    title: "受益者 Beneficiaries",
    shortTitle: "Beneficiaries",
    labelZh: "受益者",
    labelEn: "Beneficiaries",
    description: "Theme beneficiary stocks, chart handoff, smart money, bubble, earnings, and theme exposure context",
    iconKey: "bar-chart-3",
    railGroup: "top",
    target_tab: "theme-stocks",
    searchKeywords: ["stocks", "beneficiary stocks", "stock analysis", "theme stocks", "chart", "earnings", "bubble", "smart money"],
    workspaceType: "theme",
    enabled: true,
    primaryNav: false,
    order: 90,
  },
];

export const enabledTerminalModules = terminalModules.filter((module) => module.enabled).sort((left, right) => left.order - right.order);
export const primaryTerminalModules = enabledTerminalModules.filter((module) => module.primaryNav !== false);

export function getTerminalModule(id: OmniboxTargetTab | string | undefined): TerminalModule | undefined {
  return terminalModules.find((module) => module.id === id);
}

export function getEnabledTerminalModule(id: OmniboxTargetTab | string | undefined): TerminalModule | undefined {
  const terminalModule = getTerminalModule(id);
  return terminalModule?.enabled ? terminalModule : undefined;
}
