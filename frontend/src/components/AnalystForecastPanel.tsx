"use client";

import { memo, useMemo } from "react";
import { Target } from "lucide-react";
import type { AnalystConsensus, AnalystTargets } from "@/types/stock";

interface AnalystForecastPanelProps {
  targets?: AnalystTargets;
  consensus?: AnalystConsensus;
  price?: number;
  lifecycleState?: string;
  quoteStatus?: string;
}

function analystLabel(count: number): string {
  return `${count} ${count === 1 ? "Analyst" : "Analysts"}`;
}

function targetLabel(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `$${value.toFixed(2)}` : "--";
}

function finiteNumber(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function pendingLabel(lifecycleState?: string, quoteStatus?: string): string {
  if (lifecycleState === "degraded") return "Degraded";
  if (quoteStatus === "live" || lifecycleState === "live" || lifecycleState === "partial_live") return "Warming";
  return "Calibrating";
}

function AnalystForecastPanel({ targets, consensus, price = 0, lifecycleState, quoteStatus }: AnalystForecastPanelProps) {
  const averageTarget = finiteNumber(consensus?.average_target) ?? finiteNumber(targets?.average_target) ?? finiteNumber(targets?.average);
  const high = finiteNumber(targets?.high_target) ?? finiteNumber(targets?.high);
  const low = finiteNumber(targets?.low_target) ?? finiteNumber(targets?.low);
  const buy = consensus?.buy ?? targets?.buy ?? null;
  const hold = consensus?.hold ?? targets?.hold ?? null;
  const sell = consensus?.sell ?? targets?.sell ?? null;
  const buyCount = finiteNumber(buy) ?? 0;
  const holdCount = finiteNumber(hold) ?? 0;
  const sellCount = finiteNumber(sell) ?? 0;
  const total = buyCount + holdCount + sellCount;
  const livePrice = finiteNumber(price);
  const upside = finiteNumber(consensus?.implied_upside) ?? finiteNumber(targets?.implied_upside) ?? (livePrice !== null && livePrice > 0 && averageTarget !== null && averageTarget > 0 ? ((averageTarget - livePrice) / livePrice) * 100 : null);
  const hasConsensus = total > 0;
  const hasTargets = high !== null || averageTarget !== null || low !== null || upside !== null;
  const waitingLabel = pendingLabel(lifecycleState, quoteStatus);

  const ratios = useMemo(() => ({
    buy: total > 0 ? (buyCount / total) * 100 : 0,
    hold: total > 0 ? (holdCount / total) * 100 : 0,
    sell: total > 0 ? (sellCount / total) * 100 : 0,
  }), [buyCount, holdCount, sellCount, total]);

  const summary = hasConsensus
    ? `Wall Street analyst sentiment remains ${ratios.buy >= 60 ? "strongly bullish" : ratios.sell >= 35 ? "cautious" : "balanced"} with ${buyCount} Buy ratings${typeof upside === "number" ? ` and a projected upside of ${upside.toFixed(1)}%` : ""}.`
    : livePrice !== null && livePrice > 0
      ? "Live quote is available; analyst target framework is warming."
      : lifecycleState === "degraded"
        ? "Analyst framework degraded; waiting for provider recovery."
        : "Analyst target framework awaiting provider data.";

  return (
    <section className="miji-card terminal-panel p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="terminal-micro-label">Institutional Analyst Consensus</p>
          <h3 className="terminal-panel-title mt-1 text-[var(--theme-text)]">Street Target Framework</h3>
        </div>
        <Target className="text-[var(--theme-warning)]" size={22} />
      </div>

      <div className="miji-card-metrics grid grid-cols-3 gap-3">
        {[
          ["High Target", high, "text-[var(--theme-bullish)]"],
          ["Average Target", averageTarget, "text-[var(--theme-highlight)]"],
          ["Low Target", low, "text-[var(--theme-bearish)]"],
        ].map(([label, value, color]) => (
          <div key={String(label)} className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--theme-muted)]">{label}</p>
            <p className={`mt-2 font-mono text-xl font-bold ${hasTargets ? color : "text-[var(--theme-muted)]"}`}>{targetLabel(value as number | null)}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[var(--theme-muted)]">Implied Upside</span>
          <span className={typeof upside === "number" && upside >= 0 ? "font-mono text-xl font-bold text-[var(--theme-bullish)]" : typeof upside === "number" ? "font-mono text-xl font-bold text-[var(--theme-bearish)]" : "font-mono text-xl font-bold text-[var(--theme-muted)]"}>
            {typeof upside === "number" && Number.isFinite(upside) ? `${upside.toFixed(1)}%` : waitingLabel}
          </span>
        </div>

        <div className="miji-card-metrics mt-4 grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-[var(--theme-bullish)] bg-[var(--theme-positive-tag-bg)] p-3">
            <p className="text-xs font-bold text-[var(--theme-bullish)]">Buy</p>
            <p className="mt-1 font-mono text-lg font-bold text-[var(--theme-text)]">{hasConsensus ? analystLabel(buyCount) : waitingLabel}</p>
          </div>
          <div className="rounded-lg border border-[var(--theme-warning)] bg-[var(--theme-panel)] p-3">
            <p className="text-xs font-bold text-[var(--theme-warning)]">Hold</p>
            <p className="mt-1 font-mono text-lg font-bold text-[var(--theme-text)]">{hasConsensus ? analystLabel(holdCount) : waitingLabel}</p>
          </div>
          <div className="rounded-lg border border-[var(--theme-bearish)] bg-[var(--theme-negative-tag-bg)] p-3">
            <p className="text-xs font-bold text-[var(--theme-bearish)]">Sell</p>
            <p className="mt-1 font-mono text-lg font-bold text-[var(--theme-text)]">{hasConsensus ? analystLabel(sellCount) : waitingLabel}</p>
          </div>
        </div>

        {total > 0 && (
          <div className="mt-4 space-y-2">
            {[
              ["Buy", ratios.buy, "bg-[var(--theme-bullish)]", "text-[var(--theme-bullish)]"],
              ["Hold", ratios.hold, "bg-[var(--theme-warning)]", "text-[var(--theme-warning)]"],
              ["Sell", ratios.sell, "bg-[var(--theme-bearish)]", "text-[var(--theme-bearish)]"],
            ].map(([label, ratio, bar, text]) => (
              <div key={String(label)} className="grid grid-cols-[44px_1fr_42px] items-center gap-3 text-xs">
                <span className={`font-semibold ${text}`}>{label}</span>
                <div className="h-2 overflow-hidden rounded-full bg-[var(--theme-bg-secondary)]">
                  <div className={`h-full rounded-full ${bar}`} style={{ width: `${Number(ratio).toFixed(0)}%` }} />
                </div>
                <span className="text-right font-mono text-[var(--theme-text-secondary)]">{Number(ratio).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}

        <p className="mt-4 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{summary}</p>
      </div>
    </section>
  );
}

export default memo(AnalystForecastPanel);
