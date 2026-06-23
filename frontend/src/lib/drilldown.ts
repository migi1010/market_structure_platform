import { createMarketEntity, entityFromSearchResult, type MarketEntity, type MarketEntityType } from "./entities";
import type { SearchResult, WorkspaceAction } from "@/types/stock";

export type DrilldownKind = "stock" | "theme" | "sector" | "industry" | "supply" | "supply_chain" | "risk" | "risk_overlay" | "etf";

export interface DrilldownTarget {
  kind: DrilldownKind;
  name?: string;
  symbol?: string;
  label?: string;
  subject?: string;
  value?: number | null;
  meta?: string;
  intelligence?: DockIntelligence;
}

export interface DockIntelligence {
  summary?: string;
  flow?: number | null;
  risk?: number | null;
  exposure?: string[];
  beneficiaries?: string[];
  relatedThemes?: string[];
}

export interface DrilldownDockState {
  kind: MarketEntityType;
  title: string;
  subtitle?: string;
  subject?: string;
  value?: number | null;
  target: DrilldownTarget;
  entity: MarketEntity;
  intelligence?: DockIntelligence;
}

export interface DrilldownResult {
  action: WorkspaceAction;
  dock?: DrilldownDockState;
}

const SUPPLY_TERMS = ["glass", "substrate", "abf", "supply", "supplier", "dependency", "equipment", "materials"];
const RISK_TERMS = ["risk", "bubble", "crowding", "overheating", "volatility", "distribution", "drawdown"];
const ETF_TERMS = ["ETF", "SMH", "SOXX", "SPY", "QQQ", "DIA", "IWM", "XLK", "XLE", "XLF", "XLV", "XLI", "XLU"];

function compact(value: string | undefined | null): string {
  return value?.trim().replace(/\s+/g, " ") ?? "";
}

function upper(value: string | undefined | null): string {
  return compact(value).toUpperCase();
}

function labelFor(target: DrilldownTarget): string {
  return compact(target.label) || compact(target.name) || upper(target.symbol) || "Context";
}

function entityTypeFor(kind: DrilldownKind): MarketEntityType {
  if (kind === "supply") return "supply_chain";
  if (kind === "risk") return "risk_overlay";
  return kind;
}

function entityFor(target: DrilldownTarget): MarketEntity {
  return createMarketEntity({
    id: target.symbol,
    type: entityTypeFor(target.kind),
    label: labelFor(target),
    subtitle: target.meta,
    subject: target.subject,
    value: target.value,
  });
}

function dockFor(target: DrilldownTarget, title = labelFor(target)): DrilldownDockState {
  const entity = entityFor(target);
  return {
    kind: entity.type,
    title,
    subtitle: entity.subtitle,
    subject: target.subject,
    value: target.value,
    target,
    entity,
    intelligence: target.intelligence,
  };
}

export function createDockState(target: DrilldownTarget): DrilldownDockState {
  return dockFor(target);
}

export function isSupplyQuery(query: string): boolean {
  const normalized = query.toLowerCase();
  return SUPPLY_TERMS.some((term) => normalized.includes(term));
}

export function isRiskQuery(query: string): boolean {
  const normalized = query.toLowerCase();
  return RISK_TERMS.some((term) => normalized.includes(term));
}

export function isEtfQuery(query: string): boolean {
  const normalized = upper(query);
  return ETF_TERMS.some((term) => normalized === term || normalized.includes(`${term} `));
}

export function inferDrilldownTargetFromSearch(result: SearchResult): DrilldownTarget {
  const entity = entityFromSearchResult(result);
  const kind: DrilldownKind = entity.type === "supply_chain" ? "supply" : entity.type === "risk_overlay" ? "risk" : entity.type;
  const subject = entity.type === "theme" ? entity.label : entity.dockPayload.subject;
  return { kind, symbol: entity.type === "stock" || entity.type === "etf" ? entity.id : undefined, name: entity.label, label: entity.label, subject, value: entity.dockPayload.value, meta: entity.subtitle };
}

export function createDrilldownAction(target: DrilldownTarget): DrilldownResult {
  const entity = entityFor(target);
  return { action: entity.route, dock: dockFor(target, entity.dockPayload.title) };
}
