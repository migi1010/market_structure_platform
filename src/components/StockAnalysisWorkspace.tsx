"use client";

import { useEffect, useState } from "react";
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

  const hmm = stock?.hmm_prediction;
  const bull = ((hmm?.bull_probability ?? 0) * 100).toFixed(0);
  const bear = ((hmm?.bear_probability ?? 0) * 100).toFixed(0);

  return (
    <main className="min-h-full bg-[#0A0C10] p-5 text-[#E6EDF3]">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Stock Analysis Workspace</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">
            {formatTickerCompanyLabel(stock?.ticker ?? ticker, stock?.company_name ?? "")}
          </h1>
          <p className="mt-1 text-sm text-[#9BA7B4]">{stock?.sector ?? "Unknown"} · ${((stock?.price ?? 0)).toFixed(2)} · {(stock?.change_percent ?? 0).toFixed(2)}%</p>
        </div>
        {loading && <div className="flex items-center gap-2 rounded-xl border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-amber-200"><Loader2 className="animate-spin" size={16} /> Loading live market data</div>}
      </div>

      {error && <div className="mb-5 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-rose-200">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-5">
          <TradingViewChart ticker={ticker} />
          <BubbleDiagnosisPanel data={stock?.bubble_analysis_data} />
        </div>
        <aside className="space-y-5">
          <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-200">AI Forecast Engine</p>
                <h3 className="text-lg font-black text-[#E6EDF3]">HMM Regime Inference</h3>
              </div>
              <BrainCircuit className="text-amber-200" size={22} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
                <span className="text-xs text-[#9BA7B4]">Predicted Trend</span>
                <p className={hmm?.predicted_trend === "Bearish" ? "mt-2 flex items-center gap-2 text-xl font-black text-rose-300" : "mt-2 flex items-center gap-2 text-xl font-black text-emerald-300"}>
                  {hmm?.predicted_trend === "Bearish" ? <TrendingDown size={18} /> : <TrendingUp size={18} />}
                  {hmm?.predicted_trend ?? "Neutral"}
                </p>
              </div>
              <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
                <span className="text-xs text-[#9BA7B4]">Forecast Confidence</span>
                <p className="mt-2 font-mono text-xl font-black text-amber-200">{(hmm?.confidence ?? 0).toFixed(2)}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bull Probability</span><span className="text-emerald-300">{bull}%</span></div>
                <div className="h-2 rounded bg-slate-800"><div className="h-full rounded bg-gradient-to-r from-emerald-300 to-teal-400" style={{ width: `${bull}%` }} /></div>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs"><span>Bear Probability</span><span className="text-rose-300">{bear}%</span></div>
                <div className="h-2 rounded bg-slate-800"><div className="h-full rounded bg-gradient-to-r from-rose-500 to-orange-500" style={{ width: `${bear}%` }} /></div>
              </div>
              <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-3">
                <span className="text-xs text-[#9BA7B4]">Regime State</span>
                <p className="mt-1 font-semibold text-[#E6EDF3]">{hmm?.regime_state ?? "Unknown"}</p>
              </div>
            </div>
          </section>
          <AnalystForecastPanel targets={stock?.analyst_targets} price={stock?.price ?? 0} />
          <NewsIntelligencePanel news={stock?.news ?? []} />
        </aside>
      </div>
    </main>
  );
}
