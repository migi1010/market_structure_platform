import { createDockState, createDrilldownAction, isSupplyQuery, type DrilldownTarget } from "./drilldown";

export function drilldownContractTest() {
  const stock: DrilldownTarget = { kind: "stock", symbol: "NVDA", label: "NVDA" };
  const theme: DrilldownTarget = { kind: "theme", name: "HBM" };
  const sector: DrilldownTarget = {
    kind: "sector",
    name: "Energy",
    intelligence: {
      summary: "Leading rotation",
      flow: 78,
      risk: 32,
      exposure: ["Nuclear", "Grid"],
      beneficiaries: ["CEG", "VST"],
      relatedThemes: ["Power Demand"],
    },
  };
  const supply: DrilldownTarget = { kind: "supply", name: "Glass Substrate" };
  const risk: DrilldownTarget = { kind: "risk", name: "Bubble Risk", subject: "NVDA" };
  const etf: DrilldownTarget = { kind: "etf", symbol: "SMH" };

  return {
    stock: createDrilldownAction(stock).action.target_tab,
    theme: createDrilldownAction(theme).action.contextPayload?.theme,
    sector: createDrilldownAction(sector).action.target_tab,
    supplyDock: createDrilldownAction(supply).dock?.kind,
    riskDock: createDrilldownAction(risk).dock?.kind,
    etfDock: createDrilldownAction(etf).dock?.kind,
    singleClickDock: createDockState(sector).kind,
    intelligence: createDockState(sector).intelligence,
    riskIsOverlay: createDrilldownAction(risk).action.target_tab !== "theme-risk",
    supplyQuery: isSupplyQuery("Glass"),
  };
}
