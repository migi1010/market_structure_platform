"use client";

import { useMemo, useState } from "react";
import { BarChart3, CandlestickChart, Layers } from "lucide-react";

interface TradingViewChartProps {
  ticker: string;
}

const intervals = ["5", "15", "60", "D", "W"] as const;

export default function TradingViewChart({ ticker }: TradingViewChartProps) {
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
    <section className="miji-card miji-chart-card miji-tradingview min-h-[680px] min-w-0 overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--theme-border)] px-4 py-3">
        <div className="flex items-center gap-3">
          <CandlestickChart className="text-[var(--theme-warning)]" size={20} />
          <div>
            <h2 className="text-sm font-black uppercase tracking-[0.2em] text-[var(--theme-text)]">{symbol} Real-Time Chart</h2>
            <p className="text-xs text-[var(--theme-muted)]">Volume, SMA, RSI, MACD, SMC liquidity map</p>
          </div>
        </div>
        <div className="flex max-w-full items-center gap-2 overflow-x-auto">
          {intervals.map((item) => (
            <button
              key={item}
              onClick={() => setInterval(item)}
              className={`h-8 rounded-lg border px-3 font-mono text-xs font-bold transition ${
                interval === item ? "border-[var(--theme-border-strong)] bg-[var(--theme-panel-hover)] text-[var(--theme-highlight)]" : "border-[var(--theme-border)] bg-[var(--theme-panel-inset)] text-[var(--theme-muted)] hover:border-[var(--theme-border-strong)]"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div className="miji-tradingview-grid grid min-w-0 gap-px bg-[var(--theme-border)] lg:grid-cols-[1fr_260px]">
        <div className="miji-tradingview-frame h-[620px] min-w-0 bg-[var(--theme-panel-inset)] p-2">
          <iframe title={`${symbol} TradingView`} src={src} className="h-full w-full rounded-xl border-0" allowFullScreen />
        </div>
        <aside className="miji-info-panel min-w-0 bg-[var(--theme-panel-inset)] p-4">
          <div className="mb-4 flex items-center gap-2 text-[var(--theme-warning)]">
            <Layers size={16} />
            <span className="text-xs font-black uppercase tracking-[0.18em]">Smart Money Overlay</span>
          </div>
          {["Liquidity Zones", "Fair Value Gap", "Order Block", "Volume Imbalance", "Session VWAP"].map((label, index) => (
            <div key={label} className="mb-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[var(--theme-text-secondary)]">{label}</span>
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
