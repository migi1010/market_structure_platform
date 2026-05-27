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

export default function StockAnalysisWorkspace() {
  const { selectedTicker, setSelectedTicker } = useWorkspace();
  const ticker = normalizeWorkspaceTicker(selectedTicker);
  const [stock, setStock] = useState<StockAnalysis | null>(null);
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
    setStock((current) => (current?.ticker?.toUpperCase() === ticker ? current : null));
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
          setStock(result);
        }
      } catch (err) {
        if (!cancelled) {
          hasFetchedOnce.current = true;
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
    if (!hasFetchedOnce.current) return;     // initial state — fetch not yet complete
    if (retryFiredRef.current) return;
    const isFallback =
      stock === null ||
      ((stock.price === null || !Number.isFinite(stock.price as number)) &&
        (stock.quote_status === "unavailable" || stock.quote?.status === "unavailable"));
    if (!isFallback) return;
    retryFiredRef.current = true;
    const handle = window.setTimeout(async () => {
      try {
        const result = await fetchStockAnalysis(ticker);
        setStock(result);
      } catch {
        // Retry failure is silent — original fallback state remains.
      }
    }, 10_000);
    return () => window.clearTimeout(handle);
  }, [loading, stock, ticker]);

  const hmm = stock?.hmm_prediction;
  const bullProbability = typeof hmm?.bull_probability === "number" ? hmm.bull_probability : null;
  const bearProbability = typeof hmm?.bear_probability === "number" ? hmm.bear_probability : null;
  const forecastConfidence = typeof hmm?.confidence === "number" ? hmm.confidence : null;
  const hmmAvailable = hmm?.available !== false && forecastConfidence !== null && bullProbability !== null && bearProbability !== null;
  const bull = hmmAvailable ? (bullProbability * 100).toFixed(0) : "Awaiting";
  const bear = hmmAvailable ? (bearProbability * 100).toFixed(0) : "Awaiting";
  const bullWidth = hmmAvailable ? `${Math.max(8, Math.min(100, bullProbability * 100))}%` : "50%";
  const bearWidth = hmmAvailable ? `${Math.max(8, Math.min(100, bearProbability * 100))}%` : "50%";
  const priceDisplay = formatPrice(finiteNumber(stock?.canonicalPrice));
  const changeDisplay = formatSignedNumber(finiteNumber(stock?.canonicalChange));
  const changePercentDisplay = formatSignedPercent(finiteNumber(stock?.canonicalChangePercent));
  const marketCapDisplay = formatMarketCap(finiteNumber(stock?.canonicalMarketCap));
  const quoteStatusDisplay = stock?.canonicalQuoteStatus ?? "unavailable";
  const sectorDisplay = stock?.canonicalSector && stock.canonicalSector !== "Unknown" ? stock.canonicalSector : "US Equity";
  const forecastTrend = hmm?.predicted_trend ?? "Calibrating model...";
  const regimeState = hmm?.regime_state ?? "Awaiting regime confirmation...";
  const regimeFallbackMessage = hmm?.message ?? "Using fallback market regime...";
  const forecastTone = hmmAvailable && forecastTrend === "Bearish" ? "text-rose-300" : hmmAvailable ? "text-emerald-300" : "text-amber-200";

  return (
    <main className="miji-page miji-stock-page min-h-full overflow-x-hidden bg-[#0A0C10] px-3 py-4 text-[#E6EDF3] sm:p-5">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Stock Analysis Workspace</p>
          <h1 className="mt-1 break-words text-2xl font-semibold tracking-wide text-[#E6EDF3] sm:text-3xl">
            {formatTickerCompanyLabel(stock?.ticker ?? ticker, stock?.company_name ?? "")}
          </h1>
          <p className="mt-1 text-sm text-[#9BA7B4]">{sectorDisplay} · {priceDisplay} · {changeDisplay} · {changePercentDisplay} · MCap {marketCapDisplay} · {quoteStatusDisplay}</p>
        </div>
        {loading && <div className="flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-200"><Loader2 className="animate-spin" size={16} /> Updating market data</div>}
      </div>

      {error && <div className="mb-5 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div>}

      <div className="miji-stock-grid grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="miji-chart-column min-w-0 space-y-5">
          <TradingViewChart ticker={ticker} />
          <BubbleDiagnosisPanel data={stock?.bubble_analysis_data} />
        </div>
        <aside className="miji-info-panel min-w-0 space-y-5">
          <section className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-200">AI Forecast Engine</p>
                <h3 className="text-lg font-black text-[#E6EDF3]">HMM Regime Inference</h3>
              </div>
              <BrainCircuit className="text-amber-200" size={22} />
            </div>
            <div className="miji-card-metrics grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
                <span className="text-xs text-[#9BA7B4]">Predicted Trend</span>
                <p className={`mt-2 flex items-center gap-2 text-xl font-black ${forecastTone}`}>
                  {hmmAvailable && forecastTrend === "Bearish" ? <TrendingDown size={18} /> : hmmAvailable ? <TrendingUp size={18} /> : <BrainCircuit size={18} />}
                  {hmmAvailable ? forecastTrend : "Calibrating model..."}
                </p>
              </div>
              <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
                <span className="text-xs text-[#9BA7B4]">Forecast Confidence</span>
                <p className="mt-2 font-mono text-xl font-black text-amber-200">{hmmAvailable && forecastConfidence !== null ? forecastConfidence.toFixed(2) : "Calibrating"}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bull Probability</span><span className="text-emerald-300">{hmmAvailable ? `${bull}%` : bull}</span></div>
                <div className="h-2 rounded bg-slate-800"><div className="h-full rounded bg-gradient-to-r from-emerald-300 to-teal-400" style={{ width: bullWidth }} /></div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bear Probability</span><span className="text-rose-300">{hmmAvailable ? `${bear}%` : bear}</span></div>
                <div className="h-2 rounded bg-slate-800"><div className="h-full rounded bg-gradient-to-r from-rose-500 to-orange-500" style={{ width: bearWidth }} /></div>
              </div>
              <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-3">
                <span className="text-xs text-[#9BA7B4]">Regime State</span>
                <p className="mt-1 font-semibold text-[#E6EDF3]">{hmmAvailable ? regimeState : regimeFallbackMessage}</p>
              </div>
            </div>
          </section>
          <AnalystForecastPanel targets={stock?.analyst_targets} consensus={stock?.analyst_consensus} price={stock?.price ?? undefined} />
          <NewsIntelligencePanel news={stock?.news ?? []} />
        </aside>
      </div>
    </main>
  );
}
