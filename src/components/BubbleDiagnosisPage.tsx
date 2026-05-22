"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, ShieldAlert } from "lucide-react";
import { formatTickerCompanyLabel } from "@/lib/sanitize";
import { fetchBubbleAnalysis } from "@/services/bubbleApi";
import { defaultWatchlist } from "@/services/stockApi";
import type { BubbleApiResponse } from "@/types/bubble";
import BubbleDiagnosisPanel from "./BubbleDiagnosisPanel";
import GlobalStockSearch from "./GlobalStockSearch";

interface BubbleDiagnosisPageProps {
  selectedTicker: string;
  watchlist: string[];
  globalSearchTicker?: string;
  onTickerChange: (ticker: string) => void;
}

const hotStocks = ["NVDA", "AAPL", "MSFT", "META", "AMZN", "TSLA"];

export default function BubbleDiagnosisPage({ selectedTicker, watchlist, globalSearchTicker, onTickerChange }: BubbleDiagnosisPageProps) {
  const [analysis, setAnalysis] = useState<BubbleApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const quickSwitch = useMemo(() => {
    return [...hotStocks, ...defaultWatchlist, ...watchlist, selectedTicker, globalSearchTicker]
      .filter((item): item is string => Boolean(item))
      .map((item) => item.toUpperCase())
      .filter((item, index, array) => array.indexOf(item) === index);
  }, [globalSearchTicker, selectedTicker, watchlist]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchBubbleAnalysis(selectedTicker);
        if (!cancelled) setAnalysis(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Bubble analysis failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedTicker]);

  return (
    <main className="min-h-full bg-[#0A0C10] p-5 text-[#E6EDF3]">
      <div className="mb-5 rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="text-amber-200" size={28} />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Bubble Diagnosis</p>
              <h1 className="text-3xl font-semibold tracking-wide text-[#E6EDF3]">
                {analysis ? formatTickerCompanyLabel(analysis.ticker, analysis.company_name) : `${selectedTicker} - Institutional Valuation Workstation`}
              </h1>
            </div>
          </div>
          <label className="flex min-w-[260px] items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-[#9BA7B4]">Watchlist</span>
            <select
              value={selectedTicker}
              onChange={(event) => onTickerChange(event.target.value)}
              className="h-11 flex-1 rounded-2xl border border-[#2B313C] bg-[#111318] px-4 font-mono text-[#E6EDF3] outline-none backdrop-blur-md focus:border-amber-400/30 focus:shadow-[0_0_0_1px_rgba(251,191,36,0.15)]"
            >
              {quickSwitch.map((symbol) => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(300px,420px)_1fr]">
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">BubbleStockSearch</p>
            <GlobalStockSearch onSelect={onTickerChange} placeholder="Search any US stock for bubble analysis..." />
          </div>
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Hot Stocks</p>
            <div className="flex flex-wrap gap-2">
              {hotStocks.map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => onTickerChange(symbol)}
                  className="rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2 font-mono text-xs font-semibold text-[#C9D1D9] transition hover:border-amber-400/20 hover:text-amber-200"
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-[#9BA7B4]">
          <span>Sector: <b className="text-amber-200">{analysis?.sector ?? "Unknown"}</b></span>
          <span>Price: <b className="text-[#E6EDF3]">${(analysis?.price ?? 0).toFixed(2)}</b></span>
          {loading && <span className="flex items-center gap-2 text-amber-200"><Loader2 className="animate-spin" size={14} /> Fetching yfinance fundamentals</span>}
        </div>
      </div>

      {error && <div className="mb-5 rounded-2xl border border-rose-300/30 bg-rose-950/20 p-4 text-rose-300">{error}</div>}
      <BubbleDiagnosisPanel data={analysis?.bubble_analysis_data} />
    </main>
  );
}
