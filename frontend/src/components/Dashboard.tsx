"use client";

import React, { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { BrainCircuit, Briefcase, LineChart, Loader2, Menu, Radar, Settings, Trash2, X } from "lucide-react";
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

const AlphaQuantPage = React.lazy(() => import("./AlphaQuantPage"));
const SectorRotationPanel = React.lazy(() => import("./SectorRotationPanel"));
const StockAnalysisWorkspace = React.lazy(() => import("./StockAnalysisWorkspace"));
const ThemeForecastAIPage = React.lazy(() => import("./ThemeForecastAIPage"));
const ThemeIntelligenceDashboard = React.lazy(() => import("./ThemeIntelligenceDashboard"));

type ActiveTab = TerminalModuleId;
const WATCHLIST_KEY = "watchlist";
const WATCHLIST_SCHEMA_VERSION = "stock_v6";

function moduleIcon(iconKey: TerminalIconKey, size: number): React.ReactNode {
  if (iconKey === "briefcase") return <Briefcase size={size} />;
  if (iconKey === "brain") return <BrainCircuit size={size} />;
  if (iconKey === "line-chart") return <LineChart size={size} />;
  return <Radar size={size} />;
}

const navItems = enabledTerminalModules;
const mobileMenuItems: Array<{ id: ActiveTab | "settings"; label: string; icon: React.ReactNode }> = [
  ...enabledTerminalModules.map((module) => ({
    id: module.id,
    label: module.id === "theme-intelligence" ? uiText.navigation.themeIntelligence : module.title,
    icon: moduleIcon(module.iconKey, 17),
  })),
  { id: "settings", label: uiText.navigation.settings, icon: <Settings size={17} /> },
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
    <main id="portfolio-watchlist" tabIndex={-1} className="miji-page p-5 text-[#E6EDF3] outline-none ring-0">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Portfolio Command Center</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Institutional Watchlist</h1>
          <p className="mt-2 text-sm text-[#9BA7B4]">Editable hedge fund watchlist with live price, bubble risk, and HMM trend state.</p>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-amber-200">Focus: {selectedPortfolioView}</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Refreshing portfolio tape</div>}
      </div>

      {watchlist.length === 0 ? (
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-10 text-center shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <p className="text-lg font-semibold text-[#E6EDF3]">No symbols in watchlist</p>
          <p className="mt-2 text-sm text-[#9BA7B4]">Use the global search bar and Add to Watchlist to build your portfolio.</p>
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
                className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md"
              >
                <div className="mb-5 flex items-start justify-between gap-3">
                  <button onClick={() => onTickerSelect(ticker)} className="min-w-0 text-left">
                    <span className="font-mono text-3xl font-semibold tracking-wide text-[#E6EDF3]">{ticker}</span>
                    <p className="mt-1 truncate text-sm text-[#9BA7B4]">{sanitizeCompanyName(stock?.company_name) || "Loading market data"}</p>
                  </button>
                  <button
                    onClick={() => onRemove(ticker)}
                    className="rounded-lg border border-[#2B313C] p-2 text-[#9BA7B4] transition hover:border-rose-300/30 hover:text-rose-300"
                    aria-label={`Remove ${ticker}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                <button onClick={() => onTickerSelect(ticker)} className="w-full text-left">
                  <div className="miji-card-metrics grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Price</p>
                      <p className="mt-1 font-mono text-lg font-semibold text-[#E6EDF3]">{price !== null ? `$${price.toFixed(2)}` : "--"}</p>
                    </div>
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Daily</p>
                      <p className={change === null ? "mt-1 font-mono text-lg font-semibold text-[#9BA7B4]" : change >= 0 ? "mt-1 font-mono text-lg font-semibold text-emerald-300" : "mt-1 font-mono text-lg font-semibold text-rose-300"}>
                        {change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "--"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Bubble</p>
                      <p className={bubble >= 70 ? "mt-1 font-mono text-lg font-semibold text-rose-300" : bubble <= 40 ? "mt-1 font-mono text-lg font-semibold text-emerald-300" : "mt-1 font-mono text-lg font-semibold text-amber-200"}>
                        {bubble.toFixed(0)}
                      </p>
                    </div>
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">AI Trend</p>
                      <p className={trend === "Bearish" ? "mt-1 text-sm font-semibold text-rose-300" : trend === "Bullish" ? "mt-1 text-sm font-semibold text-emerald-300" : "mt-1 text-sm font-semibold text-[#C9D1D9]"}>
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

  return (
    <div className="miji-shell flex h-[100dvh] w-full flex-col overflow-hidden bg-[#0A0C10] text-[#E6EDF3]">
      <header className="miji-header shrink-0 border-b border-[#2B313C] bg-[#0A0C10]">
        <MarketTickerMarquee />
        <nav className="miji-header-nav flex min-h-16 flex-wrap items-center justify-between gap-4 overflow-x-hidden px-5 py-3">
          <div className="miji-header-brand flex shrink-0 items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-2xl border border-amber-400/20 bg-[#161B22] text-amber-200" style={{ width: 40, height: 40, display: "flex" }}>
              <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }} />
            </div>
            <div>
              <div className="miji-header-title text-lg font-semibold uppercase tracking-wide text-[#E6EDF3]">MIJI TERMINAL</div>
              <div className="miji-header-subtitle text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Institutional Trading Workstation</div>
            </div>
          </div>
          <div className="miji-mobile-actions hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="rounded-xl border border-[#2B313C] bg-[#111318] p-2 text-[#E6EDF3]"
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <button
              type="button"
              className="rounded-xl border border-[#2B313C] bg-[#111318] p-2 text-[#9BA7B4]"
              aria-label="Settings"
            >
              <Settings size={19} />
            </button>
          </div>
          <div className="miji-mobile-tabbar flex w-full flex-nowrap items-center justify-start gap-2 overflow-x-auto pb-1 md:w-auto md:flex-1 md:flex-wrap md:justify-center md:overflow-visible md:pb-0">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveModule(item.id)}
                className={`flex h-10 items-center gap-2 rounded-2xl border px-3 text-sm font-medium transition ${
                  activeTab === item.id
                    ? "bg-[#1D2430] border border-amber-400/20 text-[#E6EDF3]"
                    : "border-[#2B313C] bg-[#111318] text-[#9BA7B4] hover:bg-[#151922]"
                }`}
              >
                {moduleIcon(item.iconKey, 16)}
                {item.title}
              </button>
            ))}
          </div>
          <div className="miji-header-actions flex w-full min-w-0 items-center gap-3 md:w-auto">
            <GlobalStockSearch onSelect={openStock} onSelectResult={openSearchResult} onAddToWatchlist={addToWatchlist} />
            <div className="hidden min-w-0 rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2 text-[11px] text-[#9BA7B4] md:block">
              <span className="font-semibold uppercase tracking-wide text-[#6E7681]">Workspace</span>
              <span className="ml-2 font-mono text-[#C9D1D9]">{activeContextLabel}</span>
            </div>
            <div className="hidden rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2 font-mono text-[11px] text-[#9BA7B4] lg:block" suppressHydrationWarning>
              {timestamp ? `LIVE ${timestamp}` : "LIVE"}
            </div>
          </div>
        </nav>
      </header>

      <div className="miji-content min-h-0 flex-1 overflow-y-auto bg-[#0A0C10]">
        {activeTab === "theme-intelligence" && <div id="theme-intelligence" tabIndex={-1} className="outline-none ring-0"><ThemeIntelligenceDashboard onTickerSelect={openStock} /></div>}
        {activeTab === "theme-forecast" && <div id="theme-forecast" tabIndex={-1} className="outline-none ring-0"><ThemeForecastAIPage /></div>}
        {activeTab === "portfolio" && <div id="portfolio"><PortfolioHome watchlist={watchlist} onTickerSelect={openStock} onRemove={removeFromWatchlist} /></div>}
        {activeTab === "alpha-quant" && <div id="alpha-quant" tabIndex={-1} className="outline-none ring-0"><AlphaQuantPage onTickerSelect={openStock} /></div>}
        {activeTab === "market-intel" && <div id="sector-rotation" tabIndex={-1} className="outline-none ring-0"><SectorRotationPanel onTickerSelect={openStock} /></div>}
        {activeTab === "stock-analysis" && <div id="stock-analysis" tabIndex={-1} className="outline-none ring-0 animate-[mijiResultGlow_1.4s_ease-out_1]"><StockAnalysisWorkspace /></div>}
      </div>
      {mobileMenuOpen && (
        <motion.div
          className="miji-mobile-drawer fixed inset-0 z-[100] bg-[#0A0C10]/55 backdrop-blur-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setMobileMenuOpen(false)}
        >
          <motion.aside
            className="h-full w-[84vw] max-w-[340px] border-r border-[#2B313C] bg-[#0A0C10]/98 p-4 shadow-[0_24px_64px_rgba(0,0,0,0.5)]"
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
                <div className="h-9 w-9 overflow-hidden rounded-xl border border-amber-400/20 bg-[#161B22]">
                  <img src="/miji-cat-mark.png" alt="Miji Quant" className="h-full w-full object-contain" />
                </div>
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">MIJI</p>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Mobile Terminal</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-xl border border-[#2B313C] bg-[#111318] p-2 text-[#9BA7B4]"
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
                      ? "border-amber-400/20 bg-[#1D2430] text-[#E6EDF3]"
                      : "border-[#2B313C] bg-[#111318] text-[#9BA7B4]"
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
