import { resolveActiveBeneficiaries } from "./beneficiaries";
import type { DrilldownTarget } from "./drilldown";
import type { SectorRotation, ThemeDetailResponse, ThemeLeader, ThemeScore } from "@/types/stock";

const leader = (ticker: string, role?: string): ThemeLeader => ({ ticker, company_name: ticker, role });

const themes = [
  { theme: "HBM", leaders: [leader("MU"), leader("WDC")] },
  { theme: "Networking", leaders: [leader("ANET"), leader("MRVL")] },
] as ThemeScore[];

const detail = {
  theme: "HBM",
  related_stocks: [leader("MU")],
  top_alpha_stocks: [leader("WDC")],
  supply_chain: {},
} as ThemeDetailResponse;

const sectors = [
  {
    sector: "Energy",
    companies: [{ ticker: "XOM", company_name: "Exxon Mobil", alpha_score: 72 }],
  },
] as SectorRotation[];

const roles = [
  { role: "Materials", leaders: [leader("GLW", "Materials"), leader("APH", "Materials")] },
  { role: "Networking", leaders: [leader("ANET", "Networking")] },
];

function target(target: DrilldownTarget | null) {
  return resolveActiveBeneficiaries({ target, currentTheme: "HBM", themes, detail, sectors, roles, flowEndpoints: { Upstream: ["TSM", "ASML", "AMAT"] } });
}

function assertTickers(actual: ThemeLeader[], expected: string[]): void {
  const tickers = actual.map((row) => row.ticker);
  if (tickers.join(",") !== expected.join(",")) throw new Error(`Expected ${expected.join(",")} but received ${tickers.join(",")}`);
}

export function beneficiaryResolverContractTest() {
  const theme = target({ kind: "theme", name: "HBM" });
  const sector = target({ kind: "sector", name: "Energy" });
  const supply = target({ kind: "supply", name: "HBM", subject: "Materials" });
  const unsupported = target({ kind: "risk", name: "Bubble Risk" });
  const changed = target({ kind: "sector", name: "Utilities" });
  const unavailableTheme = resolveActiveBeneficiaries({ target: { kind: "theme", name: "HBM", subject: "THEME:HBM" }, currentTheme: "AI Infrastructure", themes: [], detail: null, sectors, roles });
  const endpoint = target({ kind: "supply", name: "Unknown", subject: "Upstream" });
  const explicit = target({ kind: "supply", name: "HBM", subject: "Materials", intelligence: { beneficiaries: ["EXPLICIT"] } });
  const unsupportedExplicit = target({ kind: "risk", name: "Bubble Risk", intelligence: { beneficiaries: ["NVDA"] } });
  const themeSupplyFallback = resolveActiveBeneficiaries({
    target: { kind: "theme", name: "Unknown Theme" },
    currentTheme: "Unknown Theme",
    themes: [],
    detail: { ...detail, theme: "Unknown Theme", related_stocks: [], top_alpha_stocks: [], supply_chain: { Materials: [leader("GLW")] } },
    sectors: [],
    roles: [],
  });
  const sectorRelatedThemeFallback = resolveActiveBeneficiaries({
    target: { kind: "sector", name: "Communication Services", intelligence: { relatedThemes: ["Networking"] } },
    currentTheme: "HBM",
    themes,
    detail,
    sectors: [],
    roles,
  });

  assertTickers(theme.rows, ["WDC", "MU"]);
  assertTickers(sector.rows, ["XOM"]);
  assertTickers(supply.rows, ["GLW", "APH"]);
  assertTickers(unsupported.rows, []);
  assertTickers(changed.rows, []);
  assertTickers(endpoint.rows, ["TSM", "ASML", "AMAT"]);
  assertTickers(explicit.rows, ["EXPLICIT"]);
  assertTickers(unsupportedExplicit.rows, ["NVDA"]);
  assertTickers(themeSupplyFallback.rows, ["GLW"]);
  assertTickers(sectorRelatedThemeFallback.rows, ["ANET", "MRVL"]);
  if (changed.label !== "Utilities") throw new Error("Changing selection must use the new empty-state label.");
  if (unavailableTheme.label !== "HBM") throw new Error("Unavailable themes must use the user-facing label.");
  return true;
}
