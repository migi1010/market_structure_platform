"use client";

import { memo, useMemo } from "react";
import { Target } from "lucide-react";
import type { AnalystConsensus, AnalystTargets } from "@/types/stock";

interface AnalystForecastPanelProps {
  targets?: AnalystTargets;
  consensus?: AnalystConsensus;
  price?: number;
}

function analystLabel(count: number): string {
  return `${count} ${count === 1 ? "Analyst" : "Analysts"}`;
}

function targetLabel(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `$${value.toFixed(2)}` : "--";
}

function AnalystForecastPanel({ targets, consensus, price = 0 }: AnalystForecastPanelProps) {
  const available = consensus?.available ?? targets?.available ?? true;
  const averageTarget = consensus?.average_target ?? targets?.average_target ?? targets?.average ?? null;
  const high = targets?.high ?? null;
  const low = targets?.low ?? null;
  const buy = consensus?.buy ?? targets?.buy ?? null;
  const hold = consensus?.hold ?? targets?.hold ?? null;
  const sell = consensus?.sell ?? targets?.sell ?? null;
  const buyCount = buy ?? 0;
  const holdCount = hold ?? 0;
  const sellCount = sell ?? 0;
  const total = buyCount + holdCount + sellCount;
  const upside = consensus?.implied_upside ?? (price > 0 && typeof averageTarget === "number" && averageTarget > 0 ? ((averageTarget - price) / price) * 100 : null);
  const hasConsensus = available && total > 0;
  const hasTargets = available && (high !== null || averageTarget !== null || low !== null || upside !== null);

  const ratios = useMemo(() => ({
    buy: total > 0 ? (buyCount / total) * 100 : 0,
    hold: total > 0 ? (holdCount / total) * 100 : 0,
    sell: total > 0 ? (sellCount / total) * 100 : 0,
  }), [buyCount, holdCount, sellCount, total]);

  const summary = hasConsensus
    ? `Wall Street analyst sentiment remains ${ratios.buy >= 60 ? "strongly bullish" : ratios.sell >= 35 ? "cautious" : "balanced"} with ${buyCount} Buy ratings${typeof upside === "number" ? ` and a projected upside of ${upside.toFixed(1)}%` : ""}.`
    : "Analyst consensus is unavailable for this ticker.";

  return (
    <section className="miji-card rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#06B6D4]">Institutional Analyst Consensus</p>
          <h3 className="mt-1 text-lg font-semibold tracking-wide text-[#E6EDF3]">Street Target Framework</h3>
        </div>
        <Target className="text-[#06B6D4]" size={22} />
      </div>

      <div className="miji-card-metrics grid grid-cols-3 gap-3">
        {[
          ["High Target", high, "text-[#10B981]"],
          ["Average Target", averageTarget, "text-amber-200"],
          ["Low Target", low, "text-red-400"],
        ].map(([label, value, color]) => (
          <div key={String(label)} className="rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">{label}</p>
            <p className={`mt-2 font-mono text-xl font-semibold ${hasTargets ? color : "text-[#9BA7B4]"}`}>{targetLabel(value as number | null)}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[#9BA7B4]">Implied Upside</span>
          <span className={typeof upside === "number" && upside >= 0 ? "font-mono text-xl font-semibold text-[#10B981]" : typeof upside === "number" ? "font-mono text-xl font-semibold text-red-400" : "font-mono text-xl font-semibold text-[#9BA7B4]"}>
            {typeof upside === "number" && Number.isFinite(upside) ? `${upside.toFixed(1)}%` : "Unavailable"}
          </span>
        </div>

        <div className="miji-card-metrics mt-4 grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-[#10B981]/25 bg-[#10B981]/10 p-3">
            <p className="text-xs font-semibold text-[#10B981]">Buy</p>
            <p className="mt-1 font-mono text-lg font-semibold text-[#E6EDF3]">{hasConsensus ? analystLabel(buyCount) : "Not Available"}</p>
          </div>
          <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-3">
            <p className="text-xs font-semibold text-amber-200">Hold</p>
            <p className="mt-1 font-mono text-lg font-semibold text-[#E6EDF3]">{hasConsensus ? analystLabel(holdCount) : "Not Available"}</p>
          </div>
          <div className="rounded-lg border border-red-400/25 bg-red-400/10 p-3">
            <p className="text-xs font-semibold text-red-400">Sell</p>
            <p className="mt-1 font-mono text-lg font-semibold text-[#E6EDF3]">{hasConsensus ? analystLabel(sellCount) : "Not Available"}</p>
          </div>
        </div>

        {total > 0 && (
          <div className="mt-4 space-y-2">
            {[
              ["Buy", ratios.buy, "bg-[#10B981]", "text-[#10B981]"],
              ["Hold", ratios.hold, "bg-amber-300", "text-amber-200"],
              ["Sell", ratios.sell, "bg-red-400", "text-red-400"],
            ].map(([label, ratio, bar, text]) => (
              <div key={String(label)} className="grid grid-cols-[44px_1fr_42px] items-center gap-3 text-xs">
                <span className={`font-semibold ${text}`}>{label}</span>
                <div className="h-2 overflow-hidden rounded-full bg-[#1C2128]">
                  <div className={`h-full rounded-full ${bar}`} style={{ width: `${Number(ratio).toFixed(0)}%` }} />
                </div>
                <span className="text-right font-mono text-[#C9D1D9]">{Number(ratio).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}

        <p className="mt-4 text-sm leading-relaxed text-[#9BA7B4]">{summary}</p>
      </div>
    </section>
  );
}

export default memo(AnalystForecastPanel);
