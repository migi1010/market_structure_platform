"use client";

import { useMemo, useState } from "react";
import { BarChart3, CandlestickChart, Layers } from "lucide-react";

interface TradingViewChartProps {
  ticker: string;
  compact?: boolean;
}

const intervals = ["5", "15", "60", "D", "W"] as const;

export default function TradingViewChart({ ticker, compact = false }: TradingViewChartProps) {
  const [interval, setInterval] = useState<(typeof intervals)[number]>("D");
  const symbol = ticker.trim().toUpperCase() || "SPY";
  const src = useMemo(() => {
    const params = new URLSearchParams({
      frameElementId: "institutional-tv",
      symbol,
      interval,
      symboledit: "1",
      saveimage: "1",
      toolbarbg: "0B0E14",
      studies: JSON.stringify(["Volume@tv-basicstudies", "MASimple@tv-basicstudies", "RSI@tv-basicstudies", "MACD@tv-basicstudies"]),
      theme: "dark",
      style: "1",
      timezone: "exchange",
      withdateranges: "1",
      hideideas: "1",
    });
    return `https://s.tradingview.com/widgetembed/?${params.toString()}`;
  }, [interval, symbol]);

  return (
    <section className={`miji-chart-card miji-tradingview min-w-0 overflow-hidden border-y border-[var(--theme-divider)] bg-[var(--theme-bg)] ${compact ? "miji-tradingview-compact" : "min-h-[760px]"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--theme-divider)] px-2 py-2">
        <div className="flex items-center gap-3">
          <CandlestickChart className="text-[var(--theme-warning)]" size={20} />
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">{symbol} Real-Time Chart</h2>
            <p className="text-xs text-[var(--theme-muted)]">Volume, SMA, RSI, MACD, SMC liquidity map</p>
          </div>
        </div>
        <div className="flex max-w-full items-center gap-2 overflow-x-auto">
          {intervals.map((item) => (
            <button
              key={item}
              onClick={() => setInterval(item)}
              className={`h-7 rounded-[4px] border px-2.5 font-mono text-xs font-semibold transition ${
                interval === item ? "border-[var(--theme-hover-edge)] bg-[rgba(255,255,255,0.045)] text-[var(--theme-highlight)]" : "border-transparent text-[var(--theme-muted)] hover:border-[var(--theme-divider)] hover:text-[var(--theme-text)]"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div className="miji-tradingview-grid grid min-w-0 gap-px bg-[var(--theme-divider)] lg:grid-cols-[minmax(0,1fr)_220px]">
        <div className={`${compact ? "h-[420px]" : "h-[700px]"} miji-tradingview-frame min-w-0 bg-[var(--theme-bg)]`}>
          <iframe title={`${symbol} TradingView`} src={src} className="h-full w-full border-0" allowFullScreen />
        </div>
        <aside className="miji-info-panel min-w-0 bg-[var(--theme-bg)] p-3">
          <div className="mb-4 flex items-center gap-2 text-[var(--theme-warning)]">
            <Layers size={16} />
            <span className="text-xs font-semibold uppercase tracking-wide">Smart Money Overlay</span>
          </div>
          {["Liquidity Zones", "Fair Value Gap", "Order Block", "Volume Imbalance", "Session VWAP"].map((label, index) => (
            <div key={label} className="border-b border-[var(--theme-divider)] py-3 last:border-b-0">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[var(--theme-text-secondary)]">{label}</span>
                <BarChart3 size={14} className={index % 2 === 0 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-warning)]"} />
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-[var(--theme-bg)]">
                <div className="h-full rounded-full bg-[var(--theme-bullish)]" style={{ width: `${68 - index * 7}%` }} />
              </div>
            </div>
          ))}
        </aside>
      </div>
    </section>
  );
}
