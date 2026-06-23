"use client";

import React, { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  Bell,
  Bookmark,
  BrainCircuit,
  Briefcase,
  LayoutDashboard,
  LineChart,
  Loader2,
  Menu,
  Network,
  PanelsTopLeft,
  Radar,
  RefreshCw,
  ScanSearch,
  Search,
  Settings2,
  ShieldAlert,
  Star,
  Trash2,
  Waves,
  X,
} from "lucide-react";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { createDockState, createDrilldownAction, inferDrilldownTargetFromSearch, type DrilldownDockState, type DrilldownTarget } from "@/lib/drilldown";
import { useHydratedTime } from "@/lib/hydration";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { enabledTerminalModules, getEnabledTerminalModule, getTerminalModule, primaryTerminalModules, type TerminalIconKey, type TerminalModuleId } from "@/modules/terminalModules";

import { fetchStockAnalysis, fetchThemeIntelligence, normalizeThemeIntelligenceId, resolveCanonicalThemeIdentity, traceThemeIdentity, warmupQuantEngine } from "@/services/stockApi";
import type { SearchResult, StockAnalysis, ThemeAggregateResponse, WorkspaceAction } from "@/types/stock";
import AppErrorBoundary from "./AppErrorBoundary";
import GlobalStockSearch from "./GlobalStockSearch";
import LoadingScreen from "./LoadingScreen";
import MarketTickerMarquee from "./MarketTickerMarquee";
import { ChangeCell, ContextDock, DrilldownTrigger, HeatStrip, MarketCell, MarketRow, MarketTable, NumericCell, StatusDot, TerminalRail, TerminalRailButton, TickerCell, TickerLogo } from "./terminal";

const AlphaQuantPage = React.lazy(() => import("./AlphaQuantPage"));
const StockAnalysisWorkspace = React.lazy(() => import("./StockAnalysisWorkspace"));
const ThemeResearchPage = React.lazy(() => import("./ThemeResearchPage"));
const ThemeScoutPage = React.lazy(() => import("./ThemeScoutPage"));

type ActiveTab = TerminalModuleId;
const WATCHLIST_KEY = "watchlist";
const WATCHLIST_SCHEMA_VERSION = "stock_v6";
const WATCHLIST_ROW_COLUMNS = "minmax(150px,1.3fr) 88px 82px 68px 44px minmax(110px,0.8fr) 36px";

function moduleIcon(iconKey: TerminalIconKey, size: number): React.ReactNode {
  if (iconKey === "activity") return <Activity size={size} />;
  if (iconKey === "bell") return <Bell size={size} />;
  if (iconKey === "bookmark") return <Bookmark size={size} />;
  if (iconKey === "brain-circuit") return <BrainCircuit size={size} />;
  if (iconKey === "briefcase") return <Briefcase size={size} />;
  if (iconKey === "bar-chart-3") return <BarChart3 size={size} />;
  if (iconKey === "layout-dashboard") return <LayoutDashboard size={size} />;
  if (iconKey === "line-chart") return <LineChart size={size} />;
  if (iconKey === "network") return <Network size={size} />;
  if (iconKey === "panels-top-left") return <PanelsTopLeft size={size} />;
  if (iconKey === "refresh-cw") return <RefreshCw size={size} />;
  if (iconKey === "scan-search") return <ScanSearch size={size} />;
  if (iconKey === "search") return <Search size={size} />;
  if (iconKey === "settings-2") return <Settings2 size={size} />;
  if (iconKey === "shield-alert") return <ShieldAlert size={size} />;
  if (iconKey === "star") return <Star size={size} />;
  if (iconKey === "waves") return <Waves size={size} />;
  return <Radar size={size} />;
}

const navItems = primaryTerminalModules;
const mobileMenuItems: Array<{ id: ActiveTab; label: string; icon: React.ReactNode }> = [
  ...primaryTerminalModules.map((module) => ({
    id: module.id,
    label: module.title,
    icon: moduleIcon(module.iconKey, 17),
  })),
];

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
}

function normalizeThemeName(result: SearchResult): string {
  return (result.theme ?? result.label ?? result.name ?? result.symbol).trim();
}

function normalizeSectorName(result: SearchResult): string {
  return (result.sector ?? result.label ?? result.name ?? result.symbol).trim();
}

function isThemeResearchModule(id: TerminalModuleId): boolean {
  return ["theme-intelligence", "theme-forecast", "market-intel", "theme-stocks", "theme-supply-chain", "theme-risk"].includes(id);
}

function themeSubjectFromTarget(target: DrilldownTarget): string | null {
  if (target.kind === "theme") return target.subject ?? target.name ?? target.label ?? null;
  if (target.kind === "supply" || target.kind === "supply_chain") return target.name ?? target.subject ?? null;
  if (target.kind === "risk") return target.subject ?? target.name ?? null;
  return null;
}

function workspaceActionFromResult(result: SearchResult): WorkspaceAction {
  if (result.workspaceAction) return result.workspaceAction;
  const type = result.type?.toLowerCase() ?? "equity";
  if (type === "theme") {
    const theme = normalizeThemeName(result);
    return {
      actionType: "open_theme",
      target_tab: "theme-intelligence",
      focusTarget: "theme-detail",
      openMode: "replace",
      contextPayload: { theme, themeView: "command", label: `Open ${theme}` },
    };
  }
  if (type === "sector") {
    const sector = normalizeSectorName(result);
    return {
      actionType: "open_sector",
      target_tab: "market-intel",
      focusTarget: "theme-rotation",
      openMode: "replace",
      contextPayload: { sector, themeView: "rotation", label: `Open ${sector} Rotation` },
    };
  }
  const targetModule = getTerminalModule(result.target_tab);
  if (targetModule?.id === "theme-forecast") {
    return {
      actionType: "open_module",
      target_tab: "theme-forecast",
      focusTarget: "theme-forecast",
      openMode: "replace",
      contextPayload: { themeView: "forecast", label: result.label ?? targetModule.title },
    };
  }
  if (targetModule?.id === "market-intel") {
    return {
      actionType: "open_module",
      target_tab: "market-intel",
      focusTarget: "theme-rotation",
      openMode: "replace",
      contextPayload: { themeView: "rotation", label: result.label ?? targetModule.title },
    };
  }
  if (targetModule && targetModule.workspaceType !== "stock") {
    const enabledModule = getEnabledTerminalModule(targetModule.id);
    if (!enabledModule) {
      return {
        actionType: "open_module",
        target_tab: "theme-intelligence",
        focusTarget: "theme-workspace",
        openMode: "replace",
        contextPayload: { themeView: "command", label: result.label ?? targetModule.title },
      };
    }
    return {
      actionType: enabledModule.id === "alpha-quant" ? "open_alpha" : enabledModule.id === "portfolio" ? "open_portfolio" : enabledModule.workspaceType === "sector" ? "open_sector" : "open_module",
      target_tab: enabledModule.id,
      focusTarget: isThemeResearchModule(enabledModule.id) ? enabledModule.id : enabledModule.id,
      openMode: "replace",
      contextPayload: { label: result.label ?? enabledModule.title },
    };
  }
  const ticker = normalizeSymbol(result.ticker ?? result.symbol);
  return {
    actionType: "open_stock",
    target_tab: "stock-analysis",
    focusTarget: "stock-workspace",
    openMode: "replace",
    contextPayload: { ticker, label: `Open ${ticker} Analysis` },
  };
}

function DockContent({
  dock,
  onDrilldown,
  themeIntelligence,
  themeIntelligenceLoading,
}: {
  dock: DrilldownDockState;
  onDrilldown: (target: DrilldownTarget) => void;
  themeIntelligence?: ThemeAggregateResponse | null;
  themeIntelligenceLoading?: boolean;
}) {
  const value = typeof dock.value === "number" && Number.isFinite(dock.value) ? dock.value.toFixed(0) : "--";
  const intelligence = dock.intelligence;
  const score = themeIntelligence?.score;
  const catalysts = themeIntelligence?.catalysts.top_catalysts ?? [];
  const bottleneck = themeIntelligence?.bottlenecks.primary_bottleneck;
  const beneficiaries = themeIntelligence?.beneficiaries.top_beneficiaries ?? [];
  const controllers = themeIntelligence?.beneficiaries.controllers ?? [];
  const portfolios = themeIntelligence?.portfolio_context.portfolios ?? [];
  const supplyLayers = themeIntelligence?.supply_chain.layers ?? [];
  const risks = themeIntelligence?.supply_chain.risks ?? [];
  const discovery = themeIntelligence?.discovery;
  return (
    <div className="context-intelligence">
      <div className="context-intelligence-summary">
        <div className="flex items-center justify-between gap-3">
          <span className="terminal-micro-label">Signal</span>
          <span className="font-mono text-xl font-semibold text-[var(--theme-text)]">{value}</span>
        </div>
        <HeatStrip value={dock.value} className="mt-3 w-full" />
        {intelligence?.summary && <p className="mt-3 text-xs leading-5 text-[var(--theme-text-secondary)]">{intelligence.summary}</p>}
      </div>
      {intelligence && (
        <>
          <div className="context-intelligence-grid">
            <div><span>Flow</span><strong>{typeof intelligence.flow === "number" ? intelligence.flow.toFixed(0) : "--"}</strong></div>
            <div><span>Risk</span><strong>{typeof intelligence.risk === "number" ? intelligence.risk.toFixed(0) : "--"}</strong></div>
          </div>
          <DockTags label="Exposure" values={intelligence.exposure} />
          <DockTags label="Beneficiaries" values={intelligence.beneficiaries} />
          <DockTags label="Related Themes" values={intelligence.relatedThemes} />
        </>
      )}
      {(themeIntelligenceLoading || themeIntelligence) && (
        <div className="context-intelligence-section">
          <p className="terminal-micro-label mb-2">Theme Intelligence</p>
          {themeIntelligenceLoading && !themeIntelligence ? (
            <p className="text-xs leading-5 text-[var(--theme-muted)]">Loading aggregate intelligence...</p>
          ) : (
            <>
              <div className="context-intelligence-grid">
                <div><span>AI Score</span><strong>{typeof score?.ai_potential_score === "number" ? score.ai_potential_score.toFixed(0) : "--"}</strong></div>
                <div><span>Lifecycle</span><strong>{themeIntelligence?.lifecycle.lifecycle_stage ?? "--"}</strong></div>
              </div>
              <DockTags label="Catalysts" values={catalysts.map((item) => item.name ?? item.catalyst_name ?? "").filter(Boolean)} />
              <DockTags label="Bottleneck" values={bottleneck ? [bottleneck.name ?? bottleneck.bottleneck_name ?? bottleneck.type ?? bottleneck.bottleneck_type ?? "Stored bottleneck"] : []} />
              <DockTags label="Discovery Detail" values={[
                typeof discovery?.brief?.why_now === "string" ? discovery.brief.why_now : "",
                ...(discovery?.brief?.signals ?? []),
              ].filter(Boolean)} />
              <DockTags label="Controllers" values={controllers.map((item) => item.ticker).filter(Boolean)} />
              <DockTags label="Beneficiaries" values={beneficiaries.map((item) => item.ticker).filter(Boolean)} />
              <DockTags label="Supply Chain" values={supplyLayers.map((item) => `${item.layer_name}: ${item.entities.map((entity) => entity.ticker).join(", ")}`).filter(Boolean)} />
              <DockTags label="Portfolio Context" values={portfolios.map((item) => item.portfolio_name).filter(Boolean)} />
              <DockTags label="Risk Summary" values={risks.map((item) => `${item.risk_type}: ${typeof item.value === "number" ? item.value.toFixed(0) : "--"}`)} />
            </>
          )}
        </div>
      )}
      <div>
        <p className="terminal-micro-label mb-2">Drilldown</p>
        <DrilldownTrigger label="Stock workspace" meta="Chart" onClick={() => onDrilldown({ kind: "stock", symbol: dock.entity.type === "stock" ? dock.entity.id : dock.subject || dock.target.symbol || "NVDA" })} />
        <DrilldownTrigger label="Theme overlap" meta="Themes" onClick={() => onDrilldown({ kind: "theme", name: dock.subject || dock.title })} />
        <DrilldownTrigger label="Supply exposure" meta="Dependency" onClick={() => onDrilldown({ kind: "supply", name: dock.subject || dock.title })} />
        <DrilldownTrigger label="Risk overlay" meta="Risk" onClick={() => onDrilldown({ kind: "risk", name: "Bubble Risk", subject: dock.subject || dock.title })} />
      </div>
      {!intelligence?.summary && <p className="text-xs leading-5 text-[var(--theme-muted)]">
        Context layer for {dock.title}. Deeper entity intelligence uses the current workspace payload and opens without a full page refresh.
      </p>}
    </div>
  );
}

function DockTags({ label, values }: { label: string; values?: string[] }) {
  if (!values?.length) return null;
  const uniqueValues = Array.from(new Set(values.filter(Boolean)));
  return (
    <div className="context-intelligence-section">
      <p className="terminal-micro-label mb-2">{label}</p>
      <div className="context-intelligence-tags">{uniqueValues.slice(0, 6).map((value) => <span key={value}>{value}</span>)}</div>
    </div>
  );
}

function readWatchlist(): string[] {
  try {
    const raw = localStorage.getItem(WATCHLIST_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || (parsed as { schema_version?: string }).schema_version !== WATCHLIST_SCHEMA_VERSION) {
      localStorage.removeItem(WATCHLIST_KEY);
      return [];
    }
    const data = (parsed as { data?: unknown }).data;
    if (!Array.isArray(data)) {
      localStorage.removeItem(WATCHLIST_KEY);
      return [];
    }
    return Array.from(new Set(data.filter((item): item is string => typeof item === "string").map(normalizeSymbol).filter(Boolean)));
  } catch {
    localStorage.removeItem(WATCHLIST_KEY);
    return [];
  }
}

function writeWatchlist(watchlist: string[]): void {
  try {
    const data = Array.from(new Set(watchlist.map(normalizeSymbol).filter(Boolean)));
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify({ schema_version: WATCHLIST_SCHEMA_VERSION, data }));
  } catch {
    // Watchlist persistence is best effort.
  }
}

function PortfolioHome({
  watchlist,
  onTickerSelect,
  onRemove,
}: {
  watchlist: string[];
  onTickerSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}) {
  const { selectedPortfolioView } = useWorkspace();
  const [snapshots, setSnapshots] = useState<Record<string, StockAnalysis>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (watchlist.length === 0) return;
      setLoading(true);
      const entries = await Promise.all(
        watchlist.map(async (ticker) => {
          try {
            return [ticker, await fetchStockAnalysis(ticker)] as const;
          } catch {
            return [ticker, null] as const;
          }
        }),
      );
      if (!cancelled) {
        setSnapshots(
          entries.reduce<Record<string, StockAnalysis>>((acc, [ticker, value]) => {
            if (value) acc[ticker] = value;
            return acc;
          }, {}),
        );
        setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [watchlist]);

  return (
    <main id="portfolio-watchlist" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Portfolio Command Center</p>
          <h1 className="mt-1 text-[28px] font-semibold leading-tight text-[var(--theme-text)]">持倉觀察 Watchlist</h1>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Price, move, bubble, trend.</p>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Focus: {selectedPortfolioView}</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[var(--theme-muted)]"><Loader2 className="animate-spin" size={16} /> Refreshing portfolio tape</div>}
      </div>

      {watchlist.length === 0 ? (
        <div className="terminal-panel p-8 text-center">
          <p className="text-lg font-semibold text-[var(--theme-text)]">No symbols in watchlist</p>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Use the global search bar and Add to Watchlist to build your portfolio.</p>
        </div>
      ) : (
        <MarketTable
          columns={WATCHLIST_ROW_COLUMNS}
          className="terminal-panel p-2"
          header={
            <>
              <MarketCell>股票</MarketCell>
              <NumericCell>Price</NumericCell>
              <NumericCell>Daily</NumericCell>
              <NumericCell>Bubble</NumericCell>
              <MarketCell>Heat</MarketCell>
              <MarketCell>Trend</MarketCell>
              <MarketCell>{null}</MarketCell>
            </>
          }
        >
          {watchlist.map((ticker) => {
            const stock = snapshots?.[ticker];
            const bubble = stock?.bubble_analysis_data?.bubble_index ?? 0;
            const change = typeof stock?.change_percent === "number" ? stock.change_percent : null;
            const price = typeof stock?.price === "number" && stock.price > 0 ? stock.price : null;
            const trend = stock?.hmm_prediction?.available === false ? "Calibrating" : stock?.hmm_prediction?.predicted_trend ?? "Loading";
            return (
              <MarketRow
                key={ticker}
                columns={WATCHLIST_ROW_COLUMNS}
              >
                <TickerCell>
                  <button onClick={() => onTickerSelect(ticker)} className="min-w-0 text-left">
                    <span className="flex items-center gap-2"><TickerLogo ticker={ticker} /><span className="truncate">{ticker}</span></span>
                    <span className="mt-0.5 block truncate text-[11px] font-normal text-[var(--theme-muted)]">{sanitizeCompanyName(stock?.company_name) || "Loading market data"}</span>
                  </button>
                </TickerCell>
                <NumericCell className="text-sm font-semibold text-[var(--theme-text)]">{price !== null ? `$${price.toFixed(2)}` : "--"}</NumericCell>
                <ChangeCell value={change} className="text-sm font-semibold">
                  {change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "--"}
                </ChangeCell>
                <NumericCell className={bubble >= 70 ? "text-sm font-semibold text-[var(--theme-bearish)]" : bubble <= 40 ? "text-sm font-semibold text-[var(--theme-bullish)]" : "text-sm font-semibold text-[var(--theme-warning)]"}>
                  {bubble.toFixed(0)}
                </NumericCell>
                <MarketCell><HeatStrip value={bubble} /></MarketCell>
                <MarketCell><StatusDot state={trend} label={trend} /></MarketCell>
                <MarketCell className="text-right">
                  <button
                    onClick={() => onRemove(ticker)}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-[6px] text-[var(--theme-muted)] transition hover:bg-[rgba(242,54,69,0.08)] hover:text-[var(--theme-bearish)]"
                    aria-label={`Remove ${ticker}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </MarketCell>
              </MarketRow>
            );
          })}
        </MarketTable>
      )}
    </main>
  );
}

function DashboardApp() {
  const {
    activeModule: activeTab,
    selectedTicker,
    selectedTheme,
    selectedSector,
    selectedThemeView,
    selectedAlphaView,
    selectedPortfolioView,
    lastWorkspaceAction,
    scrollPositions,
    setActiveModule,
    setWorkspaceScrollPosition,
    dispatchWorkspaceAction,
  } = useWorkspace();
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [watchlistReady, setWatchlistReady] = useState(false);
  const timestamp = useHydratedTime({ locale: "en-US" });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [contextDock, setContextDock] = useState<DrilldownDockState | null>(null);
  const [contextDockExpanded, setContextDockExpanded] = useState(false);
  const [contextThemeIntelligence, setContextThemeIntelligence] = useState<ThemeAggregateResponse | null>(null);
  const [contextThemeIntelligenceLoading, setContextThemeIntelligenceLoading] = useState(false);
  const [previewDock, setPreviewDock] = useState<DrilldownDockState | null>(null);
  const contextThemeAbortRef = useRef<AbortController | null>(null);
  const contextThemeRequestRef = useRef("");
  const previousActiveTabRef = useRef(activeTab);
  const contentRef = useRef<HTMLDivElement | null>(null);
  const scrollPositionsRef = useRef(scrollPositions);
  const touchStartXRef = useRef<number | null>(null);

  useEffect(() => {
    setWatchlist(readWatchlist());
    setWatchlistReady(true);
  }, []);

  useEffect(() => {
    if (!watchlistReady) return;
    writeWatchlist(watchlist);
  }, [watchlist, watchlistReady]);

  useEffect(() => {
    void warmupQuantEngine();
  }, []);

  const addToWatchlist = useCallback((ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    if (!symbol) return;
    setWatchlist((prev) => Array.from(new Set([...prev, symbol])));
  }, []);

  const removeFromWatchlist = useCallback((ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    setWatchlist((prev) => prev.filter((item) => item !== symbol));
  }, []);

  const focusWorkspaceAction = useCallback((action: WorkspaceAction) => {
    window.setTimeout(() => {
      const focusElement = (id: string) => {
        const element = document.getElementById(id);
        element?.scrollIntoView({ behavior: "smooth", block: "start" });
        element?.focus({ preventScroll: true });
      };
      if (action.focusTarget === "stock-workspace") {
        focusElement("stock-analysis");
        return;
      }
      if (action.focusTarget === "theme-detail" || action.focusTarget === "theme-workspace") {
        focusElement(action.focusTarget === "theme-detail" ? "theme-detail" : "theme-research");
        return;
      }
      if (action.focusTarget === "theme-forecast") {
        focusElement("theme-forecast");
        return;
      }
      if (action.focusTarget === "theme-rotation" || action.focusTarget === "sector-drilldown") {
        focusElement("theme-rotation");
        return;
      }
      if (action.focusTarget === "theme-supply-chain") {
        focusElement("theme-supply-chain");
        return;
      }
      if (action.focusTarget === "theme-stocks") {
        focusElement("theme-stocks");
        return;
      }
      if (action.focusTarget === "theme-risk") {
        focusElement("theme-risk");
        return;
      }
      if (action.focusTarget === "alpha-momentum" || action.focusTarget === "alpha-workspace") {
        focusElement(action.focusTarget === "alpha-momentum" ? "alpha-momentum" : "alpha-quant");
        return;
      }
      if (action.focusTarget === "portfolio-watchlist") {
        focusElement("portfolio-watchlist");
      }
    }, 120);
  }, []);

  const runWorkspaceAction = useCallback((action: WorkspaceAction) => {
    dispatchWorkspaceAction(action);
    setMobileMenuOpen(false);
  }, [dispatchWorkspaceAction]);

  const abortContextThemeFetch = useCallback(() => {
    contextThemeAbortRef.current?.abort();
    contextThemeAbortRef.current = null;
    contextThemeRequestRef.current = "";
    setContextThemeIntelligence(null);
    setContextThemeIntelligenceLoading(false);
  }, []);

  const openContextDock = useCallback((target: DrilldownTarget) => {
    setContextDock(createDockState(target));
    setContextDockExpanded(false);
    setPreviewDock(null);
  }, []);

  useEffect(() => {
    const dockTheme = contextDock ? themeSubjectFromTarget(contextDock.target) : null;
    const themeSubject = dockTheme ?? (isThemeResearchModule(activeTab) ? selectedTheme : null);
    if (!themeSubject) {
      abortContextThemeFetch();
      return undefined;
    }
    const normalized = normalizeThemeIntelligenceId(themeSubject);
    if (
      contextThemeRequestRef.current === normalized
      && contextThemeIntelligence
      && normalizeThemeIntelligenceId(contextThemeIntelligence.theme_id) === normalized
    ) {
      return undefined;
    }
    if (
      contextThemeRequestRef.current === normalized
      && contextThemeAbortRef.current
      && !contextThemeAbortRef.current.signal.aborted
    ) {
      return undefined;
    }
    contextThemeAbortRef.current?.abort();
    contextThemeRequestRef.current = normalized;
    setContextThemeIntelligence(null);
    const controller = new AbortController();
    contextThemeAbortRef.current = controller;
    setContextThemeIntelligenceLoading(true);
    fetchThemeIntelligence(themeSubject, { signal: controller.signal })
      .then((payload) => {
        if (!controller.signal.aborted && contextThemeRequestRef.current === normalized) {
          setContextThemeIntelligence(payload);
          setContextThemeIntelligenceLoading(false);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted && !(error instanceof DOMException && error.name === "AbortError")) {
          setContextThemeIntelligence(null);
          setContextThemeIntelligenceLoading(false);
        }
      });
    return undefined;
  }, [abortContextThemeFetch, activeTab, contextDock, contextThemeIntelligence, selectedTheme]);

  useEffect(() => () => {
    contextThemeAbortRef.current?.abort();
  }, []);

  const previewContext = useCallback((target: DrilldownTarget) => {
    setPreviewDock(createDockState(target));
  }, []);

  const clearPreviewContext = useCallback(() => {
    setPreviewDock(null);
  }, []);

  const runDrilldown = useCallback((target: DrilldownTarget) => {
    const drilldown = createDrilldownAction(target);
    abortContextThemeFetch();
    setContextDock(drilldown.dock ?? null);
    setPreviewDock(null);
    runWorkspaceAction(drilldown.action);
  }, [abortContextThemeFetch, runWorkspaceAction]);

  useEffect(() => {
    if (!lastWorkspaceAction || lastWorkspaceAction.target_tab !== activeTab) return;
    focusWorkspaceAction(lastWorkspaceAction);
  }, [activeTab, focusWorkspaceAction, lastWorkspaceAction]);

  useEffect(() => {
    scrollPositionsRef.current = scrollPositions;
  }, [scrollPositions]);

  useEffect(() => {
    const element = contentRef.current;
    if (!element) return;
    window.requestAnimationFrame(() => {
      element.scrollTop = scrollPositionsRef.current[activeTab] ?? 0;
    });
  }, [activeTab]);

  useEffect(() => {
    const element = contentRef.current;
    if (!element) return undefined;
    let frame = 0;
    const saveScrollPosition = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        setWorkspaceScrollPosition(activeTab, element.scrollTop);
      });
    };
    element.addEventListener("scroll", saveScrollPosition, { passive: true });
    return () => {
      window.cancelAnimationFrame(frame);
      element.removeEventListener("scroll", saveScrollPosition);
    };
  }, [activeTab, setWorkspaceScrollPosition]);

  useEffect(() => {
    if (previousActiveTabRef.current === activeTab) return;
    const leavingThemeResearch = !isThemeResearchModule(activeTab);
    previousActiveTabRef.current = activeTab;
    if (leavingThemeResearch) abortContextThemeFetch();
    setContextDock(null);
    setContextDockExpanded(false);
    setPreviewDock(null);
  }, [abortContextThemeFetch, activeTab]);

  useEffect(() => {
    const closeDockOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      abortContextThemeFetch();
      setContextDock(null);
      setContextDockExpanded(false);
      setPreviewDock(null);
    };
    window.addEventListener("keydown", closeDockOnEscape);
    return () => window.removeEventListener("keydown", closeDockOnEscape);
  }, [abortContextThemeFetch]);

  const openStock = useCallback((ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    runDrilldown({ kind: "stock", symbol });
  }, [runDrilldown]);

  const openSearchResult = useCallback((result: SearchResult) => {
    previewContext(inferDrilldownTargetFromSearch(result));
  }, [previewContext]);

  const previewSearchResult = useCallback((result: SearchResult) => {
    previewContext(inferDrilldownTargetFromSearch(result));
  }, [previewContext]);

  const drilldownSearchResult = useCallback((result: SearchResult) => {
    const target = inferDrilldownTargetFromSearch(result);
    const drilldown = createDrilldownAction(target);
    const action = result.workspaceAction ?? drilldown.action;
    const rawThemeName = action.contextPayload?.theme ?? result.theme ?? "";
    if (rawThemeName) {
      const identity = resolveCanonicalThemeIdentity(rawThemeName);
      traceThemeIdentity("search_navigation", identity.rawName, identity.themeId, null);
    }
    abortContextThemeFetch();
    setContextDock(drilldown.dock ?? null);
    runWorkspaceAction(action);
  }, [abortContextThemeFetch, runWorkspaceAction]);

  const selectMobileMenu = useCallback((id: ActiveTab) => {
    setActiveModule(id);
    setMobileMenuOpen(false);
  }, [setActiveModule]);

  const actionContextLabel = lastWorkspaceAction?.target_tab === activeTab ? lastWorkspaceAction.contextPayload?.label : null;
  const activeContextLabel =
    actionContextLabel
    ?? (activeTab === "stock-analysis" ? selectedTicker
        : activeTab === "theme-intelligence" ? `${selectedTheme || selectedSector || "Theme Research"} / ${selectedThemeView}`
          : isThemeResearchModule(activeTab) ? `${selectedTheme || selectedSector || "Theme Research"} / ${selectedThemeView}`
        : activeTab === "alpha-quant" ? selectedAlphaView
          : selectedPortfolioView);

  const railItems = navItems.filter((item) => item.railGroup !== "bottom");
  const railBottomItems = navItems.filter((item) => item.railGroup === "bottom");

  return (
    <div className="miji-shell terminal-shell flex h-[100dvh] w-full overflow-hidden">
      <TerminalRail
        brand={
          <div className="flex items-center gap-3 px-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-[6px] bg-transparent">
              <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" />
            </div>
            <div className="terminal-rail-label min-w-0 overflow-hidden whitespace-nowrap">
              <p className="truncate text-sm font-semibold text-[var(--theme-text)]">MIJI</p>
              <p className="truncate text-[10px] font-medium text-[var(--theme-muted)]">Market Intelligence</p>
            </div>
          </div>
        }
        middle={railItems.map((item) => (
          <TerminalRailButton
            key={item.id}
            label={item.labelZh}
            secondaryLabel={item.labelEn}
            icon={moduleIcon(item.iconKey, 18)}
            active={activeTab === item.id}
            onClick={() => setActiveModule(item.id)}
          />
        ))}
        bottom={
          <>
            {railBottomItems.map((item) => (
              <TerminalRailButton
                key={item.id}
                label={item.labelZh}
                secondaryLabel={item.labelEn}
                icon={moduleIcon(item.iconKey, 18)}
                active={activeTab === item.id}
                onClick={() => setActiveModule(item.id)}
              />
            ))}
          </>
        }
      />
      <div className="terminal-main flex min-w-0 flex-1 flex-col overflow-hidden">
      <header className="miji-header shrink-0 border-b border-[var(--theme-divider)] bg-[var(--theme-bg)]">
        <MarketTickerMarquee />
        <nav className="miji-header-nav flex min-h-12 flex-wrap items-center justify-between gap-3 overflow-x-hidden px-4 py-2">
          <div className="miji-header-brand flex shrink-0 items-center gap-4 md:hidden">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] text-[var(--theme-highlight)] md:hidden" style={{ width: 40, height: 40, display: "flex" }}>
              <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }} />
            </div>
            <div>
              <div className="miji-header-title text-lg font-semibold text-[var(--theme-text)]">MIJI Terminal</div>
              <div className="miji-header-subtitle text-[10px] font-semibold text-[var(--theme-muted)]">Institutional Research Terminal</div>
            </div>
          </div>
          <div className="miji-mobile-actions hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] p-2 text-[var(--theme-text)]"
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
          </div>
          <div className="miji-header-actions flex w-full min-w-0 items-center gap-4 md:w-auto">
            <GlobalStockSearch onSelect={openStock} onPreviewResult={previewSearchResult} onPreviewEnd={clearPreviewContext} onSelectResult={openSearchResult} onDrilldownResult={drilldownSearchResult} onAddToWatchlist={addToWatchlist} />
            <div className="hidden min-w-0 items-baseline gap-2 text-[11px] text-[var(--theme-muted)] md:flex">
              <span className="font-medium text-[var(--theme-muted)]">Workspace</span>
              <span className="font-mono text-[var(--theme-text-secondary)]">{activeContextLabel}</span>
            </div>
            <div className="hidden font-mono text-[11px] text-[var(--theme-muted)] lg:block">
              LIVE {timestamp}
            </div>
          </div>
        </nav>
      </header>

      <div ref={contentRef} className="miji-content min-h-0 flex-1 overflow-y-auto bg-[var(--theme-bg)]">
        {isThemeResearchModule(activeTab) && <div id="theme-intelligence" tabIndex={-1} className="outline-none ring-0"><ThemeResearchPage activeSelection={contextDock?.target ?? null} aggregateIntelligence={contextThemeIntelligence} onTickerSelect={openStock} onPreview={previewContext} onPreviewEnd={clearPreviewContext} onContext={openContextDock} onDrilldown={runDrilldown} /></div>}
        {activeTab === "theme-scout" && <div id="theme-scout" tabIndex={-1} className="outline-none ring-0"><ThemeScoutPage onPreview={previewContext} onPreviewEnd={clearPreviewContext} onContext={openContextDock} onDrilldown={runDrilldown} /></div>}
        {activeTab === "portfolio" && <div id="portfolio"><PortfolioHome watchlist={watchlist} onTickerSelect={openStock} onRemove={removeFromWatchlist} /></div>}
        {activeTab === "alpha-quant" && <div id="alpha-quant" tabIndex={-1} className="outline-none ring-0"><AlphaQuantPage onTickerSelect={openStock} onPreview={previewContext} onPreviewEnd={clearPreviewContext} onContext={openContextDock} onDrilldown={runDrilldown} /></div>}
        {activeTab === "stock-analysis" && <div id="stock-analysis" tabIndex={-1} className="outline-none ring-0"><StockAnalysisWorkspace activeSelection={contextDock?.target ?? null} onPreview={previewContext} onPreviewEnd={clearPreviewContext} onContext={openContextDock} onDrilldown={runDrilldown} /></div>}
      </div>
      <ContextDock
        open={contextDock !== null}
        collapsed={!contextDockExpanded}
        title={contextDock?.title ?? "Context"}
        subtitle={contextDock?.subtitle ?? contextDock?.kind}
        onToggle={() => setContextDockExpanded((expanded) => !expanded)}
        onClose={() => { abortContextThemeFetch(); setContextDock(null); setContextDockExpanded(false); }}
        className="fixed right-0 top-[86px] z-[90] hidden h-[calc(100dvh-86px)] w-[340px] lg:block"
      >
        {contextDock && <DockContent dock={contextDock} onDrilldown={runDrilldown} themeIntelligence={contextThemeIntelligence} themeIntelligenceLoading={contextThemeIntelligenceLoading} />}
      </ContextDock>
      {previewDock && !contextDock && (
        <div className="fixed bottom-4 right-4 z-[85] hidden w-[280px] border-l-2 border-[var(--theme-warning)] bg-[var(--theme-bg)] px-3 py-2 text-xs text-[var(--theme-text-secondary)] lg:block">
          <span className="terminal-micro-label">預覽 Preview</span>
          <span className="mt-1 block truncate font-semibold text-[var(--theme-text)]">{previewDock.title}</span>
          <span className="mt-0.5 block truncate text-[var(--theme-muted)]">{previewDock.subtitle ?? previewDock.kind}</span>
        </div>
      )}
      {mobileMenuOpen && (
        <motion.div
          className="miji-mobile-drawer fixed inset-0 z-[100] bg-[var(--theme-bg)]/55 "
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setMobileMenuOpen(false)}
        >
          <motion.aside
            className="h-full w-[84vw] max-w-[340px] border-r border-[var(--theme-divider)] bg-[var(--theme-bg)] p-4"
            initial={{ x: -24, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            onClick={(event) => event.stopPropagation()}
            onTouchStart={(event) => {
              touchStartXRef.current = event.touches?.[0]?.clientX ?? null;
            }}
            onTouchEnd={(event) => {
              const start = touchStartXRef.current;
              const end = event.changedTouches?.[0]?.clientX ?? null;
              if (start !== null && end !== null && end - start < -48) setMobileMenuOpen(false);
              touchStartXRef.current = null;
            }}
          >
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 overflow-hidden rounded-[6px]">
                  <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" />
                </div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">MIJI</p>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Mobile Terminal</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-[6px] border border-[var(--theme-divider)] bg-transparent p-2 text-[var(--theme-muted)]"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>
            <div className="space-y-2">
              {mobileMenuItems.map((item, index) => (
                <button
                  key={`${item.id}-${index}`}
                  type="button"
                  onClick={() => selectMobileMenu(item.id)}
                  className={`flex w-full items-center gap-3 rounded-[6px] border px-4 py-3 text-left text-sm font-semibold transition ${
                    activeTab === item.id
                      ? "border-[var(--theme-border-strong)] bg-[var(--theme-surface-elevated)] text-[var(--theme-text)]"
                      : "border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] text-[var(--theme-muted)]"
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </motion.aside>
        </motion.div>
      )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <AppErrorBoundary>
      <Suspense fallback={<LoadingScreen />}>
        <WorkspaceProvider>
          <DashboardApp />
        </WorkspaceProvider>
      </Suspense>
    </AppErrorBoundary>
  );
}
