import type { SearchResult, WorkspaceAction } from "@/types/stock";

export type MarketEntityType = "stock" | "theme" | "sector" | "industry" | "supply_chain" | "etf" | "risk_overlay";

export interface EntityDockPayload {
  title: string;
  subtitle: string;
  subject?: string;
  value?: number | null;
  riskContext?: string;
}

export interface RelatedEntityRef {
  id: string;
  type: MarketEntityType;
  label: string;
}

export interface MarketEntity {
  id: string;
  type: MarketEntityType;
  label: string;
  subtitle: string;
  route: WorkspaceAction;
  dockPayload: EntityDockPayload;
  relatedEntities: RelatedEntityRef[];
}

const SUPPLY_TERMS = ["glass", "substrate", "abf", "supply", "supplier", "dependency", "equipment", "materials"];
const THEME_TERMS = ["hbm", "ai infrastructure", "nand", "memory cycle", "nuclear energy", "electric grid"];
const SECTOR_TERMS = ["semiconductor", "technology", "energy", "financial", "healthcare", "industrial", "utilities", "materials"];
const INDUSTRY_TERMS = ["foundry", "memory", "equipment", "software", "shipping", "defense"];
const RISK_TERMS = ["risk", "bubble", "crowding", "overheating", "volatility", "distribution", "drawdown"];
const ETF_TERMS = ["SMH", "SOXX", "SPY", "QQQ", "DIA", "IWM", "XLK", "XLE", "XLF", "XLV", "XLI", "XLU"];

function compact(value?: string | null): string {
  return value?.trim().replace(/\s+/g, " ") ?? "";
}

function slug(value: string): string {
  return value.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function includesTerm(query: string, terms: string[]): boolean {
  const normalized = query.toLowerCase();
  return terms.some((term) => normalized.includes(term));
}

export function classifyEntityQuery(query: string): MarketEntityType {
  const normalized = compact(query);
  const upper = normalized.toUpperCase();
  if (includesTerm(normalized, RISK_TERMS)) return "risk_overlay";
  if (ETF_TERMS.includes(upper)) return "etf";
  if (includesTerm(normalized, SUPPLY_TERMS)) return "supply_chain";
  if (includesTerm(normalized, THEME_TERMS)) return "theme";
  if (includesTerm(normalized, SECTOR_TERMS)) return "sector";
  if (includesTerm(normalized, INDUSTRY_TERMS)) return "industry";
  if (/^[A-Z][A-Z0-9.-]{0,5}$/.test(upper)) return "stock";
  return "theme";
}

export function entityCategoryLabel(type: MarketEntityType): { zh: string; en: string } {
  if (type === "stock") return { zh: "股票", en: "Stock" };
  if (type === "theme") return { zh: "主題", en: "Theme" };
  if (type === "sector") return { zh: "板塊", en: "Sector" };
  if (type === "industry") return { zh: "產業", en: "Industry" };
  if (type === "supply_chain") return { zh: "供應鏈", en: "Supply Chain" };
  if (type === "etf") return { zh: "ETF", en: "ETF" };
  return { zh: "風險疊加", en: "Risk Overlay" };
}

export function routeForEntity(entity: Pick<MarketEntity, "type" | "label" | "id" | "dockPayload">): WorkspaceAction {
  if (entity.type === "stock") {
    return { actionType: "open_stock", target_tab: "stock-analysis", focusTarget: "stock-workspace", openMode: "replace", contextPayload: { ticker: entity.id, label: `Open ${entity.id} Analysis` } };
  }
  if (entity.type === "theme") {
    return { actionType: "open_theme", target_tab: "theme-intelligence", focusTarget: "theme-detail", openMode: "replace", contextPayload: { theme: entity.label, themeView: "command", label: `Open ${entity.label}` } };
  }
  if (entity.type === "supply_chain") {
    return { actionType: "open_module", target_tab: "theme-supply-chain", focusTarget: "theme-supply-chain", openMode: "replace", contextPayload: { theme: entity.label, themeView: "supply-chain", label: `${entity.label} Supply Chain` } };
  }
  if (entity.type === "sector" || entity.type === "industry" || entity.type === "etf") {
    return { actionType: "open_sector", target_tab: "market-intel", focusTarget: "theme-rotation", openMode: "replace", contextPayload: { sector: entity.label, themeView: "rotation", label: `${entity.label} Rotation` } };
  }
  const subject = compact(entity.dockPayload.subject);
  const ticker = subject && /^[A-Z][A-Z0-9.-]{0,5}$/.test(subject.toUpperCase()) ? subject.toUpperCase() : "";
  return ticker
    ? { actionType: "open_stock", target_tab: "stock-analysis", focusTarget: "stock-workspace", openMode: "replace", contextPayload: { ticker, label: `${ticker} Risk Context` } }
    : { actionType: "open_theme", target_tab: "theme-intelligence", focusTarget: "theme-detail", openMode: "replace", contextPayload: { theme: subject || entity.label, themeView: "command", label: `${entity.label} Overlay` } };
}

export function createMarketEntity(input: {
  id?: string;
  type: MarketEntityType;
  label: string;
  subtitle?: string;
  subject?: string;
  value?: number | null;
  relatedEntities?: RelatedEntityRef[];
}): MarketEntity {
  const label = compact(input.label) || "Context";
  const id = compact(input.id) || slug(label);
  const category = entityCategoryLabel(input.type);
  const dockPayload: EntityDockPayload = {
    title: label,
    subtitle: input.subtitle || `${category.zh} ${category.en}`,
    subject: compact(input.subject) || undefined,
    value: input.value,
    riskContext: input.type === "risk_overlay" ? label : undefined,
  };
  const base = { id, type: input.type, label, subtitle: dockPayload.subtitle, dockPayload, relatedEntities: input.relatedEntities ?? [] };
  return { ...base, route: routeForEntity(base) };
}

export function entityFromSearchResult(result: SearchResult): MarketEntity {
  const title = compact(result.label ?? result.theme ?? result.sector ?? result.company ?? result.name ?? result.symbol);
  const declared = compact(result.type).toLowerCase().replace(/[\s-]+/g, "_");
  const type: MarketEntityType =
    declared === "equity" || declared === "stock" ? "stock"
      : declared === "theme" ? "theme"
        : declared === "sector" ? "sector"
          : declared === "industry" ? "industry"
            : declared === "supply_chain" ? "supply_chain"
              : declared === "etf" ? "etf"
                : declared === "risk" || declared === "risk_overlay" ? "risk_overlay"
                  : classifyEntityQuery(`${result.symbol} ${title}`);
  const id = type === "stock" || type === "etf" ? compact(result.ticker ?? result.symbol).toUpperCase() : result.id ?? slug(title);
  return createMarketEntity({ id, type, label: title, subtitle: result.description ?? `${result.exchange} · ${result.type}`, subject: result.ticker ?? result.symbol, value: result.change_percent });
}
