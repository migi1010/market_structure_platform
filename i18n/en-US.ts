export const enUS = {
  navigation: {
    dashboard: "Dashboard",
    themeIntelligence: "Theme Intelligence",
    quantAnalytics: "Quant Analytics",
    marketStructure: "Market Structure",
    portfolio: "Portfolio",
    settings: "Settings",
  },
  labels: {
    alphaScore: "Alpha Score",
    bubbleRisk: "Bubble Risk",
    smartMoney: "Smart Money",
    earningsQuality: "Earnings Quality",
    sectorRotation: "Sector Rotation",
    capitalFlow: "Capital Flow",
    institutionalConsensus: "Institutional Consensus",
    confidence: "Confidence",
    partialData: "Partial Data",
  },
  tooltips: {
    bubbleRisk: "Measures valuation excess, cash-flow deterioration, dilution, volatility acceleration, and speculation intensity.",
    alphaScore: "Ranks securities using momentum, earnings quality, smart money, sector strength, theme alignment, valuation, cash flow, volatility, balance sheet quality, and regime alignment.",
    smartMoney: "Detects institutional accumulation through volume structure, VWAP-style support proxies, relative strength, liquidity quality, and volatility compression.",
    earningsQuality: "Evaluates cash conversion, accrual quality, SBC dilution, debt quality, capex efficiency, and operating cash-flow durability.",
    themeScore: "Measures capital-flow acceleration, breadth expansion, relative strength, supply-chain confirmation, ETF proxy strength, narrative acceleration, and macro alignment.",
  },
} as const;
