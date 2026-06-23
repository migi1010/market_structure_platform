import type { OmniboxTargetTab, WorkspaceAction } from "@/types/stock";

export type ResearchOsWorkspace = "rotation" | "scout" | "theme" | "supply-chain" | "stock";
export type NavigationEntityKind = "theme" | "sector" | "company" | "supply-chain-node" | "scout-candidate";

export interface NavigationEntityContext {
  theme?: string;
  ticker?: string;
  sector?: string;
  supplyChainNode?: string;
  candidate?: string;
}

export function buildResearchOsNavigationContract() {
  return {
    workspaceOrder: ["rotation", "scout", "theme", "supply-chain", "stock"] as ResearchOsWorkspace[],
    questionByWorkspace: {
      rotation: "Where is capital moving?",
      scout: "What deserves research?",
      theme: "Why does this theme matter?",
      "supply-chain": "How does this industry work?",
      stock: "Which company benefits?",
    },
  };
}

export function workspaceForNavigationTarget(target: OmniboxTargetTab): ResearchOsWorkspace {
  if (target === "market-intel") return "rotation";
  if (target === "theme-scout") return "scout";
  if (target === "theme-supply-chain") return "supply-chain";
  if (target === "stock-analysis") return "stock";
  return "theme";
}

export function navigationActionForEntity(kind: NavigationEntityKind, context: NavigationEntityContext): WorkspaceAction {
  if (kind === "company") {
    const ticker = context.ticker?.trim().toUpperCase() || "";
    return {
      actionType: "open_stock",
      target_tab: "stock-analysis",
      focusTarget: "stock-workspace",
      openMode: "replace",
      contextPayload: {
        ticker,
        theme: context.theme,
        label: ticker ? `Open ${ticker} Research` : "Open Stock Research",
      },
    };
  }

  if (kind === "supply-chain-node") {
    return {
      actionType: "open_theme",
      target_tab: "theme-supply-chain",
      focusTarget: "theme-supply-chain",
      openMode: "replace",
      contextPayload: {
        theme: context.theme,
        themeView: "supply-chain",
        label: context.supplyChainNode ?? "Open Supply Chain",
      },
    };
  }

  if (kind === "sector") {
    return {
      actionType: "open_theme",
      target_tab: context.theme ? "theme-intelligence" : "market-intel",
      focusTarget: context.theme ? "theme-detail" : "theme-rotation",
      openMode: "replace",
      contextPayload: {
        theme: context.theme,
        sector: context.sector,
        themeView: context.theme ? "command" : "rotation",
        label: context.theme ?? context.sector ?? "Open Rotation",
      },
    };
  }

  return {
    actionType: "open_theme",
    target_tab: "theme-intelligence",
    focusTarget: "theme-detail",
    openMode: "replace",
    contextPayload: {
      theme: context.theme ?? context.candidate,
      themeView: "command",
      label: context.theme ?? context.candidate ?? "Open Theme",
    },
  };
}
