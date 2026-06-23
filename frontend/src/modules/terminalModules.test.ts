import { enabledTerminalModules, primaryTerminalModules } from "./terminalModules";

export function terminalModuleContractTest() {
  const primaryLabels = primaryTerminalModules.map((item) => item.labelEn);
  const visibleLabels = enabledTerminalModules.map((item) => `${item.labelZh} ${item.labelEn}`);
  const enabledIds = enabledTerminalModules.map((item) => String(item.id));
  const expectedLabels = {
    "market-intel": ["資金輪動", "Rotation"],
    "theme-intelligence": ["主題研究", "Themes"],
    "theme-scout": ["主題偵察", "Scout"],
    "theme-supply-chain": ["產業鏈", "Supply Chain"],
    "stock-analysis": ["股票研究", "Stock"],
    "alpha-quant": ["篩選器", "Screener"],
    portfolio: ["觀察清單", "Watchlist"],
    "theme-risk": ["風險", "Alerts"],
    "theme-forecast": ["主題預測", "Forecast"],
    "theme-stocks": ["受益者", "Beneficiaries"],
  };
  const expectedLabelsMatch = Object.entries(expectedLabels).every(([id, [labelZh, labelEn]]) => {
    const terminalModule = enabledTerminalModules.find((item) => item.id === id);
    return terminalModule?.labelZh === labelZh && terminalModule.labelEn === labelEn;
  });
  const replacementCharacter = String.fromCharCode(0xfffd);
  const noMojibake = visibleLabels.every((label) => !label.includes("?") && !label.includes(replacementCharacter));

  return {
    primaryLabels,
    visibleLabels,
    finalPrimaryNavigation:
      primaryLabels.join(">") === "Rotation>Scout>Themes>Supply Chain>Stock",
    pipelineRemoved:
      !primaryLabels.includes("Pipeline")
      && !enabledIds.includes("research-pipeline"),
    decisionIntelligenceRemoved:
      !primaryLabels.includes("Decision Intelligence")
      && !enabledIds.includes("decision-intelligence"),
    expectedLabelsMatch,
    noMojibake,
    rotationIsPrimary: primaryLabels.includes("Rotation"),
    riskIsContextual: !primaryLabels.includes("Risk") && !primaryLabels.includes("Alerts"),
    forecastRoutingPreserved: enabledIds.includes("theme-forecast"),
    themeStocksRoutingPreserved: enabledIds.includes("theme-stocks"),
    riskRoutingPreserved: enabledIds.includes("theme-risk"),
    scoutRoutingPreserved: enabledIds.includes("theme-scout"),
    scoutBetweenThemesAndSupply:
      primaryLabels.indexOf("Scout") > primaryLabels.indexOf("Rotation")
      && primaryLabels.indexOf("Scout") < primaryLabels.indexOf("Themes"),
  };
}
