import type { DrilldownTarget } from "./drilldown";
import { safeArray, uniqueBy } from "./payloadSafety";
import type { SectorCompany, SectorRotation, ThemeDetailResponse, ThemeLeader, ThemeScore } from "@/types/stock";

export interface BeneficiaryRole {
  role: string;
  leaders: ThemeLeader[];
}

interface ResolveActiveBeneficiariesInput {
  target: DrilldownTarget | null;
  currentTheme: string;
  themes: Array<Partial<ThemeScore> & { theme: string }>;
  detail: ThemeDetailResponse | null;
  sectors: SectorRotation[];
  roles: BeneficiaryRole[];
  flowEndpoints?: Record<string, string[]>;
}

export interface ActiveBeneficiaryResult {
  label: string;
  rows: ThemeLeader[];
}

function same(left?: string | null, right?: string | null): boolean {
  return Boolean(left && right && left.trim().toLowerCase() === right.trim().toLowerCase());
}

function uniqueRows(rows: ThemeLeader[]): ThemeLeader[] {
  return uniqueBy(rows, (row) => row?.ticker?.trim().toUpperCase());
}

function themeRows(theme: Partial<ThemeScore> | undefined): ThemeLeader[] {
  if (!theme) return [];
  return uniqueRows([...safeArray(theme.top_alpha_stocks), ...safeArray(theme.related_stocks), ...safeArray(theme.leaders)]);
}

function detailRows(detail: ThemeDetailResponse | null, label: string): ThemeLeader[] {
  if (!detail || !same(detail.theme, label)) return [];
  return uniqueRows([...safeArray(detail.top_alpha_stocks), ...safeArray(detail.related_stocks)]);
}

function sectorCompanyRow(company: SectorCompany): ThemeLeader {
  return {
    ticker: company.ticker,
    company_name: company.company_name,
    market_cap: company.market_cap ?? undefined,
    alpha_score: company.alpha_score,
    bubble_risk: company.bubble_score,
    momentum_3m: company.relative_strength ?? undefined,
    change_percent: company.change_percent ?? undefined,
  };
}

function fallbackRows(target: DrilldownTarget): ThemeLeader[] {
  return tickerRows(target.intelligence?.beneficiaries);
}

function tickerRows(tickers: string[] | undefined): ThemeLeader[] {
  return uniqueRows((tickers ?? []).map((ticker) => ({ ticker, company_name: ticker })));
}

function firstRows(...sources: ThemeLeader[][]): ThemeLeader[] {
  return sources.find((rows) => rows.length > 0) ?? [];
}

function relatedThemeRows(target: DrilldownTarget, themes: Array<Partial<ThemeScore> & { theme: string }>): ThemeLeader[] {
  return uniqueRows(safeArray(target.intelligence?.relatedThemes).flatMap((label) => themeRows(safeArray(themes).find((theme) => same(theme.theme, label)))));
}

function roleRows(roles: BeneficiaryRole[], label?: string | null): ThemeLeader[] {
  const matched = label ? safeArray(roles).filter((row) => same(row?.role, label)) : safeArray(roles);
  return uniqueRows(matched.flatMap((row) => safeArray(row?.leaders)));
}

function supplyChainRows(detail: ThemeDetailResponse | null): ThemeLeader[] {
  if (!detail?.supply_chain || typeof detail.supply_chain !== "object") return [];
  return uniqueRows(Object.values(detail.supply_chain).flatMap((rows) => safeArray(rows)));
}

export function resolveActiveBeneficiaries({
  target,
  currentTheme,
  themes,
  detail,
  sectors,
  roles,
  flowEndpoints = {},
}: ResolveActiveBeneficiariesInput): ActiveBeneficiaryResult {
  const safeThemes = safeArray(themes);
  const safeSectors = safeArray(sectors);
  const safeRoles = safeArray(roles);
  const defaultTheme = safeThemes.find((theme) => same(theme.theme, currentTheme));
  const explicit = target ? fallbackRows(target) : [];
  if (!target) {
    const rows = detailRows(detail, currentTheme);
    return { label: currentTheme, rows: rows.length > 0 ? rows : themeRows(defaultTheme) };
  }

  if (target.kind === "sector") {
    const label = target.name ?? target.label ?? currentTheme;
    const sector = safeSectors.find((row) => same(row.sector, label));
    const rows = uniqueRows(safeArray(sector?.companies).map(sectorCompanyRow));
    const matchingTheme = safeThemes.find((theme) => same(theme.theme, label));
    return { label, rows: firstRows(explicit, rows, themeRows(matchingTheme), roleRows(safeRoles, label), tickerRows(flowEndpoints[label]), relatedThemeRows(target, safeThemes)) };
  }

  if (target.kind === "supply" || target.kind === "supply_chain") {
    const label = target.subject ?? target.name ?? target.label ?? currentTheme;
    const constituents = uniqueRows(safeArray(detail?.supply_chain?.[label]));
    const selectedTheme = safeThemes.find((theme) => same(theme.theme, target.name));
    return { label, rows: firstRows(explicit, themeRows(selectedTheme), roleRows(safeRoles, label), constituents, tickerRows(flowEndpoints[label]), relatedThemeRows(target, safeThemes)) };
  }

  if (target.kind === "theme") {
    const subjectTheme = safeThemes.find((theme) => same(theme.theme, target.subject));
    const namedTheme = safeThemes.find((theme) => same(theme.theme, target.name ?? target.label));
    const selectedTheme = subjectTheme ?? namedTheme;
    const label = selectedTheme?.theme ?? target.name ?? target.label ?? target.subject ?? currentTheme;
    const rows = detailRows(detail, label);
    const resolved = rows.length > 0 ? rows : themeRows(selectedTheme);
    const sector = safeSectors.find((row) => same(row.sector, label));
    const sectorRows = uniqueRows(safeArray(sector?.companies).map(sectorCompanyRow));
    return { label, rows: firstRows(explicit, resolved, sectorRows, roleRows(safeRoles, label), supplyChainRows(detail), tickerRows(flowEndpoints[label]), relatedThemeRows(target, safeThemes)) };
  }

  return { label: target.label ?? target.name ?? target.symbol ?? target.subject ?? "Selected context", rows: explicit };
}
