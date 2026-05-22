"use client";

import React, { Suspense, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Briefcase, LineChart, Loader2, Radar, ShieldAlert, Trash2 } from "lucide-react";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { fetchStockAnalysis } from "@/services/stockApi";
import type { StockAnalysis } from "@/types/stock";
import AppErrorBoundary from "./AppErrorBoundary";
import BubbleDiagnosisPage from "./BubbleDiagnosisPage";
import GlobalStockSearch from "./GlobalStockSearch";
import LoadingScreen from "./LoadingScreen";
import SectorRotationPanel from "./SectorRotationPanel";
import StockAnalysisWorkspace from "./StockAnalysisWorkspace";

type ActiveTab = "portfolio" | "market-intel" | "bubble-diagnosis" | "stock-analysis";

const navItems: Array<{ id: ActiveTab; label: string; icon: React.ReactNode }> = [
  { id: "portfolio", label: "Portfolio", icon: <Briefcase size={16} /> },
  { id: "market-intel", label: "Sector Rotation", icon: <Radar size={16} /> },
  { id: "bubble-diagnosis", label: "Bubble Diagnosis", icon: <ShieldAlert size={16} /> },
  { id: "stock-analysis", label: "Stock Analysis", icon: <LineChart size={16} /> },
];

function normalizeSymbol(symbol: string): string {
  return symbol.trim().toUpperCase();
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
    <main className="p-5 text-[#E6EDF3]">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Portfolio Command Center</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Institutional Watchlist</h1>
          <p className="mt-2 text-sm text-[#9BA7B4]">Editable hedge fund watchlist with live price, bubble risk, and HMM trend state.</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Refreshing portfolio tape</div>}
      </div>

      {watchlist.length === 0 ? (
        <div className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-10 text-center shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <p className="text-lg font-semibold text-[#E6EDF3]">No symbols in watchlist</p>
          <p className="mt-2 text-sm text-[#9BA7B4]">Use the global search bar and Add to Watchlist to build your portfolio.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {watchlist.map((ticker) => {
            const stock = snapshots?.[ticker];
            const bubble = stock?.bubble_analysis_data?.bubble_index ?? 0;
            const change = stock?.change_percent ?? 0;
            const trend = stock?.hmm_prediction?.predicted_trend ?? "Loading";
            return (
              <motion.div
                key={ticker}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md"
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
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Price</p>
                      <p className="mt-1 font-mono text-lg font-semibold text-[#E6EDF3]">${(stock?.price ?? 0).toFixed(2)}</p>
                    </div>
                    <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Daily</p>
                      <p className={change >= 0 ? "mt-1 font-mono text-lg font-semibold text-emerald-300" : "mt-1 font-mono text-lg font-semibold text-rose-300"}>
                        {change >= 0 ? "+" : ""}{change.toFixed(2)}%
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
  const [activeTab, setActiveTab] = useState<ActiveTab>("portfolio");
  const [selectedTicker, setSelectedTicker] = useState("NVDA");
  const [globalSearchTicker, setGlobalSearchTicker] = useState("NVDA");
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [timestamp, setTimestamp] = useState("");

  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem("watchlist") ?? "[]") as string[];
    setWatchlist(stored.map(normalizeSymbol).filter(Boolean));
  }, []);

  useEffect(() => {
    localStorage.setItem("watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    setTimestamp(new Date().toLocaleString("en-US", { hour12: false }));
  }, []);

  const addToWatchlist = (ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    if (!symbol) return;
    setWatchlist((prev) => Array.from(new Set([...prev, symbol])));
  };

  const removeFromWatchlist = (ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    setWatchlist((prev) => prev.filter((item) => item !== symbol));
  };

  const openStock = (ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    setSelectedTicker(symbol);
    setGlobalSearchTicker(symbol);
    setActiveTab("stock-analysis");
  };

  const openBubble = (ticker: string) => {
    const symbol = normalizeSymbol(ticker);
    setSelectedTicker(symbol);
    setGlobalSearchTicker(symbol);
  };

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-[#0A0C10] text-[#E6EDF3]">
      <header className="shrink-0 border-b border-[#2B313C] bg-[#0A0C10]">
        <div className="flex h-8 items-center overflow-hidden border-b border-[#2B313C] bg-[#111318]">
          <div className="animate-[ticker_36s_linear_infinite] whitespace-nowrap pl-6 font-mono text-[11px] tracking-wide text-[#9BA7B4]">
            {["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "AMD", "AVGO"].map((ticker) => (
              <span key={ticker} className="mr-10">
                <b className="text-amber-200">{ticker}</b> MARKET INTEL
              </span>
            ))}
          </div>
        </div>
        <nav className="flex min-h-16 flex-wrap items-center justify-between gap-4 px-5 py-3">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-amber-400/20 bg-[#161B22] text-amber-200">
              <ShieldAlert size={20} />
            </div>
            <div>
              <div className="text-lg font-semibold uppercase tracking-wide text-[#E6EDF3]">MIJI TERMINAL</div>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Institutional Trading Workstation</div>
            </div>
          </div>
          <div className="flex flex-1 flex-wrap items-center justify-center gap-2">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex h-10 items-center gap-2 rounded-2xl border px-3 text-sm font-medium transition ${
                  activeTab === item.id
                    ? "bg-[#1D2430] border border-amber-400/20 text-[#E6EDF3]"
                    : "border-[#2B313C] bg-[#111318] text-[#9BA7B4] hover:bg-[#151922]"
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <GlobalStockSearch onSelect={openStock} onAddToWatchlist={addToWatchlist} />
            <div className="hidden rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2 font-mono text-[11px] text-[#9BA7B4] lg:block" suppressHydrationWarning>
              {timestamp ? `LIVE ${timestamp}` : "LIVE"}
            </div>
          </div>
        </nav>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto bg-[#0A0C10]">
        {activeTab === "market-intel" && <SectorRotationPanel onTickerSelect={openStock} />}
        {activeTab === "portfolio" && <PortfolioHome watchlist={watchlist} onTickerSelect={openStock} onRemove={removeFromWatchlist} />}
        {activeTab === "bubble-diagnosis" && (
          <BubbleDiagnosisPage
            selectedTicker={selectedTicker}
            watchlist={watchlist}
            globalSearchTicker={globalSearchTicker}
            onTickerChange={openBubble}
          />
        )}
        {activeTab === "stock-analysis" && <StockAnalysisWorkspace ticker={selectedTicker} />}
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <AppErrorBoundary>
      <Suspense fallback={<LoadingScreen />}>
        <DashboardApp />
      </Suspense>
    </AppErrorBoundary>
  );
}
