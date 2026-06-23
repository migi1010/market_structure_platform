"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, Boxes, LineChart, ShieldAlert, Target, Workflow } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { resolveActiveBeneficiaries } from "@/lib/beneficiaries";
import { useHydratedTime } from "@/lib/hydration";
import { safeArray } from "@/lib/payloadSafety";
import { deriveSupplyChainIntelligence, type SupplyStageView } from "@/lib/supplyChainIntelligence";
import type { DrilldownTarget } from "@/lib/drilldown";
import { buildRotationWorkspace, capitalFlowWeight } from "@/lib/rotationWorkspace";
import {
  fetchSectorRotation,
  fetchThemeRanking,
  fetchThemeRegistry,
  fetchThemePortfolio,
  fetchThemeScores,
  normalizeThemeIntelligenceId,
  resolveCanonicalThemeSelection,
  traceThemeIdentity,
} from "@/services/stockApi";
import type {
  SectorRotation,
  RotationSnapshotResponse,
  ThemeAggregateResponse,
  ThemeBeneficiaryRecord,
  ThemeDiscoveryResponse,
  ThemeDetailResponse,
  ThemeForecastRecord,
  ThemeForecastValidationResponse,
  ThemeLeader,
  ThemeNarrativeResponse,
  ThemePortfolioResponse,
  ThemeScore,
  ThemeScoreRecord,
  ThemeRegistryEntry,
  ThemeRank,
  ThemeScoresResponse,
  ThemeSupplyChainResponse,
} from "@/types/stock";
import { findThemeRegistryEntry, sortThemeRegistryEntries } from "@/lib/themeRegistry";
import { rankingAwareThemeOrder } from "@/lib/themeRanking";
import { BeneficiaryMatrix, BilingualLabel, CapitalFlowSurface, ChangeCell, ConfidenceMeter, FlowIndicator, HeatStrip, MarketCell, MarketRow, MarketTable, MarketTreemap, NumericCell, SectorIcon, SparklineMini, StatusDot, TerminalPanel, ThemeIcon, TickerCell, TickerLogo, type BeneficiaryMatrixRow, type CapitalFlowLane, type MarketTreemapItem } from "./terminal";
import CapitalFlowStory from "./terminal/CapitalFlowStory";
import DynamicThemeRotationPanel from "./theme-workspace/DynamicThemeRotationPanel";
import IndustrialDependencyWorkflow from "./theme-workspace/IndustrialDependencyWorkflow";
import ThemeInvestmentWorkflow from "./theme-workspace/ThemeInvestmentWorkflow";

type ThemeResearchTab = "command" | "forecast" | "rotation" | "stocks" | "supply-chain" | "risk";

interface ThemeResearchPageProps {
  activeSelection?: DrilldownTarget | null;
  aggregateIntelligence?: ThemeAggregateResponse | null;
  onTickerSelect?: (ticker: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

interface ThemeDataState {
  themeScores: ThemeScoresResponse | null;
  themeDiscovery: ThemeDiscoveryResponse | null;
  themePortfolio: ThemePortfolioResponse | null;
  topThemes: ThemeScore[];
  emergingThemes: ThemeScore[];
  rotationMap: ThemeScore[];
  capitalFlow: Array<Partial<ThemeScore> & { theme: string; category: string }>;
  sectors: SectorRotation[];
  rotationSnapshot: RotationSnapshotResponse | null;
  narratives: ThemeNarrativeResponse | null;
  supplyChain: ThemeSupplyChainResponse | null;
  detail: ThemeDetailResponse | null;
  forecast: ThemeForecastRecord[];
  validation: ThemeForecastValidationResponse | null;
  loading: boolean;
}

const TAB_ALIASES: Record<string, ThemeResearchTab> = {
  command: "command",
  forecast: "forecast",
  rotation: "rotation",
  stocks: "stocks",
  "supply-chain": "supply-chain",
  risk: "risk",
};

const MODULE_VIEW: Record<string, ThemeResearchTab> = {
  "theme-intelligence": "command",
  "theme-forecast": "forecast",
  "market-intel": "rotation",
  "theme-stocks": "stocks",
  "theme-supply-chain": "supply-chain",
  "theme-risk": "risk",
};

const THEME_TABLE_COLUMNS = "minmax(0,1fr) 58px 58px 48px";
const SECTOR_TABLE_COLUMNS = "minmax(0,1fr) 58px 58px 58px 96px";
const BENEFICIARY_TABLE_COLUMNS = "72px minmax(0,1fr) 74px 58px";
const SUPPLY_CHAIN_TABLE_COLUMNS = "150px minmax(0,1fr) 74px";
const RISK_TABLE_COLUMNS = "140px 74px minmax(0,1fr)";

const VIEW_COPY: Record<ThemeResearchTab, { eyebrow: string; title: string; description: string; icon: typeof Target }> = {
  command: {
    eyebrow: "? Command",
    title: "?銝剖? Command Center",
    description: "Theme tape, flow, forecast, beneficiaries.",
    icon: Target,
  },
  forecast: {
    eyebrow: "?葫 Forecast",
    title: "銝駁??葫 Theme Forecast",
    description: "Leadership forecast, confidence, risk state.",
    icon: LineChart,
  },
  rotation: {
    eyebrow: "輪動 Rotation",
    title: "輪動 Rotation",
    description: "Sector flow, market diagnostics, and ranked themes.",
    icon: Workflow,
  },
  stocks: {
    eyebrow: "? Stocks",
    title: "??? Stock Drilldown",
    description: "Beneficiary stocks and quick handoff.",
    icon: BarChart3,
  },
  "supply-chain": {
    eyebrow: "靘???Supply Chain",
    title: "靘???Supply Chain",
    description: "Roles, constituents, dependency path.",
    icon: Boxes,
  },
  risk: {
    eyebrow: "憸券 Risk",
    title: "憸券?? Risk Monitor",
    description: "Crowding, heat, downside state.",
    icon: ShieldAlert,
  },
};
const EMPTY_STATE: ThemeDataState = {
  themeScores: null,
  themeDiscovery: null,
  themePortfolio: null,
  topThemes: [],
  emergingThemes: [],
  rotationMap: [],
  capitalFlow: [],
  sectors: [],
  rotationSnapshot: null,
  narratives: null,
  supplyChain: null,
  detail: null,
  forecast: [],
  validation: null,
  loading: true,
};

function finite(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function formatScore(value: unknown, digits = 1): string {
  const numberValue = finite(value);
  return numberValue === null ? "--" : numberValue.toFixed(digits);
}

function formatPercent(value: unknown, digits = 1): string {
  const numberValue = finite(value);
  if (numberValue === null) return "--";
  return `${numberValue >= 0 ? "+" : ""}${numberValue.toFixed(digits)}%`;
}

function themeScore(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.score)
    ?? finite(theme?.theme_strength_score)
    ?? finite(theme?.leadership_score)
    ?? finite(theme?.ranking_score)
    ?? finite(theme?.narrative_strength)
    ?? finite(theme?.relative_strength_vs_spy);
}

function themeFlow(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.flow)
    ?? finite(theme?.theme_capital_flow_score)
    ?? finite(theme?.institutional_alignment)
    ?? finite(theme?.participation_breadth)
    ?? finite(theme?.volume_expansion);
}

function themeMomentum(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.momentum)
    ?? finite(theme?.momentum_strength)
    ?? finite(theme?.relative_momentum)
    ?? finite(theme?.acceleration_velocity)
    ?? finite(theme?.trend_consistency);
}

function themeName(theme: Partial<ThemeScore> | null | undefined): string {
  return theme?.theme ?? "Theme";
}

function classForScore(value: unknown): string {
  const numberValue = finite(value);
  if (numberValue === null) return "text-[var(--theme-muted)]";
  if (numberValue >= 70) return "text-[var(--theme-bullish)]";
  if (numberValue <= 40) return "text-[var(--theme-bearish)]";
  return "text-[var(--theme-warning)]";
}

function compactLifecycle(value?: string | null): string {
  return value ? value.replace(/_/g, " ") : "partial live";
}

function topLeaders(detail: ThemeDetailResponse | null, activeTheme: ThemeScore | null): ThemeLeader[] {
  const detailRows = [...(detail?.top_alpha_stocks ?? []), ...(detail?.related_stocks ?? [])];
  const themeRows = [...(activeTheme?.top_alpha_stocks ?? []), ...(activeTheme?.related_stocks ?? []), ...(activeTheme?.leaders ?? [])];
  const rows = detailRows.length > 0 ? detailRows : themeRows;
  const seen = new Set<string>();
  return rows.filter((row) => {
    const ticker = row.ticker?.toUpperCase();
    if (!ticker || seen.has(ticker)) return false;
    seen.add(ticker);
    return true;
  }).slice(0, 10);
}

function sameTheme(left?: string | null, right?: string | null): boolean {
  return normalizeThemeIntelligenceId(left ?? "") === normalizeThemeIntelligenceId(right ?? "");
}

function scoreRecordValue(record: ThemeScoreRecord | null | undefined, field: keyof Pick<ThemeScoreRecord, "ai_potential_score" | "research_importance" | "allocation_readiness" | "risk_adjusted_score">): number | null {
  return finite(record?.[field]);
}

function stageForPhase10(record: ThemeScoreRecord | null | undefined, aggregate: ThemeAggregateResponse | null): string {
  const stage = aggregate?.lifecycle.lifecycle_stage
    ?? (record?.score_components?.lifecycle_stage ? String(record.score_components.lifecycle_stage) : null)
    ?? null;
  if (!stage) return "Unavailable";
  const compact = stage.replace(/_/g, " ").trim();
  const lower = compact.toLowerCase();
  if (lower.includes("growth")) return "???Growth";
  if (lower.includes("expansion")) return "?游撐??Expansion";
  if (lower.includes("mature")) return "????Mature";
  if (lower.includes("seed")) return "蝔桀???Seed";
  return "?拇? Early";
}

function beneficiaryToLeader(row: ThemeBeneficiaryRecord): ThemeLeader | null {
  const ticker = row.ticker?.trim().toUpperCase();
  if (!ticker) return null;
  return {
    ticker,
    company_name: row.company_name ?? row.company ?? ticker,
    alpha_score: finite(row.allocation_score) ?? finite(row.beneficiary_score),
    ...(finite(row.relationship_strength) === null ? {} : { confidence_score: finite(row.relationship_strength) ?? undefined }),
    role: row.beneficiary_type ?? row.role,
  };
}

function aggregateBeneficiaryLeaders(aggregate: ThemeAggregateResponse | null): ThemeLeader[] {
  return (aggregate?.beneficiaries.top_beneficiaries ?? [])
    .map(beneficiaryToLeader)
    .filter((row): row is ThemeLeader => Boolean(row));
}

function aggregateRoles(aggregate: ThemeAggregateResponse | null): Array<{ role: string; leaders: ThemeLeader[] }> {
  if (!aggregate) return [];
  return [
    { role: "Direct Beneficiaries", leaders: aggregate.beneficiaries.direct_beneficiaries.map(beneficiaryToLeader).filter((row): row is ThemeLeader => Boolean(row)) },
    { role: "Bottleneck Controllers", leaders: aggregate.beneficiaries.controllers.map(beneficiaryToLeader).filter((row): row is ThemeLeader => Boolean(row)) },
    { role: "Resolution Enablers", leaders: aggregate.beneficiaries.resolution_enablers.map(beneficiaryToLeader).filter((row): row is ThemeLeader => Boolean(row)) },
    { role: "Indirect Beneficiaries", leaders: aggregate.beneficiaries.indirect_beneficiaries.map(beneficiaryToLeader).filter((row): row is ThemeLeader => Boolean(row)) },
  ].filter((role) => role.leaders.length > 0);
}

function aggregateMetric(value: unknown, suffix = ""): string {
  const numeric = finite(value);
  return numeric === null ? "Unavailable" : `${formatScore(numeric, 0)}${suffix}`;
}

function aggregateControllerLabels(aggregate: ThemeAggregateResponse | null): string[] {
  const labels = (aggregate?.bottlenecks.controllers ?? []).map((controller) => {
    const company = typeof controller.company_name === "string"
      ? controller.company_name
      : typeof controller.company === "string"
        ? controller.company
        : "";
    const ticker = typeof controller.ticker === "string" ? controller.ticker : "";
    return company.trim() || ticker.trim();
  }).filter(Boolean);
  return Array.from(new Set(labels)).slice(0, 3);
}

function relationshipLabel(value: string): string {
  return value.split("_").filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function CompactEvidenceGrid({ aggregate }: { aggregate: ThemeAggregateResponse | null }) {
  const catalystFacts = (aggregate?.catalysts.top_catalysts ?? [])
    .map((item) => item.name ?? item.catalyst_name ?? "")
    .filter(Boolean);
  const constraintFacts = [
    aggregate?.bottlenecks.primary_bottleneck?.name ?? aggregate?.bottlenecks.primary_bottleneck?.bottleneck_name ?? "",
    ...(aggregate?.bottlenecks.secondary_bottlenecks ?? []).map((item) => item.name ?? item.bottleneck_name ?? ""),
  ].filter(Boolean);
  const beneficiaryFacts = (aggregate?.beneficiaries.top_beneficiaries ?? []).map((item) => item.ticker).filter(Boolean);
  const supplyFacts = (aggregate?.supply_chain.layers ?? []).map((item) => item.layer_name).filter(Boolean);
  const graphFacts = (aggregate?.relationship_intelligence.related_themes ?? []).map((item) => relationshipLabel(item.related_theme_id)).filter(Boolean);
  const controllerFacts = aggregateControllerLabels(aggregate);
  const sections = [
    { label: "Catalysts", count: catalystFacts.length, target: 3, facts: catalystFacts, missing: "catalyst evidence" },
    { label: "Constraints", count: constraintFacts.length, target: 4, facts: constraintFacts, missing: "canonical constraint evidence" },
    { label: "Beneficiaries", count: beneficiaryFacts.length, target: 5, facts: beneficiaryFacts, missing: "verified beneficiaries" },
    { label: "Supply Chain", count: supplyFacts.length, target: 5, facts: supplyFacts, missing: "verified supply-chain layers" },
    { label: "Industrial Graph", count: graphFacts.length, target: 3, facts: graphFacts, missing: "graph relationship evidence" },
    { label: "Controller", count: controllerFacts.length, target: 2, facts: controllerFacts, missing: "controller evidence" },
    { label: "Opportunity", count: 0, target: 1, facts: [], missing: "opportunity evidence" },
    { label: "Decision Packet", count: 0, target: 1, facts: [], missing: "decision packet evidence" },
  ];
  return (
    <section className="theme-evidence-shell" aria-label="Theme evidence coverage">
      <div className="ai-panel-head"><BilingualLabel zh="霅?閬?" en="Evidence Coverage" inline /><span>Verified persisted evidence only</span></div>
      <div className="theme-evidence-grid">
        {sections.map((section) => (
          <article key={section.label} className="theme-evidence-card" data-available={section.count > 0}>
            <div><strong>{section.label}</strong><span>{section.count}/{section.target}</span></div>
            {section.facts.length > 0
              ? <ul>{section.facts.slice(0, 2).map((fact, index) => <li key={`${section.label}-${index}`}>{fact}</li>)}</ul>
              : <p>Status: Missing evidence</p>}
            {section.count < section.target && <span className="theme-evidence-gap-chip">Missing: {section.missing}</span>}
          </article>
        ))}
      </div>
    </section>
  );
}

function ThemeIntelligenceSummary({
  aggregate,
  rank,
  totalThemes,
  portfolioWeight,
}: {
  aggregate: ThemeAggregateResponse | null;
  rank: number | null;
  totalThemes: number;
  portfolioWeight: number | null;
}) {
  const lifecycle = aggregate?.lifecycle;
  const catalysts = (aggregate?.catalysts.top_catalysts ?? [])
    .map((item) => item.name ?? item.catalyst_name ?? "")
    .filter(Boolean)
    .slice(0, 4);
  const bottleneck = aggregate?.bottlenecks.primary_bottleneck ?? null;
  const controllers = aggregateControllerLabels(aggregate);
  const score = aggregate?.score;
  const relationships = (aggregate?.relationship_intelligence.related_themes ?? []).slice(0, 4);

  return (
    <section className="ai-panel theme-intelligence-summary">
      <div className="ai-panel-head">
        <span>Theme Intelligence Summary</span>
        <span>Phase 10 Aggregate</span>
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Positioning</span><small>Score + Portfolio Engines</small></div>
        <div className="theme-momentum-grid">
          <div className="theme-momentum-metric"><span>Rank</span><strong>{rank !== null && totalThemes > 0 ? `#${rank} / ${totalThemes}` : "Unavailable"}</strong></div>
          <div className="theme-momentum-metric"><span>Portfolio Weight</span><strong>{aggregateMetric(portfolioWeight, "%")}</strong></div>
          <div className="theme-momentum-metric"><span>Research Importance</span><strong>{aggregateMetric(score?.research_importance)}</strong></div>
          <div className="theme-momentum-metric"><span>Risk Adjusted Score</span><strong>{aggregateMetric(score?.risk_adjusted_score)}</strong></div>
        </div>
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Momentum</span><small>Lifecycle Engine</small></div>
        <div className="theme-momentum-grid">
          <div className="theme-momentum-metric"><span>Current Stage</span><strong>{lifecycle?.lifecycle_stage ?? "Unavailable"}</strong></div>
          <div className="theme-momentum-metric"><span>Stage Confidence</span><strong>{aggregateMetric(lifecycle?.lifecycle_confidence, "%")}</strong></div>
          <div className="theme-momentum-metric"><span>Expected Next Stage</span><strong>{lifecycle?.expected_next_stage ?? "Unavailable"}</strong></div>
          <div className="theme-momentum-metric"><span>Estimated Time Window</span><strong>{lifecycle?.time_window ?? "Unavailable"}</strong></div>
        </div>
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Why Now</span><small>Catalyst Engine</small></div>
        {catalysts.length > 0
          ? <ul className="theme-momentum-evidence">{catalysts.map((catalyst) => <li key={catalyst}>{catalyst}</li>)}</ul>
          : <p className="theme-momentum-empty">No catalyst evidence available.</p>}
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Primary Bottleneck</span><small>Bottleneck Engine</small></div>
        {bottleneck
          ? <div className="theme-momentum-bottleneck">
            <strong>{bottleneck.name ?? bottleneck.bottleneck_name ?? "Unavailable"}</strong>
            <div>
              <span><small>Severity</small><b>{aggregateMetric(bottleneck.severity_score)}</b></span>
              <span><small>Resolution Probability</small><b>{aggregateMetric(bottleneck.resolution_probability, "%")}</b></span>
              <span><small>Controller</small><b>{controllers.length > 0 ? controllers.join(", ") : "Unavailable"}</b></span>
            </div>
          </div>
          : <p className="theme-momentum-empty">No bottleneck evidence available.</p>}
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Conviction Summary</span><small>Theme Score Engine</small></div>
        <div className="theme-conviction-grid">
          <div className="theme-momentum-metric"><span>Allocation Readiness</span><strong>{aggregateMetric(score?.allocation_readiness)}</strong></div>
          <div className="theme-momentum-metric"><span>Conviction Level</span><strong>{score?.conviction_level ?? "Unrated"}</strong></div>
        </div>
      </div>

      <div className="theme-momentum-section">
        <div className="theme-momentum-section-head"><span>Theme Relationship Intelligence</span><small>Phase 10.12 Knowledge Graph</small></div>
        {relationships.length > 0
          ? <div className="theme-relationship-list">
            {relationships.map((relationship) => {
              const evidence = [
                ...relationship.shared_controllers.map((item) => `Controller ${item}`),
                ...relationship.shared_beneficiaries.map((item) => `Beneficiary ${item}`),
                ...relationship.shared_portfolios.map((item) => `Portfolio ${relationshipLabel(item)}`),
                ...relationship.shared_supply_chain_roles.map((item) => `Role ${relationshipLabel(item)}`),
              ].slice(0, 3);
              return (
                <div key={relationship.related_theme_id} className="theme-relationship-row">
                  <div><strong>{relationshipLabel(relationship.related_theme_id)}</strong><b>{aggregateMetric(relationship.overlap_score)}</b></div>
                  {evidence.length > 0 && <p>{evidence.map((item) => <span key={item}>{item}</span>)}</p>}
                </div>
              );
            })}
          </div>
          : <p className="theme-momentum-empty">No relationship intelligence available.</p>}
      </div>
    </section>
  );
}

function forecastForTheme(records: ThemeForecastRecord[], theme: string): ThemeForecastRecord | null {
  return records.find((record) => record.theme.toLowerCase() === theme.toLowerCase()) ?? records[0] ?? null;
}

function ThemeRankRow({
  theme,
  active,
  onSelect,
  onPreview,
  onPreviewEnd,
  onDrilldown,
}: {
  theme: ThemeScore;
  active: boolean;
  onSelect: (theme: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}) {
  const score = themeScore(theme);
  const flow = themeFlow(theme);
  const momentum = themeMomentum(theme);
  return (
    <MarketRow
      columns={THEME_TABLE_COLUMNS}
      onClick={() => onSelect(theme.theme)}
      onDoubleClick={() => onDrilldown?.({ kind: "theme", name: theme.theme, value: score, meta: compactLifecycle(theme.lifecycle_state) })}
      onPreview={() => onPreview?.({ kind: "theme", name: theme.theme, value: score, meta: compactLifecycle(theme.lifecycle_state) })}
      onPreviewEnd={onPreviewEnd}
      active={active}
    >
      <MarketCell>
        <span className="flex min-w-0 items-center gap-2">
          <ThemeIcon theme={theme.theme} />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{theme.theme}</span>
            <span className="mt-0.5 flex min-w-0 items-center gap-2 text-[11px] text-[var(--theme-muted)]">
              <StatusDot state={theme.status ?? theme.lifecycle_state} label={theme.category || theme.status || "Theme"} />
            </span>
          </span>
        </span>
      </MarketCell>
      <NumericCell className={`text-sm font-semibold ${classForScore(score)}`}>{formatScore(score)}</NumericCell>
      <NumericCell><FlowIndicator value={flow} /></NumericCell>
      <MarketCell><HeatStrip value={momentum} /></MarketCell>
    </MarketRow>
  );
}

function sectorWeight(sector: SectorRotation): number {
  return capitalFlowWeight(finite(sector.flow));
}

function sectorTreemapItem(sector: SectorRotation): MarketTreemapItem {
  return {
    id: sector.sector,
    label: sector.sector,
    weight: sectorWeight(sector),
    score: finite(sector.score),
    momentum: finite(sector.momentum ?? sector.momentum_20d ?? sector.relative_strength),
    flow: finite(sector.flow),
    relativeStrength: finite(sector.relative_strength),
    state: sector.rotation_state ?? sector.lifecycle_state,
  };
}

function beneficiaryMatrixRow(row: ThemeLeader): BeneficiaryMatrixRow {
  return {
    ticker: row.ticker,
    company: row.company_name,
    alpha: finite(row.alpha_score ?? row.confidence_score),
    risk: finite(row.bubble_risk),
    flow: finite(row.smart_money ?? row.relative_volume),
    relativeStrength: finite(row.momentum_3m ?? row.change_percent),
    exposure: finite(row.confidence_score ?? row.alpha_score),
  };
}
function SectorRow({ sector, active, onSelect, onPreview, onPreviewEnd, onDrilldown }: { sector: SectorRotation; active: boolean; onSelect: (sector: string) => void; onPreview?: (target: DrilldownTarget) => void; onPreviewEnd?: () => void; onDrilldown?: (target: DrilldownTarget) => void }) {
  return (
    <MarketRow
      columns={SECTOR_TABLE_COLUMNS}
      onClick={() => onSelect(sector.sector)}
      onDoubleClick={() => onDrilldown?.({ kind: "sector", name: sector.sector, value: finite(sector.score), meta: sector.rotation_state ?? compactLifecycle(sector.lifecycle_state) })}
      onPreview={() => onPreview?.({ kind: "sector", name: sector.sector, value: finite(sector.score), meta: sector.rotation_state ?? compactLifecycle(sector.lifecycle_state) })}
      onPreviewEnd={onPreviewEnd}
      active={active}
    >
      <MarketCell>
        <span className="flex min-w-0 items-center gap-2">
          <SectorIcon sector={sector.sector} />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">{sector.sector}</span>
            <span className="mt-0.5 block text-[11px] text-[var(--theme-muted)]">{sector.rotation_state ?? compactLifecycle(sector.lifecycle_state)}</span>
          </span>
        </span>
      </MarketCell>
      <NumericCell className={`text-sm font-semibold ${classForScore(sector.score)}`}>{formatScore(sector.score)}</NumericCell>
      <NumericCell className="text-sm font-semibold text-[var(--theme-text-secondary)]">{formatScore(sector.relative_strength)}</NumericCell>
      <NumericCell><FlowIndicator value={finite(sector.flow)} /></NumericCell>
      <MarketCell className="truncate text-right"><StatusDot state={sector.rotation_state ?? sector.lifecycle_state} label={sector.rotation_state ?? compactLifecycle(sector.lifecycle_state)} /></MarketCell>
    </MarketRow>
  );
}

function BeneficiaryList({ rows, onPreview, onPreviewEnd, onContext, onTickerSelect }: { rows: ThemeLeader[]; onPreview?: (target: DrilldownTarget) => void; onPreviewEnd?: () => void; onContext?: (target: DrilldownTarget) => void; onTickerSelect?: (ticker: string) => void }) {
  return (
    <MarketTable
      columns={BENEFICIARY_TABLE_COLUMNS}
      header={rows.length > 0 && (
        <>
          <MarketCell>?∠巨 Stock</MarketCell>
          <MarketCell>閫 Role</MarketCell>
          <NumericCell>Alpha</NumericCell>
          <NumericCell>? Move</NumericCell>
        </>
      )}
    >
      {rows.length === 0 ? (
        <div className="py-3 text-sm text-[var(--theme-muted)]">No beneficiary stock payload yet.</div>
      ) : rows.map((row) => (
        <MarketRow
          key={`${row.ticker}-${row.role ?? "leader"}`}
          columns={BENEFICIARY_TABLE_COLUMNS}
          onClick={() => row.ticker && onContext?.({ kind: "stock", symbol: row.ticker, label: row.company_name || row.ticker, value: finite(row.alpha_score ?? row.confidence_score ?? row.change_percent), meta: row.role ?? row.quote_status })}
          onDoubleClick={() => row.ticker && onTickerSelect?.(row.ticker)}
          onPreview={() => row.ticker && onPreview?.({ kind: "stock", symbol: row.ticker, label: row.company_name || row.ticker, value: finite(row.alpha_score ?? row.confidence_score ?? row.change_percent), meta: row.role ?? row.quote_status })}
          onPreviewEnd={onPreviewEnd}
        >
          <TickerCell>
            <span className="flex items-center gap-2"><TickerLogo ticker={row.ticker} /><span>{row.ticker}</span></span>
          </TickerCell>
          <MarketCell>
            <span className="block truncate text-xs text-[var(--theme-text-secondary)]">{row.company_name || row.role || "Theme leader"}</span>
            <span className="block truncate text-[10px] text-[var(--theme-muted)]">{row.role || row.quote_status || "Beneficiary"}</span>
          </MarketCell>
          <NumericCell className={`text-sm font-semibold ${classForScore(row.alpha_score ?? row.confidence_score ?? row.change_percent)}`}>
            {finite(row.alpha_score) !== null ? formatScore(row.alpha_score) : formatPercent(row.change_percent)}
          </NumericCell>
          <ChangeCell value={finite(row.change_percent)} className="text-xs font-semibold">{formatPercent(row.change_percent)}</ChangeCell>
        </MarketRow>
      ))}
    </MarketTable>
  );
}

function MetricStrip({ items }: { items: Array<{ label: string; value: unknown }> }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-y border-[var(--theme-border)] py-3">
      {items.map((item, index) => (
        <div key={item.label} className="flex items-baseline gap-2">
          {index > 0 && <span className="hidden h-4 w-px bg-[var(--theme-border)] sm:inline-block" />}
          <span className="text-[11px] font-medium text-[var(--theme-muted)]">{item.label}</span>
          <span className={`font-mono text-sm font-semibold ${classForScore(item.value)}`}>{formatScore(item.value)}</span>
        </div>
      ))}
    </div>
  );
}

function VisualStrip({ items }: { items: Array<{ label: string; value: unknown; state?: string | null }> }) {
  return (
    <div className="mb-5 grid gap-3 md:grid-cols-4">
      {items.map((item) => {
        const score = finite(item.value);
        return (
          <div key={item.label} className="border-y border-[rgba(255,255,255,0.026)] px-1 py-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[11px] text-[var(--theme-muted)]">{item.label}</span>
              <span className={`font-mono text-lg font-semibold ${classForScore(score)}`}>{formatScore(score)}</span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <HeatStrip value={score} className="w-full" />
              <StatusDot state={item.state ?? String(item.value ?? "")} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SupplyDependencyMap({
  theme,
  roles,
  selectedRole,
  onSelectRole,
  onPreview,
  onPreviewEnd,
  onContext,
  onDrilldown,
}: {
  theme: string;
  roles: Array<{ role: string; leaders: ThemeLeader[] }>;
  selectedRole: string;
  onSelectRole: (role: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}) {
  return (
    <div className="dependency-map">
      <div className="dependency-node dependency-root">
        <ThemeIcon theme={theme} />
        <span className="truncate">{theme}</span>
      </div>
      <div className="dependency-lanes">
        {roles.map((role) => {
          const active = selectedRole === role.role;
          return (
            <button
              key={role.role}
              type="button"
              data-active={active ? "true" : undefined}
              className="dependency-node"
              onClick={() => {
                onSelectRole(role.role);
                onContext?.({ kind: "supply", name: theme, subject: role.role, value: role.leaders.length * 20, meta: "Dependency node" });
              }}
              onDoubleClick={() => onDrilldown?.({ kind: "supply", name: theme, subject: role.role, value: role.leaders.length * 20, meta: "Dependency node" })}
              onMouseEnter={() => onPreview?.({ kind: "supply", name: theme, subject: role.role, value: role.leaders.length * 20, meta: "Dependency node" })}
              onMouseLeave={onPreviewEnd}
              onFocus={() => onPreview?.({ kind: "supply", name: theme, subject: role.role, value: role.leaders.length * 20, meta: "Dependency node" })}
              onBlur={onPreviewEnd}
            >
              <span className="truncate text-sm font-semibold text-[var(--theme-text)]">{role.role}</span>
              <span className="mt-2 flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-[var(--theme-muted)]">{role.leaders.length} nodes</span>
                <HeatStrip value={role.leaders.length * 20} />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RiskStressGrid({
  items,
  onSelect,
  selected,
  onPreview,
  onPreviewEnd,
  onContext,
  onDrilldown,
}: {
  items: Array<{ label: string; value: unknown; state?: string | null }>;
  onSelect: (label: string) => void;
  selected: string;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}) {
  return (
    <div className="stress-map">
      {items.map((item) => {
        const score = finite(item.value);
        const state = score === null ? "neutral" : score >= 72 ? "overheating" : score <= 40 ? "distribution" : "neutral";
        return (
          <button
            key={item.label}
            type="button"
            data-active={selected === item.label ? "true" : undefined}
            className="stress-cell"
            onClick={() => {
              onSelect(item.label);
              onContext?.({ kind: "risk", name: item.label, subject: item.state ?? state, value: score, meta: "Risk factor" });
            }}
            onDoubleClick={() => onDrilldown?.({ kind: "risk", name: item.label, subject: item.state ?? state, value: score, meta: "Risk factor" })}
            onMouseEnter={() => onPreview?.({ kind: "risk", name: item.label, subject: item.state ?? state, value: score, meta: "Risk factor" })}
            onMouseLeave={onPreviewEnd}
            onFocus={() => onPreview?.({ kind: "risk", name: item.label, subject: item.state ?? state, value: score, meta: "Risk factor" })}
            onBlur={onPreviewEnd}
          >
            <span className="flex items-center justify-between gap-3">
              <span className="text-sm font-semibold text-[var(--theme-text)]">{item.label}</span>
              <StatusDot state={state} label={state} />
            </span>
            <span className={`mt-4 block font-mono text-2xl font-semibold ${classForScore(score)}`}>{formatScore(score)}</span>
            <span className="mt-4 flex items-center gap-3">
              <HeatStrip value={score} className="w-full" />
              <ConfidenceMeter value={score} label="Stress" />
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ForecastTab({
  forecast,
  validation,
  selectedTheme,
}: {
  forecast: ThemeForecastRecord[];
  validation: ThemeForecastValidationResponse | null;
  selectedTheme: string;
}) {
  const selectedForecast = forecastForTheme(forecast, selectedTheme);
  return (
    <div id="theme-forecast" tabIndex={-1} className="grid gap-4 outline-none xl:grid-cols-[1.2fr_0.8fr]">
      <TerminalPanel
        eyebrow="?葫 Forecast"
        title={selectedForecast ? `${selectedForecast.theme} Path` : "Forecast Path"}
        description="Score, probability, risk."
      >
        <div className="mb-5 border-y border-[rgba(255,255,255,0.026)] py-4">
          <div className="mb-3 flex items-center justify-between">
            <BilingualLabel zh="?葫?脩?" en="Forecast Curve" inline />
            <SparklineMini values={forecast.slice(0, 8).map((item) => item.forecast_score)} />
          </div>
          <div className="flex items-end gap-2">
            {forecast.slice(0, 7).map((item) => (
              <div key={`${item.theme}-${item.forecast_horizon}`} className="min-w-0 flex-1">
                <div className="h-16 rounded-t-[4px] bg-[rgba(255,255,255,0.018)]">
                  <div className="mt-auto rounded-t-[4px] bg-[var(--theme-warning)]" style={{ height: `${Math.max(8, Math.min(100, item.forecast_score ?? 0))}%` }} />
                </div>
                <p className="mt-2 truncate text-[10px] text-[var(--theme-muted)]">{item.theme}</p>
              </div>
            ))}
          </div>
        </div>
        <MetricStrip
          items={[
            { label: "Forecast Score", value: selectedForecast?.forecast_score },
            { label: "Expected Excess", value: selectedForecast?.expected_excess_return },
            { label: "Probability", value: selectedForecast?.outperformance_probability !== null && selectedForecast?.outperformance_probability !== undefined ? selectedForecast.outperformance_probability * 100 : null },
          ]}
        />
        <div className="mt-4 line-clamp-2 border-b border-[var(--theme-border)] pb-4 text-sm leading-6 text-[var(--theme-text-secondary)]">
          {selectedForecast?.explanation || "Forecast engine is warming. Live theme research remains available from lightweight factors."}
        </div>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <div>
            <p className="terminal-micro-label">Positive Drivers</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--theme-text-secondary)]">
              {(selectedForecast?.top_positive_drivers ?? []).slice(0, 5).map((driver) => <li key={driver}>+ {driver}</li>)}
            </ul>
          </div>
          <div>
            <p className="terminal-micro-label">Negative Drivers</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--theme-text-secondary)]">
              {(selectedForecast?.top_negative_drivers ?? []).slice(0, 5).map((driver) => <li key={driver}>- {driver}</li>)}
            </ul>
          </div>
        </div>
      </TerminalPanel>
      <TerminalPanel eyebrow="撽? Validation" title="Walk-Forward" description="Chronological validation.">
        <MetricStrip
          items={[
            { label: "Hit Rate", value: validation?.hit_rate },
            { label: "Precision@5", value: validation?.precision_at_5 },
            { label: "Info Ratio", value: validation?.information_ratio },
            { label: "Stability", value: validation?.excess_return_stability },
          ]}
        />
        <div className="mt-4 border-t border-[var(--theme-border)] pt-3 text-xs leading-relaxed text-[var(--theme-muted)]">
          Status: {compactLifecycle(validation?.lifecycle_state)} / Observations: {validation?.observations ?? 0}
        </div>
      </TerminalPanel>
    </div>
  );
}

export default function ThemeResearchPage({ activeSelection = null, aggregateIntelligence = null, onTickerSelect, onPreview, onPreviewEnd, onContext, onDrilldown }: ThemeResearchPageProps) {
  const {
    selectedTheme,
    selectedSector,
    selectedThemeView,
    activeModule,
    setSelectedTheme,
    setSelectedSector,
    setSelectedThemeView,
    setActiveModule,
  } = useWorkspace();
  const [data, setData] = useState<ThemeDataState>(EMPTY_STATE);
  const [selectedSupplyRole, setSelectedSupplyRole] = useState("");
  const [selectedRiskFactor, setSelectedRiskFactor] = useState("Crowding");
  const [selectedBeneficiary, setSelectedBeneficiary] = useState("");
  const [themeRegistry, setThemeRegistry] = useState<ThemeRegistryEntry[]>([]);
  const [themeRanking, setThemeRanking] = useState<ThemeRank[]>([]);
  const hydratedTime = useHydratedTime({ locale: "zh-TW" });
  const activeTab = MODULE_VIEW[activeModule] ?? TAB_ALIASES[selectedThemeView] ?? "command";

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    async function load() {
      setData((current) => ({ ...current, loading: true }));
      const [themeScores, themePortfolio, rotationSnapshot, registry, ranking] = await Promise.all([
        fetchThemeScores().catch(() => null),
        fetchThemePortfolio().catch(() => null),
        fetchSectorRotation({ signal: controller.signal }).catch(() => null),
        fetchThemeRegistry(controller.signal).catch(() => null),
        fetchThemeRanking(controller.signal).catch(() => null),
      ]);
      if (cancelled) return;
      setThemeRegistry(registry?.themes ?? []);
      setThemeRanking(ranking?.themes ?? []);
      setData((current) => ({
        ...current,
        themeScores,
        themeDiscovery: null,
        themePortfolio,
        topThemes: [],
        emergingThemes: [],
        rotationMap: [],
        capitalFlow: [],
        sectors: rotationSnapshot?.sector_ranking ?? [],
        rotationSnapshot,
        narratives: null,
        forecast: [],
        validation: null,
        loading: false,
      }));
    }
    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const registryThemes = useMemo(
    () => rankingAwareThemeOrder(sortThemeRegistryEntries(themeRegistry), themeRanking),
    [themeRanking, themeRegistry],
  );

  const selectedEntityTheme = activeSelection?.kind === "theme"
    ? activeSelection.subject ?? activeSelection.name ?? activeSelection.label
    : activeSelection?.kind === "supply" || activeSelection?.kind === "supply_chain"
      ? activeSelection.name
      : null;
  const scoreThemeSeed = data.themeScores?.rankings?.top_ai_themes?.[0]?.theme ?? data.themeScores?.themes?.[0]?.theme ?? registryThemes[0]?.theme_id;
  const selectedThemeIdentity = resolveCanonicalThemeSelection(
    selectedEntityTheme,
    selectedTheme,
    scoreThemeSeed,
    data.themeDiscovery?.themes?.[0]?.name,
  );
  const selectedThemeName = selectedThemeIdentity.displayName;
  const selectedThemeId = selectedThemeIdentity.themeId;

  useEffect(() => {
    if (selectedThemeName && selectedTheme !== selectedThemeName) setSelectedTheme(selectedThemeName);
  }, [selectedTheme, selectedThemeName, setSelectedTheme]);

  useEffect(() => {
    traceThemeIdentity(
      activeTab === "supply-chain" ? "supply_chain_selection" : "theme_selection",
      selectedThemeIdentity.rawName,
      selectedThemeId,
      selectedThemeId || null,
    );
  }, [activeTab, selectedThemeId, selectedThemeIdentity.rawName]);

  // Hoist selectedAggregate before useMemos so it's available to supplyIntelligence.
  const selectedAggregate = aggregateIntelligence && sameTheme(aggregateIntelligence.theme_id, selectedThemeId) ? aggregateIntelligence : null;

  const activeTheme = null;
  const phase10ThemeRows = useMemo(() => {
    const ranked = data.themeScores?.rankings?.top_ai_themes?.length ? data.themeScores.rankings.top_ai_themes : data.themeScores?.themes ?? [];
    const seen = new Set<string>();
    return ranked.filter((theme) => {
      const id = normalizeThemeIntelligenceId(theme.theme_id || theme.theme);
      if (!id || seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  }, [data.themeScores]);
  const selectedScore = useMemo(() => (
    phase10ThemeRows.find((theme) => sameTheme(theme.theme_id, selectedThemeName) || sameTheme(theme.theme, selectedThemeName))
    ?? phase10ThemeRows[0]
    ?? null
  ), [phase10ThemeRows, selectedThemeName]);

  const forecast = useMemo(() => forecastForTheme(data.forecast, selectedThemeName), [data.forecast, selectedThemeName]);
  const leaders = useMemo(() => aggregateBeneficiaryLeaders(selectedAggregate), [selectedAggregate]);
  const roles = useMemo(() => (selectedAggregate?.supply_chain.layers ?? []).map((layer) => ({
    role: layer.layer_name,
    leaders: layer.entities.map((entity) => ({
      ticker: entity.ticker,
      company_name: entity.company,
      role: entity.role,
      confidence_score: entity.strength,
    })),
  })), [selectedAggregate]);
  const activeSupplyRoleName = activeSelection?.kind === "supply" || activeSelection?.kind === "supply_chain" ? activeSelection.subject ?? activeSelection.name : selectedSupplyRole;
  const activeSupplyRole = roles.find((role) => role.role === activeSupplyRoleName) ?? null;
  const narrative = data.narratives?.narratives?.find((item) => (item.theme ?? item.narrative_name).toLowerCase().includes(selectedThemeName.toLowerCase())) ?? data.narratives?.top_narratives?.[0] ?? null;
  const selectedEntitySector = activeSelection?.kind === "sector" ? activeSelection.name ?? activeSelection.label : null;
  const activeSector = data.sectors.find((sector) => sector.sector.toLowerCase() === (selectedEntitySector ?? selectedSector).toLowerCase()) ?? data.sectors[0] ?? null;
  const flowRows = data.capitalFlow.length > 0 ? data.capitalFlow : data.topThemes;
  const flowEndpoints = useMemo(() => Object.fromEntries([
    ...roles.map((role) => [role.role, (role.leaders ?? []).map((leader) => leader.ticker)]),
    ...flowRows.map((theme) => [theme.theme, (theme.leaders ?? []).map((leader) => leader.ticker)]),
  ]), [flowRows, roles]);
  const beneficiarySelection = useMemo(() => resolveActiveBeneficiaries({
    target: activeSelection,
    currentTheme: selectedThemeName,
    themes: [...data.topThemes, ...data.rotationMap, ...data.capitalFlow],
    detail: data.detail,
    sectors: data.sectors,
    roles,
    flowEndpoints,
  }), [activeSelection, data.capitalFlow, data.detail, data.rotationMap, data.sectors, data.topThemes, flowEndpoints, roles, selectedThemeName]);
  const rotationBeneficiarySelection = useMemo(() => resolveActiveBeneficiaries({
    target: activeSector ? {
      kind: "sector",
      name: activeSector.sector,
      intelligence: { relatedThemes: safeArray(data.topThemes).slice(0, 5).map((theme) => theme.theme) },
    } : null,
    currentTheme: selectedThemeName,
    themes: [...safeArray(data.topThemes), ...safeArray(data.rotationMap), ...safeArray(data.capitalFlow)],
    detail: data.detail,
    sectors: safeArray(data.sectors),
    roles,
    flowEndpoints,
  }), [activeSector, data.capitalFlow, data.detail, data.rotationMap, data.sectors, data.topThemes, flowEndpoints, roles, selectedThemeName]);
  const supplyIntelligence = useMemo(() => deriveSupplyChainIntelligence({
    theme: selectedThemeName,
    aggregateSupplyChain: selectedAggregate?.supply_chain ?? null,
  }), [selectedAggregate, selectedThemeName]);

  useEffect(() => {
    setSelectedBeneficiary("");
    if (activeSelection?.kind === "supply" || activeSelection?.kind === "supply_chain") {
      setSelectedSupplyRole(activeSelection.subject ?? activeSelection.name ?? "");
    } else {
      setSelectedSupplyRole("");
    }
  }, [activeSelection]);

  const selectTheme = (theme: string) => {
    const registryEntry = findThemeRegistryEntry(registryThemes, theme);
    const themeId = registryEntry?.theme_id ?? theme;
    const themeLabel = registryEntry?.theme_name ?? theme;
    setSelectedTheme(themeId);
    const phase10Row = phase10ThemeRows.find((item) => sameTheme(item.theme, theme) || sameTheme(item.theme_id, theme));
    onContext?.({ kind: "theme", name: themeLabel, subject: themeId, value: scoreRecordValue(phase10Row, "ai_potential_score"), meta: phase10Row?.conviction_level });
  };
  const setTab = setSelectedThemeView;
  const openThemeFromRotation = (theme: string) => {
    selectTheme(theme);
    setActiveModule("theme-intelligence");
    setTab("command");
  };
  const selectSector = (sector: string) => {
    setSelectedSector(sector);
    const row = data.sectors.find((item) => item.sector === sector);
    onContext?.({ kind: "sector", name: sector, value: finite(row?.score), meta: row?.rotation_state ?? compactLifecycle(row?.lifecycle_state) });
  };

  if (activeTab === "forecast") {
    return (
      <main id="theme-research" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
        <Header activeTab={activeTab} loading={data.loading} />
        <ForecastTab forecast={data.forecast} validation={data.validation} selectedTheme={selectedThemeName} />
      </main>
    );
  }

  if (activeTab === "rotation") {
    const safeSectors = safeArray(data.sectors);
    const rotationSnapshot = data.rotationSnapshot;
    const rotationModel = buildRotationWorkspace(safeSectors, activeSector?.sector ?? selectedSector);
    const treemapItems = safeSectors.map(sectorTreemapItem);
    const selectedSectorRankedThemes = registryThemes.slice(0, 5);
    const sectorTarget = (item: MarketTreemapItem): DrilldownTarget => ({
      kind: "sector",
      name: item.label,
      label: item.label,
      value: finite(item.score),
      meta: item.state ?? "Sector Rotation Workspace",
      intelligence: {
        flow: finite(item.flow),
        exposure: [String(item.state ?? "unavailable")],
        relatedThemes: registryThemes.slice(0, 5).map((theme) => theme.theme_name),
      },
    });
    const selectTreemapSector = (item: MarketTreemapItem) => {
      setSelectedSector(item.label);
      onContext?.(sectorTarget(item));
    };
    const selectedRotation = rotationModel.selected;
    const rotationBeneficiaries = rotationBeneficiarySelection.rows.slice(0, 5);
    const leadingThemes = selectedSectorRankedThemes.slice(0, 2);
    const supportingThemes = selectedSectorRankedThemes.slice(2, 5);
    const rotationRisk =
      finite(selectedRotation?.volatility_quality) ??
      (finite(selectedRotation?.momentum) === null ? null : 100 - (finite(selectedRotation?.momentum) ?? 50));
    const rotationDiagnostics = [
      { labelZh: "市場狀態", labelEn: "Market Regime", value: rotationSnapshot?.market_regime ?? "unavailable" },
      { labelZh: "風險偏好", labelEn: "Risk Appetite", value: rotationSnapshot?.risk_appetite ?? "unavailable" },
      { labelZh: "波動狀態", labelEn: "Volatility", value: rotationSnapshot?.volatility_state ?? "unavailable" },
      { labelZh: "輪動偏向", labelEn: "Rotation Bias", value: rotationSnapshot?.rotation_bias ?? "unavailable" },
    ];

    return (
      <main className="rotation-workspace rotation-command-center institutional-page page-scrollable" data-testid="rotation-workspace">
        {/* Legacy layout contract markers: className="rotation-capital-flow-surface"; className="rotation-unified-intelligence-panel"; data-state="improving". */}
        <header className="rotation-command-center-header">
          <BilingualLabel zh="資金流向指揮中心" en="Capital Flow Command Center" inline />
          <span>Where is capital moving?</span>
        </header>

        <section className="rotation-command-center-grid">
          <div className="rotation-capital-flow-surface rotation-command-center-treemap">
          <div className="market-command-pane rotation-treemap-pane">
            <div className="market-command-pane-head">
              <BilingualLabel zh="資金流向熱圖" en="Capital Flow Treemap" inline />
            </div>
            <MarketTreemap items={treemapItems} selectedId={activeSector?.sector ?? null} onSelect={selectTreemapSector} />
            <div className="rotation-legend-strip" aria-label="Rotation state legend">
              <span data-state="strong-leader" className="rotation-legend-pill rotation-state-strong-leader">Strong Leader</span>
              <span data-state="leader" className="rotation-legend-pill rotation-state-leader">Leader</span>
              <span data-state="neutral" className="rotation-legend-pill rotation-state-neutral">Neutral</span>
              <span data-state="weakening" className="rotation-legend-pill rotation-state-weakening">Weakening</span>
              <span data-state="laggard" className="rotation-legend-pill rotation-state-laggard">Laggard</span>
            </div>
          </div>
          </div>

          <aside className="rotation-command-center-middle">
            <section className="market-command-pane">
              <div className="market-command-pane-head">
                <BilingualLabel zh="市場診斷" en="Market Diagnostics" inline />
              </div>
              <div className="rotation-diagnostic-grid">
                {rotationDiagnostics.map((item) => (
                  <div key={item.labelEn} className="rotation-diagnostic-cell">
                    <BilingualLabel zh={item.labelZh} en={item.labelEn} inline />
                    <strong>{String(item.value)}</strong>
                  </div>
                ))}
              </div>
            </section>

            <CapitalFlowStory sector={selectedRotation} />
          </aside>

          <aside className="rotation-command-center-right">
            <DynamicThemeRotationPanel
              themes={registryThemes}
              selectedTheme={selectedThemeId}
              onThemeSelect={openThemeFromRotation}
              titleZh="主題輪動"
              titleEn="Theme Rotation Panel"
              limit={5}
              variant="rail"
            />
          </aside>
        </section>

        {selectedRotation ? (
          <section className="rotation-selected-sector-compact">
            <article className="market-command-pane selected-sector-intelligence">
              <div className="market-command-pane-head">
                <BilingualLabel zh="選定產業情報" en="Selected Sector Intelligence" inline />
                <StatusDot state={selectedRotation.rotation_state ?? selectedRotation.lifecycle_state} label={selectedRotation.rotation_state ?? selectedRotation.lifecycle_state ?? "Selected"} />
              </div>
              <div className="sector-intelligence-scoreline">
                <div>
                  <span>Rotation Score</span>
                  <strong>{formatPercent(selectedRotation.score)}</strong>
                </div>
                <div>
                  <span>Momentum</span>
                  <strong>{formatPercent(selectedRotation.momentum)}</strong>
                </div>
                <div>
                  <span>Capital Flow</span>
                  <strong>{formatScore(selectedRotation.flow, 0)}</strong>
                </div>
                <div>
                  <span>Risk Quality</span>
                  <strong>{formatPercent(rotationRisk)}</strong>
                </div>
              </div>
              <HeatStrip value={selectedRotation.score} label="Rotation strength" />
              <div className="selected-sector-compact-grid">
                <section>
                  <span>Leading Themes</span>
                  <strong>{leadingThemes.length ? leadingThemes.map((theme) => theme.theme_name).join(", ") : "Unavailable"}</strong>
                </section>
                <section>
                  <span>Supporting Themes</span>
                  <strong>{supportingThemes.length ? supportingThemes.map((theme) => theme.theme_name).join(", ") : "Unavailable"}</strong>
                </section>
                <section>
                  <span>Key Beneficiaries</span>
                  <strong>{rotationBeneficiaries.length ? rotationBeneficiaries.map((row) => row.ticker).join(", ") : "Unavailable"}</strong>
                </section>
                <section>
                  <span>Supporting Evidence</span>
                  <strong>{selectedRotation.confidence_score === null || selectedRotation.confidence_score === undefined ? "Unavailable" : `Confidence ${formatPercent(selectedRotation.confidence_score)}`}</strong>
                </section>
              </div>
            </article>
          </section>
        ) : null}
      </main>
    );
  }
  if (activeTab === "supply-chain") {
    if (selectedAggregate?.industrial_intelligence) {
      return (
        <main id="theme-research" tabIndex={-1} className="theme-industrial-supply-page text-[var(--theme-text)] outline-none ring-0">
          <IndustrialDependencyWorkflow
            aggregate={selectedAggregate}
            selectedTheme={selectedThemeId}
            registryThemes={registryThemes}
            onThemeSelect={selectTheme}
            onPreview={onPreview}
            onPreviewEnd={onPreviewEnd}
            onContext={onContext}
            onDrilldown={onDrilldown}
          />
        </main>
      );
    }
    return (
      <main id="theme-research" tabIndex={-1} className="theme-industrial-supply-page text-[var(--theme-text)] outline-none ring-0">
        <DynamicThemeRotationPanel
          themes={registryThemes}
          selectedTheme={selectedThemeId}
          onThemeSelect={selectTheme}
          titleZh="產業主題"
          titleEn="Top Ranked Themes"
          limit={5}
          variant="compact"
        />
        <section className="industrial-supply-loading">
          <BilingualLabel zh="載入供應鏈" en="Loading Industrial Supply Chain Snapshot" inline />
          <p>Waiting for graph-backed industrial intelligence for the selected theme.</p>
        </section>
      </main>
    );
  }

  if (activeTab === "risk") {
    const riskItems = (selectedAggregate?.supply_chain.risks ?? []).map((risk) => ({
      label: risk.risk_type,
      value: risk.value,
      state: risk.risk_type,
    }));
    const selectedRisk = riskItems.find((item) => item.label === selectedRiskFactor) ?? riskItems[0] ?? { label: "Risk", value: null, state: "unavailable" };
    return (
      <main id="theme-research" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
        <Header activeTab={activeTab} loading={data.loading} />
        <VisualStrip
          items={riskItems}
        />
        <div className="grid gap-7 xl:grid-cols-[minmax(0,1fr)_340px]">
          <TerminalPanel eyebrow="憸券 Risk" title={`${selectedThemeName} Heat`}>
            <RiskStressGrid items={riskItems} selected={selectedRisk.label} onSelect={setSelectedRiskFactor} onPreview={onPreview} onPreviewEnd={onPreviewEnd} onContext={onContext} onDrilldown={onDrilldown} />
            <div id="theme-risk" tabIndex={-1} className="mt-5 outline-none">
              <MarketTable
                columns={RISK_TABLE_COLUMNS}
                header={
                  <>
                  <MarketCell>Risk</MarketCell>
                  <NumericCell>Score</NumericCell>
                  <MarketCell>State</MarketCell>
                  </>
                }
              >
                {riskItems.filter((item) => item.label === selectedRisk.label).map((item) => (
                  <MarketRow
                    key={item.label}
                    columns={RISK_TABLE_COLUMNS}
                    onClick={() => onContext?.({ kind: "risk", name: item.label, subject: selectedThemeName, value: finite(item.value), meta: item.state ?? "Risk factor" })}
                    onDoubleClick={() => onDrilldown?.({ kind: "risk", name: item.label, subject: selectedThemeName, value: finite(item.value), meta: item.state ?? "Risk factor" })}
                    onPreview={() => onPreview?.({ kind: "risk", name: item.label, subject: selectedThemeName, value: finite(item.value), meta: item.state ?? "Risk factor" })}
                    onPreviewEnd={onPreviewEnd}
                  >
                    <MarketCell className="text-sm font-semibold text-[var(--theme-text)]">{item.label}</MarketCell>
                    <NumericCell className={`text-sm font-semibold ${classForScore(item.value)}`}>{formatScore(item.value)}</NumericCell>
                    <MarketCell className="text-sm text-[var(--theme-muted)]">{item.state ?? "state"}</MarketCell>
                  </MarketRow>
                ))}
              </MarketTable>
            </div>
          </TerminalPanel>
          <TerminalPanel eyebrow="?窗 Context" title="Risk Note">
            <details className="interaction-detail">
              <summary>{selectedRisk.label} reasoning</summary>
              <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{forecast?.explanation || narrative?.explanation || "Risk monitor is using live lightweight theme factors while forecast context warms."}</p>
            </details>
          </TerminalPanel>
        </div>
      </main>
    );
  }

  if (activeTab === "stocks") {
    return (
      <main id="theme-research" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
        <Header activeTab={activeTab} loading={data.loading} />
        <TerminalPanel eyebrow="? Drilldown" title={`${selectedThemeName} Beneficiary Stocks`}>
          <div className="mb-4">
            <MetricStrip
              items={[
                { label: "Leadership", value: themeScore(activeTheme) },
                { label: "Flow", value: themeFlow(activeTheme) },
                { label: "Momentum", value: themeMomentum(activeTheme) },
                { label: "Forecast", value: forecast?.forecast_score },
              ]}
            />
          </div>
          <div id="theme-stocks" tabIndex={-1} className="outline-none">
            <BeneficiaryList rows={leaders} onPreview={onPreview} onPreviewEnd={onPreviewEnd} onContext={onContext} onTickerSelect={onTickerSelect} />
          </div>
        </TerminalPanel>
      </main>
    );
  }

  const institutionalRankIndex = phase10ThemeRows.findIndex((theme) => (
    sameTheme(theme.theme_id, selectedThemeName) || sameTheme(theme.theme, selectedThemeName)
  ));
  const institutionalRank = institutionalRankIndex >= 0 ? institutionalRankIndex + 1 : null;
  return (
    <main id="theme-research" tabIndex={-1} className="institutional-theme-workspace text-[var(--theme-text)] outline-none ring-0">
      <section className="theme-research-surface">
        <ThemeInvestmentWorkflow
          aggregate={selectedAggregate}
          rank={institutionalRank}
          totalThemes={phase10ThemeRows.length}
          conviction={selectedScore?.conviction_level ?? null}
          selectedTheme={selectedThemeId}
          registryThemes={registryThemes}
          onThemeSelect={selectTheme}
        />
      </section>
      <section className="theme-validation-surface" aria-label="Theme research validation surface">
        <span>Persisted evidence only</span>
        <span>No inferred graph edges</span>
        <span>Unavailable remains unavailable</span>
      </section>
    </main>
  );

  /* Legacy Phase 10 command composition retained only as a secondary drilldown reference.
  const displayAiThemes = phase10ThemeRows.slice(0, 8);
  const discoveryBeneficiaryRows = selectedAggregate?.beneficiaries.top_beneficiaries ?? [];
  const discoveryBeneficiaries = aggregateBeneficiaryLeaders(selectedAggregate);
  const discoveryRoles = aggregateRoles(selectedAggregate);
  const potential = scoreRecordValue(selectedScore, "ai_potential_score");
  const probability = finite(selectedAggregate?.discovery.confidence_score) ?? finite(selectedAggregate?.discovery.emerging_score);
  const confidenceValue = finite(selectedAggregate?.lifecycle.lifecycle_confidence) ?? finite(selectedAggregate?.discovery.confidence_score) ?? finite(selectedScore?.score_components?.confidence_score);
  const stageLabel = stageForPhase10(selectedScore, selectedAggregate);
  const keyInsight = selectedAggregate?.discovery.brief?.why_now
    ?? selectedScore?.why_high_score
    ?? selectedScore?.conviction_reason
    ?? "Discovery context unavailable.";
  const keyDrivers = [
    ...(selectedScore?.major_strengths ?? []),
    ...((selectedAggregate?.catalysts.top_catalysts ?? []).map((item) => item.name ?? item.catalyst_name ?? "").filter(Boolean)),
  ].slice(0, 5);
  const catalystItems = selectedAggregate?.catalysts.top_catalysts ?? [];
  const riskNotes = [
    ...(selectedScore?.major_risks ?? []),
    ...((selectedAggregate?.catalysts.key_blockers ?? []).map((item) => item.description ?? item.name ?? item.catalyst_name ?? "").filter(Boolean)),
    ...(selectedAggregate?.bottlenecks.primary_bottleneck?.description ? [selectedAggregate.bottlenecks.primary_bottleneck.description] : []),
  ].slice(0, 5);
  const portfolioRows = selectedAggregate?.portfolio_context.portfolios ?? [];
  const hasSupplyChainVisual = discoveryRoles.length >= 2 && discoveryBeneficiaryRows.length > 0;
  const hasCatalystVisual = catalystItems.length >= 2;
  const selectedRankIndex = phase10ThemeRows.findIndex((theme) => sameTheme(theme.theme_id, selectedThemeName) || sameTheme(theme.theme, selectedThemeName));
  const selectedRank = selectedRankIndex >= 0 ? selectedRankIndex + 1 : null;
  const portfolioWeight = portfolioRows.reduce<number | null>((highest, row) => {
    const weight = finite(row.weight);
    if (weight === null) return highest;
    return highest === null ? weight : Math.max(highest, weight);
  }, null);
  return (
    <main id="theme-research" tabIndex={-1} className="ai-discovery text-[var(--theme-text)] outline-none ring-0">
      <header className="ai-discovery-header"><div><BilingualLabel zh="AI 頞典?Ｙ揣" en="AI Trend Discovery Engine" inline /><span className="ai-beta">BETA</span><p>AI 憭雁摨行????湛??葫銝???賜??潛?頞典銝駁?嚗???撅銝?瘜Ｘ??瑟???/p></div><span>Last update: {hydratedTime} 繚 PARTIAL LIVE</span></header>
      <ThemeInvestmentWorkflow aggregate={selectedAggregate} rank={selectedRank} totalThemes={phase10ThemeRows.length} conviction={selectedScore?.conviction_level ?? null} selectedTheme={selectedThemeId} registryThemes={registryThemes} onThemeSelect={selectTheme} />
      <div className="ai-discovery-top">
        <section className="ai-panel ai-hero">
          <div className="ai-panel-head"><BilingualLabel zh="AI ?撘琿?皜砌蜓憿? en="Top AI Predicted Theme" inline /><button type="button" onClick={() => onContext?.({ kind: "theme", name: selectedThemeName, value: potential, meta: "AI predicted theme" })}>?亦?摰?? ??/button></div>
          <div className="ai-hero-main"><div className="ai-theme-art"><span /><span /><span /></div><div><strong>{selectedThemeName}</strong><small>{selectedScore?.conviction_level ?? "Unrated"}</small><em>{stageLabel}</em></div><div className="ai-potential"><span>AI 瞏?閰?<br /><small>AI Potential Score</small></span><strong>{formatScore(potential, 0)}</strong><i>/100</i></div><div className="ai-hero-trend"><span>頞典撘瑕漲頞典<br /><small>Trend Strength</small></span><SparklineMini values={[scoreRecordValue(selectedScore, "research_importance"), scoreRecordValue(selectedScore, "allocation_readiness"), scoreRecordValue(selectedScore, "risk_adjusted_score"), potential]} /></div></div>
          <div className="ai-hero-kpis">{[["?璈?","Probability",probability],["靽∪?摨?,"Confidence",confidenceValue],["??蝒?,"Time Window",selectedAggregate?.lifecycle.time_window || selectedAggregate?.discovery.time_window || "--"],["?挾","Stage",stageLabel]].map(([zh,en,value])=><div key={String(en)}><BilingualLabel zh={String(zh)} en={String(en)} inline /><strong>{typeof value === "number" ? formatScore(value,0) : value}</strong></div>)}</div>
          <div className="ai-metric-row">{[["AI Potential",potential],["Research Importance",scoreRecordValue(selectedScore,"research_importance")],["Allocation Readiness",scoreRecordValue(selectedScore,"allocation_readiness")],["Risk Adjusted",scoreRecordValue(selectedScore,"risk_adjusted_score")],["Catalyst Score",finite(selectedAggregate?.discovery.catalyst_score)],["Crowding Proxy",finite(selectedAggregate?.discovery.crowding_proxy)]].map(([label,value])=><div key={String(label)} data-empty={finite(value)===null}><span>{label}</span><strong>{finite(value)===null ? "No data" : formatScore(value,0)}</strong></div>)}</div>
          <div className="ai-insight"><BilingualLabel zh="?詨?瘣?" en="Key Insight" inline /><p>{keyInsight}</p><BilingualLabel zh="?撽???" en="Key Drivers" inline /><div>{keyDrivers.length > 0 ? keyDrivers.map((item)=><span key={item}>{item}</span>) : <span>Catalyst drivers unavailable</span>}</div></div>
        </section>
        <section className="ai-panel ai-ranking"><div className="ai-panel-head"><BilingualLabel zh="AI 頞典?刻??璁? en="AI Theme Ranking" inline /><span>{displayAiThemes.length ? "Phase 10 scores" : "No score rows"}</span></div><div className="ai-ranking-head"><span>#</span><span>銝駁? Theme</span><span>AI 閰?</span><span>頞典撘瑕漲 Trend</span><span>?挾</span><span>Conviction</span></div>{displayAiThemes.length > 0 ? displayAiThemes.map((theme,index)=><button key={theme.theme_id || theme.theme} type="button" data-selected={sameTheme(theme.theme,selectedThemeName)||sameTheme(theme.theme_id,selectedThemeName)} className="ai-ranking-row" onClick={()=>selectTheme(theme.theme)} onMouseEnter={()=>onPreview?.({kind:"theme",name:theme.theme,value:scoreRecordValue(theme,"ai_potential_score"),meta:theme.conviction_level})} onMouseLeave={onPreviewEnd}><b>{index+1}</b><strong>{theme.theme}</strong><em>{formatScore(theme.ai_potential_score,0)}</em><SparklineMini values={[theme.research_importance,theme.allocation_readiness,theme.risk_adjusted_score,theme.ai_potential_score]} /><span>{stageForPhase10(theme, sameTheme(theme.theme, selectedThemeName) ? selectedAggregate : null)}</span><i>{theme.conviction_level}</i></button>) : <div className="p-4 text-sm text-[var(--theme-muted)]">No Phase 10 theme scores are stored yet.</div>}</section>
        <aside className="ai-side-stack"><ThemeIntelligenceSummary aggregate={selectedAggregate} rank={selectedRank} totalThemes={phase10ThemeRows.length} portfolioWeight={portfolioWeight} /></aside>
      </div>
      {hasSupplyChainVisual && <div className="ai-discovery-middle"><section className="ai-panel ai-supply-map"><div className="ai-panel-head"><BilingualLabel zh="銝駁?靘???? en={`Supply Chain Map 繚 ${selectedThemeName}`} inline /></div><div className="ai-supply-lanes">{discoveryRoles.slice(0,5).map((role,index)=><button key={role.role} type="button" onClick={()=>onContext?.({kind:"supply",name:selectedThemeName,subject:role.role,value:(role.leaders?.length??0)*20,meta:"Aggregate beneficiary role",intelligence:{beneficiaries:(role.leaders??[]).map(item=>item.ticker)}})}><strong>{role.role}</strong><span>{(role.leaders??[]).slice(0,3).map(item=><i key={item.ticker}><TickerLogo ticker={item.ticker}/>{item.ticker}</i>)}</span>{index<Math.min(4, discoveryRoles.length-1)&&<b>??/b>}</button>)}</div></section><section className="ai-panel ai-top-beneficiaries"><div className="ai-panel-head"><BilingualLabel zh="????? en="Top Beneficiaries" inline /></div><div className="ai-beneficiary-head"><span>Ticker</span><span>?砍</span><span>Score</span><span>Role</span><span>Bucket</span></div>{discoveryBeneficiaryRows.slice(0,6).map((row,index)=><button key={`${row.ticker}-${row.beneficiary_type ?? row.role ?? index}`} type="button" onClick={()=>onContext?.({kind:"stock",symbol:row.ticker,label:row.company_name||row.company||row.ticker,value:finite(row.allocation_score ?? row.beneficiary_score),meta:"Aggregate beneficiary"})} onDoubleClick={()=>onTickerSelect?.(row.ticker)}><strong>{row.ticker}</strong><span>{row.company_name||row.company||row.ticker}</span><em>{formatScore(row.allocation_score??row.beneficiary_score,0)}</em><span>{row.beneficiary_type ?? row.role ?? "--"}</span><i>{row.allocation_bucket ?? "--"}</i></button>)}</section></div>}
      {hasCatalystVisual && <section className="ai-panel ai-deep-dive"><div className="ai-panel-head"><BilingualLabel zh="銝駁?閰單???" en="Theme Deep Dive" inline /></div><div className="ai-deep-grid"><div><BilingualLabel zh="?砍???" en="Catalysts" inline /><div className="theme-catalyst-bars">{catalystItems.slice(0,5).map((item)=><span key={`${item.name ?? item.catalyst_name}-${item.source}`}><b style={{height:`${Math.max(18,(finite(item.catalyst_strength ?? item.impact_score) ?? 0)/2)}px`}} /><i>{formatScore(item.catalyst_strength ?? item.impact_score,0)}</i><small>{item.name ?? item.catalyst_name ?? item.catalyst_type ?? "Catalyst"}</small></span>)}</div></div><div><BilingualLabel zh="AI 頞典??頠? en="Trend Timeline" inline /><div className="ai-timeline"><span data-active><b>{selectedAggregate?.lifecycle.lifecycle_stage ?? "--"}</b><i>Current stage</i></span><span><b>{selectedAggregate?.lifecycle.expected_next_stage ?? "--"}</b><i>Expected next</i></span><span><b>{selectedAggregate?.lifecycle.time_window || selectedAggregate?.discovery.time_window || "--"}</b><i>Time window</i></span></div></div><div><BilingualLabel zh="憸券???? en="Risk & Challenges" inline /><ul className="ai-risks">{riskNotes.length > 0 ? riskNotes.map(item=><li key={item}>??{item}</li>) : <li>No risk evidence available.</li>}</ul></div><div><BilingualLabel zh="AI 銝駁?靽∪?摨? en="Confidence Score" inline /><div className="ai-confidence"><strong>{formatScore(confidenceValue,0)}</strong><span>/100<br/>{selectedScore?.conviction_level ?? "Unrated"}</span></div></div><div><BilingualLabel zh="撣?蝑撱箄降" en="Strategy Suggestions" inline /><div className="ai-strategy">{portfolioRows.length > 0 ? portfolioRows.slice(0,3).map((row)=><span key={row.portfolio_type}><b>{row.portfolio_name}</b><em>{formatScore(row.weight,1)}%</em></span>) : <span><b>No portfolio allocation available</b><em>--</em></span>}</div></div></div></section>}
    </main>
  );
  */
}

function Header({ activeTab, loading }: { activeTab: ThemeResearchTab; loading: boolean }) {
  const copy = VIEW_COPY[activeTab];
  const Icon = copy.icon;
  return (
    <div className="mb-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <Icon className="mt-1 shrink-0 text-[var(--theme-warning)]" size={22} />
          <div className="min-w-0">
            <p className="terminal-micro-label text-[var(--theme-warning)]">{copy.eyebrow}</p>
            <h1 className="terminal-page-title mt-1 text-[var(--theme-text)]">{copy.title}</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--theme-muted)]">{copy.description}</p>
          </div>
        </div>
        <div className="border-l border-[var(--theme-divider)] pl-3 text-[11px] font-medium uppercase tracking-wide text-[var(--theme-muted)]">
          {loading ? "Hydrating research tape" : "partial live research"}
        </div>
      </div>
    </div>
  );
}

