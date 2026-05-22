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
    <section className="min-h-[680px] rounded-2xl border border-[#2B313C] bg-[#161B22]/95 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#2B313C] px-4 py-3">
        <div className="flex items-center gap-3">
          <CandlestickChart className="text-amber-200" size={20} />
          <div>
            <h2 className="text-sm font-black uppercase tracking-[0.2em] text-[#E6EDF3]">{symbol} Real-Time Chart</h2>
            <p className="text-xs text-[#9BA7B4]">Volume, SMA, RSI, MACD, SMC liquidity map</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {intervals.map((item) => (
            <button
              key={item}
              onClick={() => setInterval(item)}
              className={`h-8 rounded-lg border px-3 font-mono text-xs font-bold transition ${
                interval === item ? "border-amber-400/30 bg-amber-400/10 text-amber-200" : "border-[#2B313C] bg-[#0A0C10] text-[#9BA7B4] hover:border-amber-400/20"
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-px bg-[#2A2F3D] lg:grid-cols-[1fr_260px]">
        <div className="h-[620px] bg-[#0A0C10] p-2">
          <iframe title={`${symbol} TradingView`} src={src} className="h-full w-full rounded-xl border-0" allowFullScreen />
        </div>
        <aside className="bg-[#0A0C10] p-4">
          <div className="mb-4 flex items-center gap-2 text-amber-200">
            <Layers size={16} />
            <span className="text-xs font-black uppercase tracking-[0.18em]">Smart Money Overlay</span>
          </div>
          {["Liquidity Zones", "Fair Value Gap", "Order Block", "Volume Imbalance", "Session VWAP"].map((label, index) => (
            <div key={label} className="mb-3 rounded-xl border border-[#2B313C] bg-[#161B22]/95 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-[#C9D1D9]">{label}</span>
                <BarChart3 size={14} className={index % 2 === 0 ? "text-emerald-300" : "text-amber-200"} />
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-gradient-to-r from-emerald-300 to-teal-400" style={{ width: `${68 - index * 7}%` }} />
              </div>
            </div>
          ))}
        </aside>
      </div>
    </section>
  );
}
