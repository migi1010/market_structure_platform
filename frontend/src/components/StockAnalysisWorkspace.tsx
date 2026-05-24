"use client";

import { useEffect, useRef, useState } from "react";
import { BrainCircuit, Loader2, TrendingDown, TrendingUp } from "lucide-react";
import { formatTickerCompanyLabel } from "@/lib/sanitize";
import { fetchStockAnalysis } from "@/services/stockApi";
import type { StockAnalysis } from "@/types/stock";
import AnalystForecastPanel from "./AnalystForecastPanel";
import BubbleDiagnosisPanel from "./BubbleDiagnosisPanel";
import NewsIntelligencePanel from "./NewsIntelligencePanel";
import TradingViewChart from "./TradingViewChart";

interface StockAnalysisWorkspaceProps {
  ticker: string;
}

export default function StockAnalysisWorkspace({ ticker }: StockAnalysisWorkspaceProps) {
  const [stock, setStock] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchStockAnalysis(ticker);
        if (!cancelled) setStock(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Analysis failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  // One-shot retry: if the initial load returned a cold-start fallback (price null,
  // status unavailable), wait 10s for the backend to warm up then try once more.
  // The retryFiredRef prevents this from firing more than once per ticker.
  const retryFiredRef = useRef(false);
  useEffect(() => {
    retryFiredRef.current = false;
  }, [ticker]);
  useEffect(() => {
    if (loading) return;
    if (retryFiredRef.current) return;
    const isFallback = stock === null || (stock.price === null && (stock.quote_status === "unavailable" || stock.quote?.status === "unavailable"));
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
  const priceDisplay = typeof stock?.price === "number" && Number.isFinite(stock.price) && stock.price > 0 ? `$${stock.price.toFixed(2)}` : "--";
  const changeDisplay = typeof stock?.change === "number" && Number.isFinite(stock.change) ? `${stock.change >= 0 ? "+" : ""}${stock.change.toFixed(2)}` : "--";
  const changePercentDisplay = typeof stock?.change_percent === "number" && Number.isFinite(stock.change_percent) ? `${stock.change_percent >= 0 ? "+" : ""}${stock.change_percent.toFixed(2)}%` : "--";
  const marketCapDisplay = typeof stock?.market_cap === "number" && Number.isFinite(stock.market_cap) && stock.market_cap > 0 ? `$${(stock.market_cap / 1_000_000_000).toFixed(1)}B` : "--";
  const quoteStatusDisplay = stock?.quote_status ?? stock?.quote?.status ?? "unavailable";
  const sectorDisplay = stock?.sector && stock.sector !== "Unknown" ? stock.sector : "US Equity";
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
