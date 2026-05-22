"use client";

import { Target } from "lucide-react";
import type { AnalystTargets } from "@/types/stock";

interface AnalystForecastPanelProps {
  targets?: AnalystTargets;
  price?: number;
}

export default function AnalystForecastPanel({ targets, price = 0 }: AnalystForecastPanelProps) {
  const high = targets?.high ?? 0;
  const average = targets?.average ?? 0;
  const low = targets?.low ?? 0;
  const buy = targets?.buy ?? 0;
  const hold = targets?.hold ?? 0;
  const sell = targets?.sell ?? 0;
  const total = Math.max(1, buy + hold + sell);
  const upside = price > 0 && average > 0 ? ((average - price) / price) * 100 : 0;

  return (
    <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-200">Institutional Street View</p>
          <h3 className="text-lg font-black text-[#E6EDF3]">Analyst Forecast</h3>
        </div>
        <Target className="text-amber-200" size={22} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[
          ["High Target", high, "text-emerald-300"],
          ["Average Target", average, "text-amber-200"],
          ["Low Target", low, "text-rose-300"],
        ].map(([label, value, color]) => (
          <div key={String(label)} className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#6E7681]">{label}</p>
            <p className={`mt-2 font-mono text-xl font-black ${color}`}>${Number(value).toFixed(2)}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-xl border border-[#2B313C] bg-[#0A0C10] p-4">
        <div className="flex justify-between text-xs text-[#9BA7B4]">
          <span>Implied Upside</span>
          <span className={upside >= 0 ? "text-emerald-300" : "text-rose-300"}>{upside.toFixed(1)}%</span>
        </div>
        <div className="mt-3 grid grid-cols-3 overflow-hidden rounded-lg border border-[#2B313C]">
          <div className="bg-emerald-400/20 py-2 text-center text-xs font-black text-emerald-300" style={{ width: "100%" }}>
            Buy {Math.round((buy / total) * 100)}%
          </div>
          <div className="bg-slate-500/20 py-2 text-center text-xs font-black text-[#C9D1D9]">
            Hold {Math.round((hold / total) * 100)}%
          </div>
          <div className="bg-rose-500/20 py-2 text-center text-xs font-black text-rose-300">
            Sell {Math.round((sell / total) * 100)}%
          </div>
        </div>
      </div>
    </section>
  );
}
