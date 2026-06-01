"use client";

import { useEffect, useRef, useState } from "react";
import { BrainCircuit, Loader2, TrendingDown, TrendingUp } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { formatTickerCompanyLabel } from "@/lib/sanitize";
import { fetchStockAnalysis } from "@/services/stockApi";
import type { StockAnalysis } from "@/types/stock";
import AnalystForecastPanel from "./AnalystForecastPanel";
import BubbleDiagnosisPanel from "./BubbleDiagnosisPanel";
import NewsIntelligencePanel from "./NewsIntelligencePanel";
import TradingViewChart from "./TradingViewChart";

const DEFAULT_STOCK_TICKER = "NVDA";

interface StockViewModel {
  ticker: string;
  companyName: string;
  sector: string;
  price: number | null;
  change: number | null;
  changePercent: number | null;
  marketCap: number | null;
  quoteStatus: string;
  requestFailed: boolean;
  analysis: StockAnalysis | null;
}

function normalizeWorkspaceTicker(ticker: string | null | undefined): string {
  return ticker?.trim().toUpperCase() || DEFAULT_STOCK_TICKER;
}

function finiteNumber(...values: unknown[]): number | null {
  for (const value of values) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string") {
      const parsed = Number.parseFloat(value.replace(/[$,%\s,]/g, ""));
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function formatPrice(value: number | null): string {
  return value !== null && value > 0 ? `$${value.toFixed(2)}` : "--";
}

function formatSignedNumber(value: number | null): string {
  return value !== null ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}` : "--";
}

function formatSignedPercent(value: number | null): string {
  return value !== null ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}%` : "--";
}

function formatMarketCap(value: number | null): string {
  if (value === null || value <= 0) return "--";
  if (value >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

function createFallbackStockView(ticker: string, requestFailed = false): StockViewModel {
  return {
    ticker,
    companyName: "",
    sector: "US Equity",
    price: null,
    change: null,
    changePercent: null,
    marketCap: null,
    quoteStatus: requestFailed ? "unavailable" : "updating",
    requestFailed,
    analysis: null,
  };
}

function createStockViewModel(ticker: string, analysis: StockAnalysis | null, requestFailed = false): StockViewModel {
  if (!analysis) return createFallbackStockView(ticker, requestFailed);
  const price = finiteNumber(analysis.canonicalPrice);
  const rawStatus = analysis.canonicalQuoteStatus || "";
  return {
    ticker: analysis.ticker?.trim().toUpperCase() || ticker,
    companyName: analysis.company_name ?? "",
    sector: analysis.canonicalSector && analysis.canonicalSector !== "Unknown" ? analysis.canonicalSector : "US Equity",
    price,
    change: finiteNumber(analysis.canonicalChange),
    changePercent: finiteNumber(analysis.canonicalChangePercent),
    marketCap: finiteNumber(analysis.canonicalMarketCap),
    quoteStatus: price !== null ? (rawStatus === "unavailable" ? "live_or_cached" : rawStatus || "live_or_cached") : requestFailed ? "unavailable" : "updating",
    requestFailed,
    analysis,
  };
}

export default function StockAnalysisWorkspace() {
  const { selectedTicker, setSelectedTicker } = useWorkspace();
  const ticker = normalizeWorkspaceTicker(selectedTicker);
  const [stockView, setStockView] = useState<StockViewModel>(() => createFallbackStockView(ticker));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // hasFetchedOnce: true after the first fetch (success or fallback) completes.
  // Prevents the retry from firing on the initial null state before any fetch.
  const hasFetchedOnce = useRef(false);
  const retryFiredRef = useRef(false);

  useEffect(() => {
    if (selectedTicker?.trim()) return;
    setSelectedTicker(DEFAULT_STOCK_TICKER);
  }, [selectedTicker, setSelectedTicker]);

  useEffect(() => {
    hasFetchedOnce.current = false;
    retryFiredRef.current = false;
    setStockView((current) => (current.ticker === ticker ? current : createFallbackStockView(ticker)));
  }, [ticker]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchStockAnalysis(ticker);
        if (!cancelled) {
          hasFetchedOnce.current = true;
          const failed = result.canonicalPrice === null && result.canonicalQuoteStatus === "unavailable";
          setStockView(createStockViewModel(ticker, result, failed));
        }
      } catch (err) {
        if (!cancelled) {
          hasFetchedOnce.current = true;
          setStockView(createFallbackStockView(ticker, true));
          setError(err instanceof Error ? err.message : "Analysis failed");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  // One-shot retry: fires ONLY after the initial fetch has returned a fallback response
  // (price null + status unavailable). The hasFetchedOnce guard ensures the retry never
  // fires on the initial null state before any fetch completes.
  useEffect(() => {
    if (loading) return;
    if (!hasFetchedOnce.current) return;     // initial state ??fetch not yet complete
    if (retryFiredRef.current) return;
    const isFallback = stockView.price === null && (stockView.quoteStatus === "unavailable" || stockView.quoteStatus === "updating");
    if (!isFallback) return;
    retryFiredRef.current = true;
    const handle = window.setTimeout(async () => {
      try {
        const result = await fetchStockAnalysis(ticker);
        const failed = result.canonicalPrice === null && result.canonicalQuoteStatus === "unavailable";
        setStockView(createStockViewModel(ticker, result, failed));
      } catch {
        // Retry failure is silent ??original fallback state remains.
      }
    }, 10_000);
    return () => window.clearTimeout(handle);
  }, [loading, stockView, ticker]);

  const stock = stockView.analysis;
  const hmm = stock?.hmm_prediction;
  const bullProbability = typeof hmm?.bull_probability === "number" ? hmm.bull_probability : null;
  const bearProbability = typeof hmm?.bear_probability === "number" ? hmm.bear_probability : null;
  const forecastConfidence = typeof hmm?.confidence === "number" ? hmm.confidence : null;
  const hmmAvailable = hmm?.available !== false && forecastConfidence !== null && bullProbability !== null && bearProbability !== null;
  const bull = hmmAvailable ? (bullProbability * 100).toFixed(0) : "Awaiting";
  const bear = hmmAvailable ? (bearProbability * 100).toFixed(0) : "Awaiting";
  const bullWidth = hmmAvailable ? `${Math.max(8, Math.min(100, bullProbability * 100))}%` : "50%";
  const bearWidth = hmmAvailable ? `${Math.max(8, Math.min(100, bearProbability * 100))}%` : "50%";
  const priceDisplay = formatPrice(stockView.price);
  const changeDisplay = formatSignedNumber(stockView.change);
  const changePercentDisplay = formatSignedPercent(stockView.changePercent);
  const marketCapDisplay = formatMarketCap(stockView.marketCap);
  const quoteStatusDisplay = stockView.quoteStatus;
  const sectorDisplay = stockView.sector;
  const forecastTrend = hmm?.predicted_trend ?? "Calibrating model...";
  const regimeState = hmm?.regime_state ?? "Awaiting regime confirmation...";
  const regimeFallbackMessage = hmm?.message ?? "Using fallback market regime...";
  const forecastTone = hmmAvailable && forecastTrend === "Bearish" ? "text-[var(--theme-bearish)]" : hmmAvailable ? "text-[var(--theme-bullish)]" : "text-[var(--theme-warning)]";

  return (
    <main className="miji-page miji-stock-page min-h-full overflow-x-hidden bg-[var(--theme-bg)] px-3 py-4 text-[var(--theme-text)] sm:p-5">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="terminal-micro-label">?撌乩?? Stock Workspace</p>
          <h1 className="mt-1 break-words text-2xl font-semibold tracking-wide text-[var(--theme-text)] sm:text-3xl">
            {formatTickerCompanyLabel(stockView.ticker, stockView.companyName)}
          </h1>
          <p className="mt-1 text-sm text-[var(--theme-text-secondary)]">{sectorDisplay} / {priceDisplay} / {changeDisplay} / {changePercentDisplay} / MCap {marketCapDisplay} / {quoteStatusDisplay}</p>
        </div>
        {loading && <div className="flex items-center gap-2 rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] px-3 py-2 text-[var(--theme-warning)]"><Loader2 className="animate-spin" size={16} /> Updating market data</div>}
      </div>

      {error && <div className="mb-5 rounded-xl border border-[var(--theme-danger)] bg-[var(--theme-panel)] p-4 text-[var(--theme-danger)]">{error}</div>}

      <div className="miji-stock-grid grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="miji-chart-column min-w-0 space-y-5">
          <TradingViewChart ticker={stockView.ticker} />
          <BubbleDiagnosisPanel data={stock?.bubble_analysis_data} />
        </div>
        <aside className="miji-info-panel min-w-0 space-y-5">
          <section className="miji-card terminal-panel p-5">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="terminal-micro-label">?葫撠? Forecast Alignment</p>
                <h3 className="terminal-panel-title text-[var(--theme-text)]">HMM Regime Inference</h3>
              </div>
              <BrainCircuit className="text-[var(--theme-accent)]" size={22} />
            </div>
            <div className="miji-card-metrics grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                <span className="text-xs text-[var(--theme-muted)]">Predicted Trend</span>
                <p className={`mt-2 flex items-center gap-2 text-xl font-black ${forecastTone}`}>
                  {hmmAvailable && forecastTrend === "Bearish" ? <TrendingDown size={18} /> : hmmAvailable ? <TrendingUp size={18} /> : <BrainCircuit size={18} />}
                  {hmmAvailable ? forecastTrend : "Calibrating model..."}
                </p>
              </div>
              <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                <span className="text-xs text-[var(--theme-muted)]">Forecast Confidence</span>
                <p className="mt-2 font-mono text-xl font-black text-[var(--theme-warning)]">{hmmAvailable && forecastConfidence !== null ? forecastConfidence.toFixed(2) : "Calibrating"}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bull Probability</span><span className="text-[var(--theme-bullish)]">{hmmAvailable ? `${bull}%` : bull}</span></div>
                <div className="h-2 rounded bg-[var(--theme-bg-secondary)]"><div className="h-full rounded bg-[var(--theme-bullish)]" style={{ width: bullWidth }} /></div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bear Probability</span><span className="text-[var(--theme-bearish)]">{hmmAvailable ? `${bear}%` : bear}</span></div>
                <div className="h-2 rounded bg-[var(--theme-bg-secondary)]"><div className="h-full rounded bg-[var(--theme-bearish)]" style={{ width: bearWidth }} /></div>
              </div>
              <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
                <span className="text-xs text-[var(--theme-muted)]">Regime State</span>
                <p className="mt-1 font-semibold text-[var(--theme-text)]">{hmmAvailable ? regimeState : regimeFallbackMessage}</p>
              </div>
            </div>
          </section>
          <AnalystForecastPanel
            targets={stock?.analyst_targets}
            consensus={stock?.analyst_consensus}
            price={stockView.price ?? undefined}
            lifecycleState={stock?.lifecycle_state}
            quoteStatus={stockView.quoteStatus}
          />
          <NewsIntelligencePanel news={stock?.news ?? []} />
        </aside>
      </div>
    </main>
  );
}
