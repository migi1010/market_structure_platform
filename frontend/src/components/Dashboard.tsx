"use client";

import React, { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Bell,
  Bookmark,
  BrainCircuit,
  Briefcase,
  LayoutDashboard,
  LineChart,
  Loader2,
  Menu,
  Newspaper,
  PanelsTopLeft,
  Radar,
  RefreshCw,
  ScanSearch,
  Search,
  Settings2,
  Star,
  Trash2,
  Waves,
  X,
} from "lucide-react";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { uiText } from "@/lib/i18n";
import { WorkspaceProvider, useWorkspace } from "@/context/WorkspaceContext";
import { enabledTerminalModules, getTerminalModule, type TerminalIconKey, type TerminalModuleId } from "@/modules/terminalModules";

import { fetchStockAnalysis, warmupQuantEngine } from "@/services/stockApi";
import type { SearchResult, StockAnalysis, WorkspaceAction } from "@/types/stock";
import AppErrorBoundary from "./AppErrorBoundary";
import GlobalStockSearch from "./GlobalStockSearch";
import LoadingScreen from "./LoadingScreen";
import MarketTickerMarquee from "./MarketTickerMarquee";
import { TerminalRail, TerminalRailButton } from "./terminal";

const AlphaQuantPage = React.lazy(() => import("./AlphaQuantPage"));
const SectorRotationPanel = React.lazy(() => import("./SectorRotationPanel"));
const StockAnalysisWorkspace = React.lazy(() => import("./StockAnalysisWorkspace"));
const ThemeForecastAIPage = React.lazy(() => import("./ThemeForecastAIPage"));
const ThemeIntelligenceDashboard = React.lazy(() => import("./ThemeIntelligenceDashboard"));

type ActiveTab = TerminalModuleId;
const WATCHLIST_KEY = "watchlist";
const WATCHLIST_SCHEMA_VERSION = "stock_v6";

function moduleIcon(iconKey: TerminalIconKey, size: number): React.ReactNode {
  if (iconKey === "activity") return <Activity size={size} />;
  if (iconKey === "bell") return <Bell size={size} />;
  if (iconKey === "bookmark") return <Bookmark size={size} />;
  if (iconKey === "brain-circuit") return <BrainCircuit size={size} />;
  if (iconKey === "briefcase") return <Briefcase size={size} />;
  if (iconKey === "layout-dashboard") return <LayoutDashboard size={size} />;
  if (iconKey === "line-chart") return <LineChart size={size} />;
  if (iconKey === "newspaper") return <Newspaper size={size} />;
  if (iconKey === "panels-top-left") return <PanelsTopLeft size={size} />;
  if (iconKey === "refresh-cw") return <RefreshCw size={size} />;
  if (iconKey === "scan-search") return <ScanSearch size={size} />;
  if (iconKey === "search") return <Search size={size} />;
  if (iconKey === "settings-2") return <Settings2 size={size} />;
  if (iconKey === "star") return <Star size={size} />;
  if (iconKey === "waves") return <Waves size={size} />;
  return <Radar size={size} />;
}

const navItems = enabledTerminalModules;
const mobileMenuItems: Array<{ id: ActiveTab | "settings"; label: string; icon: React.ReactNode }> = [
  ...enabledTerminalModules.map((module) => ({
    id: module.id,
    label: module.id === "theme-intelligence" ? uiText.navigation.themeIntelligence : module.title,
    icon: moduleIcon(module.iconKey, 17),
  })),
  { id: "settings", label: uiText.navigation.settings, icon: <Settings2 size={17} /> },
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
      contextPayload: { theme, label: `Open ${theme}` },
    };
  }
  if (type === "sector") {
    const sector = normalizeSectorName(result);
    return {
      actionType: "open_sector",
      target_tab: "market-intel",
      focusTarget: "sector-drilldown",
      openMode: "replace",
      contextPayload: { sector, label: `Open ${sector} Rotation` },
    };
  }
  const targetModule = getTerminalModule(result.target_tab);
  if (targetModule && targetModule.workspaceType !== "stock") {
    return {
      actionType: targetModule.id === "alpha-quant" ? "open_alpha" : targetModule.id === "portfolio" ? "open_portfolio" : "open_module",
      target_tab: targetModule.id,
      focusTarget: targetModule.id,
      openMode: "replace",
      contextPayload: { label: result.label ?? targetModule.title },
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
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[var(--theme-text)]">Institutional Watchlist</h1>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Editable hedge fund watchlist with live price, bubble risk, and HMM trend state.</p>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Focus: {selectedPortfolioView}</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[var(--theme-muted)]"><Loader2 className="animate-spin" size={16} /> Refreshing portfolio tape</div>}
      </div>

      {watchlist.length === 0 ? (
        <div className="miji-card rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel)] p-10 text-center shadow-sm">
          <p className="text-lg font-semibold text-[var(--theme-text)]">No symbols in watchlist</p>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Use the global search bar and Add to Watchlist to build your portfolio.</p>
        </div>
      ) : (
        <div className="miji-card-grid grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {watchlist.map((ticker) => {
            const stock = snapshots?.[ticker];
            const bubble = stock?.bubble_analysis_data?.bubble_index ?? 0;
            const change = typeof stock?.change_percent === "number" ? stock.change_percent : null;
            const price = typeof stock?.price === "number" && stock.price > 0 ? stock.price : null;
            const trend = stock?.hmm_prediction?.available === false ? "Calibrating" : stock?.hmm_prediction?.predicted_trend ?? "Loading";
            return (
              <motion.div
                key={ticker}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className="miji-card rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel)] p-5 shadow-sm"
              >
                <div className="mb-5 flex items-start justify-between gap-3">
                  <button onClick={() => onTickerSelect(ticker)} className="min-w-0 text-left">
                    <span className="font-mono text-3xl font-semibold tracking-wide text-[var(--theme-text)]">{ticker}</span>
                    <p className="mt-1 truncate text-sm text-[var(--theme-muted)]">{sanitizeCompanyName(stock?.company_name) || "Loading market data"}</p>
                  </button>
                  <button
                    onClick={() => onRemove(ticker)}
                    className="rounded-lg border border-[var(--theme-border)] p-2 text-[var(--theme-muted)] transition hover:border-[var(--theme-bearish)] hover:text-[var(--theme-bearish)]"
                    aria-label={`Remove ${ticker}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                <button onClick={() => onTickerSelect(ticker)} className="w-full text-left">
                  <div className="miji-card-metrics grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Price</p>
                      <p className="mt-1 font-mono text-lg font-semibold text-[var(--theme-text)]">{price !== null ? `$${price.toFixed(2)}` : "--"}</p>
                    </div>
                    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Daily</p>
                      <p className={change === null ? "mt-1 font-mono text-lg font-semibold text-[var(--theme-muted)]" : change >= 0 ? "mt-1 font-mono text-lg font-semibold text-[var(--theme-bullish)]" : "mt-1 font-mono text-lg font-semibold text-[var(--theme-bearish)]"}>
                        {change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "--"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Bubble</p>
                      <p className={bubble >= 70 ? "mt-1 font-mono text-lg font-semibold text-[var(--theme-bearish)]" : bubble <= 40 ? "mt-1 font-mono text-lg font-semibold text-[var(--theme-bullish)]" : "mt-1 font-mono text-lg font-semibold text-[var(--theme-warning)]"}>
                        {bubble.toFixed(0)}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">AI Trend</p>
                      <p className={trend === "Bearish" ? "mt-1 text-sm font-semibold text-[var(--theme-bearish)]" : trend === "Bullish" ? "mt-1 text-sm font-semibold text-[var(--theme-bullish)]" : "mt-1 text-sm font-semibold text-[var(--theme-text-secondary)]"}>
                        {trend}
                      </p>
                    </div>
                  </div>
                </button>
              </motion.div>
            );
          })}
        </div>
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
    selectedAlphaView,
    selectedPortfolioView,
    lastWorkspaceAction,
    setActiveModule,
    dispatchWorkspaceAction,
  } = useWorkspace();
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [watchlistReady, setWatchlistReady] = useState(false);
  const [timestamp, setTimestamp] = useState("");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
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
    setTimestamp(new Date().toLocaleString("en-US", { hour12: false }));
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
        focusElement(action.focusTarget === "theme-detail" ? "theme-detail" : "theme-intelligence");
        return;
      }
      if (action.focusTarget === "sector-drilldown") {
        focusElement("sector-drilldown");
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

  useEffect(() => {
    if (!lastWorkspaceAction || lastWorkspaceAction.target_tab !== activeTab) return;
    focusWorkspaceAction(lastWorkspaceAction);
  }, [activeTab, focusWorkspaceAction, lastWorkspaceAction]);

  const openStock = useCallback((ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    runWorkspaceAction({
      actionType: "open_stock",
      target_tab: "stock-analysis",
      focusTarget: "stock-workspace",
      openMode: "replace",
      contextPayload: { ticker: symbol, label: `Open ${symbol} Analysis` },
    });
  }, [runWorkspaceAction]);

  const openSearchResult = useCallback((result: SearchResult) => {
    runWorkspaceAction(workspaceActionFromResult(result));
  }, [runWorkspaceAction]);

  const selectMobileMenu = useCallback((id: ActiveTab | "settings") => {
    if (id !== "settings") setActiveModule(id);
    setMobileMenuOpen(false);
  }, [setActiveModule]);

  const actionContextLabel = lastWorkspaceAction?.target_tab === activeTab ? lastWorkspaceAction.contextPayload?.label : null;
  const activeContextLabel =
    actionContextLabel
    ?? (activeTab === "stock-analysis" ? selectedTicker
      : activeTab === "theme-intelligence" ? selectedTheme || "Theme Intelligence"
        : activeTab === "theme-forecast" ? "Theme Forecast AI"
          : activeTab === "market-intel" ? selectedSector
            : activeTab === "alpha-quant" ? selectedAlphaView
              : selectedPortfolioView);

  const railItems = navItems.filter((item) => item.railGroup !== "bottom");
  const railBottomItems = navItems.filter((item) => item.railGroup === "bottom");

  return (
    <div className="miji-shell terminal-shell flex h-[100dvh] w-full overflow-hidden">
      <TerminalRail
        brand={
          <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)]">
            <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" />
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
            <TerminalRailButton label="?" secondaryLabel="Alerts" icon={<Bell size={18} />} />
            <TerminalRailButton label="閮剖?" secondaryLabel="Settings" icon={<Settings2 size={18} />} />
          </>
        }
      />
      <div className="terminal-main flex min-w-0 flex-1 flex-col overflow-hidden">
      <header className="miji-header shrink-0 border-b border-[var(--theme-border)] bg-[var(--theme-bg)]">
        <MarketTickerMarquee />
        <nav className="miji-header-nav flex min-h-16 flex-wrap items-center justify-between gap-4 overflow-x-hidden px-5 py-3">
          <div className="miji-header-brand flex shrink-0 items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] text-[var(--theme-highlight)] md:hidden" style={{ width: 40, height: 40, display: "flex" }}>
              <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }} />
            </div>
            <div>
              <div className="miji-header-title text-lg font-semibold uppercase tracking-wide text-[var(--theme-text)]">MIJI TERMINAL</div>
              <div className="miji-header-subtitle text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Institutional AI Research Terminal</div>
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
            <button
              type="button"
              className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] p-2 text-[var(--theme-muted)]"
              aria-label="Settings"
            >
              <Settings2 size={19} />
            </button>
          </div>
          <div className="miji-header-actions flex w-full min-w-0 items-center gap-3 md:w-auto">
            <GlobalStockSearch onSelect={openStock} onSelectResult={openSearchResult} onAddToWatchlist={addToWatchlist} />
            <div className="hidden min-w-0 rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] px-3 py-2 text-[11px] text-[var(--theme-muted)] md:block">
              <span className="font-semibold uppercase tracking-wide text-[var(--theme-accent)]">撌乩?? Workspace</span>
              <span className="ml-2 font-mono text-[var(--theme-text-secondary)]">{activeContextLabel}</span>
            </div>
            <div className="hidden rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] px-3 py-2 font-mono text-[11px] text-[var(--theme-muted)] lg:block" suppressHydrationWarning>
              {timestamp ? `LIVE ${timestamp}` : "LIVE"}
            </div>
          </div>
        </nav>
      </header>

      <div className="miji-content min-h-0 flex-1 overflow-y-auto bg-[var(--theme-bg)]">
        {activeTab === "theme-intelligence" && <div id="theme-intelligence" tabIndex={-1} className="outline-none ring-0"><ThemeIntelligenceDashboard onTickerSelect={openStock} /></div>}
        {activeTab === "theme-forecast" && <div id="theme-forecast" tabIndex={-1} className="outline-none ring-0"><ThemeForecastAIPage /></div>}
        {activeTab === "portfolio" && <div id="portfolio"><PortfolioHome watchlist={watchlist} onTickerSelect={openStock} onRemove={removeFromWatchlist} /></div>}
        {activeTab === "alpha-quant" && <div id="alpha-quant" tabIndex={-1} className="outline-none ring-0"><AlphaQuantPage onTickerSelect={openStock} /></div>}
        {activeTab === "market-intel" && <div id="sector-rotation" tabIndex={-1} className="outline-none ring-0"><SectorRotationPanel onTickerSelect={openStock} /></div>}
        {activeTab === "stock-analysis" && <div id="stock-analysis" tabIndex={-1} className="outline-none ring-0 animate-[mijiResultGlow_1.4s_ease-out_1]"><StockAnalysisWorkspace /></div>}
      </div>
      {mobileMenuOpen && (
        <motion.div
          className="miji-mobile-drawer fixed inset-0 z-[100] bg-[var(--theme-bg)]/55 "
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setMobileMenuOpen(false)}
        >
          <motion.aside
            className="h-full w-[84vw] max-w-[340px] border-r border-[var(--theme-border)] bg-[var(--theme-bg)]/98 p-4 shadow-sm"
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
                <div className="h-9 w-9 overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel)]">
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
                className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-2 text-[var(--theme-muted)]"
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
                  className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm font-semibold transition ${
                    activeTab === item.id
                      ? "border-[var(--theme-border)] bg-[var(--theme-panel-hover)] text-[var(--theme-text)]"
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
