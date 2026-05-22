"use client";

import { ArrowDownRight, ArrowUpRight, Banknote, Building2, DollarSign, ShieldAlert } from "lucide-react";
import type { BubbleAnalysisData } from "@/types/bubble";
import BubbleGauge from "./BubbleGauge";

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
    <div className="flex items-center justify-between border-b border-[#2B313C] py-3 last:border-b-0">
      <span className="text-sm font-medium text-[#9BA7B4]">{label}</span>
      <span className={`font-mono text-lg font-semibold ${accent ?? "text-[#E6EDF3]"}`}>{value}</span>
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
  const operatingCashFlowDescription =
    operatingCashFlow > 0 ? "Core business generating healthy cash flow" : "Operations are not producing durable cash support";
  const freeCashFlowDescription =
    freeCashFlow > 0 ? "Strong post-expense cash generation" : "Capital demands are absorbing operating cash";
  const cashHealthClass = freeCashFlow > 0 ? "text-emerald-300" : "text-rose-300";
  const debtRisk = debtRatio > 0.7 ? "High Leverage Risk" : "Balance Sheet Defense Stable";
  const hasCashFlowTrend = operatingCashFlow !== 0 && freeCashFlow !== 0;
  const cashFlowTrend =
    operatingCashFlow > 0 && freeCashFlow > 0
      ? "Improving"
      : operatingCashFlow > 0 || freeCashFlow > 0
        ? "Stable"
        : "Weakening";

  return (
    <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]" style={{ gridTemplateColumns: "minmax(0, 1.2fr) minmax(340px, 1fr)" }}>
      <div className="space-y-5">
        <BubbleGauge score={data?.bubble_index ?? 0} />
        <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-6 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <div className="mb-5 flex items-center gap-2 text-amber-200">
            <DollarSign size={18} />
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Revenue and Profitability</h3>
          </div>
          <MetricRow label="Revenue" value={money(revenue)} accent="text-amber-200" />
          <MetricRow label="Net Income" value={money(netIncome)} accent={netIncome >= 0 ? "text-emerald-300" : "text-rose-300"} />
          <MetricRow label="Gross Margin" value={`${(grossMargin * 100).toFixed(1)}%`} />
          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
              <div className="flex items-center gap-2 text-amber-200">
                {revenue >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                <span className="text-xs font-semibold">Revenue Quality</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-[#1C2128]">
                <div className="h-full rounded-full bg-gradient-to-r from-amber-200 to-emerald-300" style={{ width: `${Math.max(10, revenueQuality)}%` }} />
              </div>
            </div>
            <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
              <span className="text-xs font-semibold text-emerald-300">Margin Health</span>
              <p className="mt-2 text-lg font-semibold text-[#E6EDF3]">{grossMargin >= 0.4 ? "Premium" : grossMargin >= 0.2 ? "Stable" : "Thin"}</p>
            </div>
          </div>
        </section>
      </div>

      <div className="space-y-5">
        <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-6 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <div className="mb-5 flex items-center gap-2 text-emerald-300">
            <Banknote size={18} />
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Cash Flow Health</h3>
          </div>
          <p className="mb-5 text-sm leading-relaxed text-[#9BA7B4]">Cash conversion matters more than narrative. This section focuses on operating inflow and residual cash after investment needs.</p>
          <div className={`grid gap-4 ${hasCashFlowTrend ? "xl:grid-cols-3 md:grid-cols-2" : "md:grid-cols-2"}`}>
            <article className="rounded-2xl border border-[#2B313C] bg-[#161B22] p-5">
              <p className="text-sm font-semibold tracking-wide text-[#E6EDF3]">Operating Cash Flow</p>
              <p className={`mt-3 text-xl font-semibold ${operatingCashFlow >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{money(operatingCashFlow)}</p>
              <p className="mt-3 text-sm leading-relaxed text-[#9BA7B4]">{operatingCashFlowDescription}</p>
            </article>
            <article className="rounded-2xl border border-[#2B313C] bg-[#161B22] p-5">
              <p className="text-sm font-semibold tracking-wide text-[#E6EDF3]">Free Cash Flow</p>
              <p className={`mt-3 text-xl font-semibold ${cashHealthClass}`}>{money(freeCashFlow)}</p>
              <p className="mt-3 text-sm leading-relaxed text-[#9BA7B4]">{freeCashFlowDescription}</p>
            </article>
            {hasCashFlowTrend && (
              <article className="rounded-2xl border border-[#2B313C] bg-[#161B22] p-5">
                <p className="text-sm font-semibold tracking-wide text-[#E6EDF3]">Cash Flow Trend</p>
                <p className={`mt-3 text-xl font-semibold ${cashFlowTrend === "Improving" ? "text-emerald-300" : cashFlowTrend === "Weakening" ? "text-rose-300" : "text-amber-200"}`}>
                  {cashFlowTrend}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-[#9BA7B4]">
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

        <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-6 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <div className="mb-5 flex items-center gap-2 text-amber-200">
            <Building2 size={18} />
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Balance Sheet Defense</h3>
          </div>
          <MetricRow label="Total Assets" value={money(totalAssets)} />
          <MetricRow label="Total Liabilities" value={money(totalLiabilities)} accent="text-amber-200" />
          <MetricRow label="Debt Ratio" value={`${(debtRatio * 100).toFixed(1)}%`} accent={debtRatio > 0.7 ? "text-rose-300" : "text-emerald-300"} />
          <div className={`mt-5 rounded-xl border p-4 ${debtRatio > 0.7 ? "border-rose-300/30 bg-rose-950/20" : "border-amber-400/20 bg-[#111318]"}`}>
            <div className="flex items-center gap-2">
              <ShieldAlert size={18} className={debtRatio > 0.7 ? "text-rose-300" : "text-amber-200"} />
              <span className={debtRatio > 0.7 ? "font-semibold text-rose-300" : "font-semibold text-amber-200"}>{debtRisk}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
