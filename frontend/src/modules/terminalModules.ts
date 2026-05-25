import type { OmniboxTargetTab } from "@/types/stock";

export type TerminalModuleId = OmniboxTargetTab;
export type TerminalWorkspaceType = "stock" | "theme" | "sector" | "portfolio" | "alpha" | "general";
export type TerminalIconKey = "radar" | "briefcase" | "brain" | "line-chart";

export interface TerminalModule {
  id: TerminalModuleId;
  title: string;
  shortTitle: string;
  description: string;
  iconKey: TerminalIconKey;
  target_tab: OmniboxTargetTab;
  searchKeywords: string[];
  workspaceType: TerminalWorkspaceType;
  enabled: boolean;
  order: number;
}

export const terminalModules: TerminalModule[] = [
  {
    id: "theme-intelligence",
    title: "Theme Intelligence",
    shortTitle: "Themes",
    description: "Macro themes, supply chains, and capital-flow intelligence",
    iconKey: "radar",
    target_tab: "theme-intelligence",
    searchKeywords: ["theme", "themes", "theme intelligence", "macro themes", "ai themes"],
    workspaceType: "theme",
    enabled: true,
    order: 10,
  },
  {
    id: "portfolio",
    title: "Portfolio",
    shortTitle: "Portfolio",
    description: "Institutional watchlist and portfolio command center",
    iconKey: "briefcase",
    target_tab: "portfolio",
    searchKeywords: ["portfolio", "watchlist", "holdings", "positions"],
    workspaceType: "portfolio",
    enabled: true,
    order: 20,
  },
  {
    id: "alpha-quant",
    title: "Alpha Quant",
    shortTitle: "Alpha",
    description: "Alpha ranking, factor scores, and quant recommendations",
    iconKey: "brain",
    target_tab: "alpha-quant",
    searchKeywords: ["alpha", "alpha quant", "ranking", "rankings", "top alpha", "factors"],
    workspaceType: "alpha",
    enabled: true,
    order: 30,
  },
  {
    id: "market-intel",
    title: "Sector Rotation",
    shortTitle: "Sectors",
    description: "Sector leadership, rotation, and relative strength analytics",
    iconKey: "radar",
    target_tab: "market-intel",
    searchKeywords: ["sector", "sectors", "sector rotation", "market intel", "relative strength"],
    workspaceType: "sector",
    enabled: true,
    order: 40,
  },
  {
    id: "stock-analysis",
    title: "Stock Analysis",
    shortTitle: "Stock",
    description: "Single-stock intelligence workspace with quote, valuation, and regime context",
    iconKey: "line-chart",
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
