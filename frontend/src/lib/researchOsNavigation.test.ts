import {
  buildResearchOsNavigationContract,
  navigationActionForEntity,
  workspaceForNavigationTarget,
} from "./researchOsNavigation";

export function researchOsNavigationContractTest() {
  const contract = buildResearchOsNavigationContract();

  return {
    workspaceOrderIsFinalResearchOs:
      contract.workspaceOrder.join(">")
      === "rotation>scout>theme>supply-chain>stock",
    themeToSupplyPreservesTheme:
      navigationActionForEntity("theme", { theme: "ai_infrastructure" }).contextPayload?.theme
      === "ai_infrastructure",
    supplyToStockPreservesThemeAndTicker:
      navigationActionForEntity("company", { theme: "ai_infrastructure", ticker: "NVDA" }).contextPayload?.theme
      === "ai_infrastructure"
      && navigationActionForEntity("company", { theme: "ai_infrastructure", ticker: "NVDA" }).contextPayload?.ticker === "NVDA",
    scoutThemeOpensThemeWorkspace:
      navigationActionForEntity("scout-candidate", { theme: "ai_infrastructure" }).target_tab
      === "theme-intelligence",
    rotationThemeOpensThemeWorkspace:
      navigationActionForEntity("sector", { sector: "Technology", theme: "hbm" }).target_tab
      === "theme-intelligence",
    stockTargetMapsToStockWorkspace:
      workspaceForNavigationTarget("stock-analysis") === "stock",
  };
}
