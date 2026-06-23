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
    <main className="min-h-full bg-[var(--theme-bg)] p-5 text-[var(--theme-text)]">
      <div className="terminal-panel mb-5 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="text-amber-200" size={28} />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Bubble Diagnosis</p>
              <h1 className="text-3xl font-semibold text-[var(--theme-text)]">
                {analysis ? formatTickerCompanyLabel(analysis.ticker, analysis.company_name) : `${selectedTicker} - Institutional Valuation Workstation`}
              </h1>
            </div>
          </div>
          <label className="flex min-w-[260px] items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Watchlist</span>
            <select
              value={selectedTicker}
              onChange={(event) => onTickerChange(event.target.value)}
              className="h-10 flex-1 rounded-[6px] border border-[var(--theme-divider)] bg-transparent px-4 font-mono text-[var(--theme-text)] outline-none focus:border-[var(--theme-border-strong)]"
            >
              {quickSwitch.map((symbol) => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-5 grid gap-3 xl:grid-cols-[minmax(300px,420px)_1fr]">
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">BubbleStockSearch</p>
            <GlobalStockSearch onSelect={onTickerChange} placeholder="Search any US stock for bubble analysis..." />
          </div>
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Hot Stocks</p>
            <div className="flex flex-wrap gap-2">
              {hotStocks.map((symbol) => (
                <button
                  key={symbol}
                  onClick={() => onTickerChange(symbol)}
                  className="rounded-[4px] border border-transparent px-3 py-2 font-mono text-xs font-semibold text-[var(--theme-text-secondary)] transition hover:border-[var(--theme-divider)] hover:bg-[rgba(255,255,255,0.028)] hover:text-[var(--theme-warning)]"
                >
                  {symbol}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-[var(--theme-muted)]">
          <span>Sector: <b className="text-[var(--theme-warning)]">{analysis?.sector ?? "Unknown"}</b></span>
          <span>Price: <b className="text-[var(--theme-text)]">${(analysis?.price ?? 0).toFixed(2)}</b></span>
          {loading && <span className="flex items-center gap-2 text-[var(--theme-warning)]"><Loader2 className="animate-spin" size={14} /> Fetching yfinance fundamentals</span>}
        </div>
      </div>

      {error && <div className="mb-5 border-y border-[var(--theme-divider)] py-3 text-sm text-rose-300">{error}</div>}
      <BubbleDiagnosisPanel data={analysis?.bubble_analysis_data} />
    </main>
  );
}
