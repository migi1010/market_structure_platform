"use client";

import { ArrowDownRight, ArrowUpRight, Banknote, Building2, DollarSign, ShieldAlert } from "lucide-react";
import type { BubbleAnalysisData } from "@/types/bubble";
import { institutionalTooltips } from "../../i18n/labels";
import BubbleGauge from "./BubbleGauge";
import InstitutionalTooltip from "./InstitutionalTooltip";

interface BubbleDiagnosisPanelProps {
  data?: BubbleAnalysisData;
}

function money(value: number | undefined): string {
  const n = value ?? 0;
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toFixed(0)}`;
}

function MetricRow({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--theme-border)] py-3 last:border-b-0">
      <span className="text-sm font-medium text-[var(--theme-muted)]">{label}</span>
      <span className={`font-mono text-lg font-bold ${accent ?? "text-[var(--theme-text)]"}`}>{value}</span>
    </div>
  );
}

function IntelligenceMetric({ label, value, tone = "text-[var(--theme-text)]" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--theme-muted)]">{label}</p>
      <p className={`mt-2 font-mono text-lg font-bold ${tone}`}>{value}</p>
    </div>
  );
}

export default function BubbleDiagnosisPanel({ data }: BubbleDiagnosisPanelProps) {
  const revenue = data?.revenue ?? 0;
  const netIncome = data?.net_income ?? 0;
  const grossMargin = data?.gross_margin ?? 0;
  const operatingCashFlow = data?.operating_cash_flow ?? 0;
  const freeCashFlow = data?.free_cash_flow ?? 0;
  const totalAssets = data?.total_assets ?? 0;
  const totalLiabilities = data?.total_liabilities ?? 0;
  const debtRatio = data?.debt_ratio ?? 0;
  const revenueQuality = revenue > 0 && netIncome > 0 ? Math.min(100, Math.max(0, (netIncome / revenue) * 600)) : 0;
  const bubbleRisk = data?.bubble_index ?? 0;
  const valuationHeat = data?.valuation_heat ?? (data?.pe_ratio ?? 0) + (data?.ps_ratio ?? 0);
  const revenueDivergence = data?.revenue_divergence ?? 0;
  const fcfQuality = data?.fcf_quality ?? 0;
  const dilutionRisk = data?.dilution_risk ?? 0;
  const distributionSignal = data?.distribution_signal ?? 0;
  const retailSpeculation = data?.retail_speculation ?? 0;
  const operatingCashFlowDescription =
    operatingCashFlow > 0 ? "Core business generating healthy cash flow" : "Operations are not producing durable cash support";
  const freeCashFlowDescription =
    freeCashFlow > 0 ? "Strong post-expense cash generation" : "Capital demands are absorbing operating cash";
  const cashHealthClass = freeCashFlow > 0 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-bearish)]";
  const debtRisk = debtRatio > 0.7 ? "High Leverage Risk" : "Balance Sheet Defense Stable";
  const hasCashFlowTrend = operatingCashFlow !== 0 && freeCashFlow !== 0;
  const cashFlowTrend =
    operatingCashFlow > 0 && freeCashFlow > 0
      ? "Improving"
      : operatingCashFlow > 0 || freeCashFlow > 0
        ? "Stable"
        : "Weakening";

  return (
    <div className="miji-bubble-grid grid gap-5 xl:grid-cols-[1.2fr_1fr]" style={{ gridTemplateColumns: "minmax(0, 1.2fr) minmax(340px, 1fr)" }}>
      <div className="space-y-5">
        <BubbleGauge score={data?.bubble_index ?? 0} />
        <section className="miji-card terminal-panel p-5">
          <div className="mb-5 flex items-center gap-2 text-[var(--theme-warning)]">
            <ShieldAlert size={18} />
            <div>
              <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-[var(--theme-text)]">
                泡沫智慧 Bubble Intelligence
                <InstitutionalTooltip label="Bubble Risk" description={institutionalTooltips.bubbleRisk} />
              </h3>
              <p className="mt-1 text-xs text-[var(--theme-muted)]">Valuation, cash conversion, dilution, distribution, and retail speculation risk.</p>
            </div>
          </div>
          <div className="miji-card-metrics grid gap-3 md:grid-cols-2">
            <IntelligenceMetric label="Bubble Risk" value={bubbleRisk.toFixed(0)} tone={bubbleRisk >= 70 ? "text-[var(--theme-bearish)]" : bubbleRisk <= 30 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-warning)]"} />
            <IntelligenceMetric label="Valuation Heat" value={valuationHeat.toFixed(1)} tone="text-[var(--theme-highlight)]" />
            <IntelligenceMetric label="Revenue Divergence" value={`${(revenueDivergence * 100).toFixed(1)}%`} tone={revenueDivergence > 0.18 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-bullish)]"} />
            <IntelligenceMetric label="FCF Quality" value={fcfQuality.toFixed(2)} tone={fcfQuality >= 0.5 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-bearish)]"} />
            <IntelligenceMetric label="Dilution Risk" value={`${dilutionRisk.toFixed(1)}%`} tone={dilutionRisk > 3 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-text-secondary)]"} />
            <IntelligenceMetric label="Distribution Signal" value={distributionSignal.toFixed(0)} tone={distributionSignal > 45 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-text-secondary)]"} />
            <IntelligenceMetric label="Retail Speculation" value={retailSpeculation.toFixed(0)} tone={retailSpeculation > 70 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-text-secondary)]"} />
          </div>
          <p className="mt-4 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{data?.ai_summary ?? "Bubble intelligence will populate after live fundamentals are loaded."}</p>
        </section>

        <section className="miji-card terminal-panel p-5">
          <div className="mb-5 flex items-center gap-2 text-[var(--theme-warning)]">
            <DollarSign size={18} />
            <h3 className="text-sm font-bold uppercase tracking-wide text-[var(--theme-text)]">Revenue and Profitability</h3>
          </div>
          <MetricRow label="Revenue" value={money(revenue)} accent="text-[var(--theme-warning)]" />
          <MetricRow label="Net Income" value={money(netIncome)} accent={netIncome >= 0 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-bearish)]"} />
          <MetricRow label="Gross Margin" value={`${(grossMargin * 100).toFixed(1)}%`} />
          <div className="miji-card-metrics mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
              <div className="flex items-center gap-2 text-[var(--theme-warning)]">
                {revenue >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                <span className="text-xs font-bold">Revenue Quality</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-[var(--theme-bg)]">
                <div className="h-full rounded-full bg-[var(--theme-bullish)]" style={{ width: `${Math.max(10, revenueQuality)}%` }} />
              </div>
            </div>
            <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
              <span className="text-xs font-bold text-[var(--theme-bullish)]">Margin Health</span>
              <p className="mt-2 text-lg font-bold text-[var(--theme-text)]">{grossMargin >= 0.4 ? "Premium" : grossMargin >= 0.2 ? "Stable" : "Thin"}</p>
            </div>
          </div>
        </section>
      </div>

      <div className="space-y-5">
        <section className="miji-card terminal-panel p-5">
          <div className="mb-5 flex items-center gap-2 text-[var(--theme-bullish)]">
            <Banknote size={18} />
            <h3 className="text-sm font-bold uppercase tracking-wide text-[var(--theme-text)]">Cash Flow Health</h3>
          </div>
          <p className="mb-5 text-sm leading-relaxed text-[var(--theme-text-secondary)]">Cash conversion matters more than narrative. This section focuses on operating inflow and residual cash after investment needs.</p>
          <div className={`miji-card-grid grid gap-4 ${hasCashFlowTrend ? "xl:grid-cols-3 md:grid-cols-2" : "md:grid-cols-2"}`}>
            <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-5">
              <p className="text-sm font-bold tracking-wide text-[var(--theme-text)]">Operating Cash Flow</p>
              <p className={`mt-3 text-xl font-bold ${operatingCashFlow >= 0 ? "text-[var(--theme-bullish)]" : "text-[var(--theme-bearish)]"}`}>{money(operatingCashFlow)}</p>
              <p className="mt-3 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{operatingCashFlowDescription}</p>
            </article>
            <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-5">
              <p className="text-sm font-bold tracking-wide text-[var(--theme-text)]">Free Cash Flow</p>
              <p className={`mt-3 text-xl font-bold ${cashHealthClass}`}>{money(freeCashFlow)}</p>
              <p className="mt-3 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{freeCashFlowDescription}</p>
            </article>
            {hasCashFlowTrend && (
              <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-5">
                <p className="text-sm font-bold tracking-wide text-[var(--theme-text)]">Cash Flow Trend</p>
                <p className={`mt-3 text-xl font-bold ${cashFlowTrend === "Improving" ? "text-[var(--theme-bullish)]" : cashFlowTrend === "Weakening" ? "text-[var(--theme-bearish)]" : "text-[var(--theme-warning)]"}`}>
                  {cashFlowTrend}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[var(--theme-text-secondary)]">
                  {cashFlowTrend === "Improving"
                    ? "Both operating and free cash flow are supporting the current capital structure."
                    : cashFlowTrend === "Stable"
                      ? "Cash generation is mixed, but the liquidity profile is still manageable."
                      : "Cash generation is deteriorating and needs closer funding discipline review."}
                </p>
              </article>
            )}
          </div>
        </section>

        <section className="miji-card terminal-panel p-5">
          <div className="mb-5 flex items-center gap-2 text-[var(--theme-warning)]">
            <Building2 size={18} />
            <h3 className="text-sm font-bold uppercase tracking-wide text-[var(--theme-text)]">Balance Sheet Defense</h3>
          </div>
          <MetricRow label="Total Assets" value={money(totalAssets)} />
          <MetricRow label="Total Liabilities" value={money(totalLiabilities)} accent="text-[var(--theme-warning)]" />
          <MetricRow label="Debt Ratio" value={`${(debtRatio * 100).toFixed(1)}%`} accent={debtRatio > 0.7 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-bullish)]"} />
          <div className={`mt-5 rounded-xl border p-4 ${debtRatio > 0.7 ? "border-[var(--theme-bearish)] bg-[var(--theme-negative-tag-bg)]" : "border-[var(--theme-border)] bg-[var(--theme-panel-inset)]"}`}>
            <div className="flex items-center gap-2">
              <ShieldAlert size={18} className={debtRatio > 0.7 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-warning)]"} />
              <span className={debtRatio > 0.7 ? "font-bold text-[var(--theme-bearish)]" : "font-bold text-[var(--theme-warning)]"}>{debtRisk}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
