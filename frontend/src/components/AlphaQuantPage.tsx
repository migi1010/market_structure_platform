"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, BrainCircuit, Loader2, ShieldCheck, TrendingUp } from "lucide-react";
import { fetchAlphaQuant } from "@/services/stockApi";
import type { AlphaQuantResponse, AlphaQuantRow } from "@/types/stock";
import { sanitizeCompanyName } from "@/lib/sanitize";

interface AlphaQuantPageProps {
  onTickerSelect: (ticker: string) => void;
}

function scoreColor(score: number): string {
  if (score >= 85) return "text-[#10B981]";
  if (score >= 70) return "text-[#06B6D4]";
  if (score >= 55) return "text-amber-200";
  return "text-red-400";
}

function actionClass(action: AlphaQuantRow["suggested_action"]): string {
  if (action === "Strong Buy" || action === "Accumulation") return "border-[#10B981]/25 bg-[#10B981]/10 text-[#10B981]";
  if (action === "Bubble Risk" || action === "Avoid") return "border-red-400/25 bg-red-400/10 text-red-400";
  if (action === "Watchlist") return "border-[#06B6D4]/25 bg-[#06B6D4]/10 text-[#06B6D4]";
  return "border-amber-400/25 bg-amber-400/10 text-amber-200";
}

const FactorBar = memo(function FactorBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] font-medium text-[#9BA7B4]">
        <span>{label}</span>
        <span className="font-mono text-[#C9D1D9]">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#1C2128]">
        <div className="h-full rounded-full bg-[#06B6D4]" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  );
});

const UNIVERSE_OPTIONS = [
  { value: "sp500", label: "S&P 500" },
  { value: "nasdaq100", label: "Nasdaq 100" },
  { value: "dow30", label: "Dow 30" },
  { value: "russell2000", label: "Russell 2000" },
  { value: "sox", label: "SOX / Philadelphia Semiconductor" },
  { value: "smh", label: "SMH" },
  { value: "soxx", label: "SOXX" },
  { value: "xlk", label: "XLK Technology" },
  { value: "xle", label: "XLE Energy" },
  { value: "xlf", label: "XLF Financials" },
  { value: "xlv", label: "XLV Healthcare" },
  { value: "xli", label: "XLI Industrials" },
  { value: "xlu", label: "XLU Utilities" },
  { value: "xlb", label: "XLB Materials" },
  { value: "xly", label: "XLY Consumer Discretionary" },
  { value: "xlp", label: "XLP Consumer Staples" },
  { value: "iwm", label: "IWM" },
  { value: "dia", label: "DIA" },
  { value: "arkk", label: "ARKK" },
  { value: "ai_infrastructure", label: "AI Infrastructure" },
  { value: "semiconductor", label: "Semiconductor" },
  { value: "memory_cycle", label: "Memory Cycle" },
  { value: "glass_substrate", label: "Glass Substrate" },
  { value: "electric_grid", label: "Electric Grid" },
  { value: "cable_copper", label: "Cable / Copper" },
  { value: "nuclear_energy", label: "Nuclear Energy" },
  { value: "energy", label: "Energy" },
  { value: "defense", label: "Defense" },
  { value: "industrial_automation", label: "Industrial Automation" },
  { value: "shipping", label: "Shipping" },
  { value: "commodities", label: "Commodities" },
  { value: "traditional_industry", label: "Traditional Industry" },
  { value: "healthcare_innovation", label: "Healthcare Innovation" },
  { value: "financial_rotation", label: "Financial Rotation" },
];

function AlphaRowCard({ row, onOpen }: { row: AlphaQuantRow; onOpen: (ticker: string) => void }) {
  const open = useCallback(() => onOpen(row.ticker), [onOpen, row.ticker]);
  const price = typeof row.price === "number" && Number.isFinite(row.price) && row.price > 0 ? row.price : null;
  const change = typeof row.change_percent === "number" && Number.isFinite(row.change_percent) ? row.change_percent : null;
  return (
    <button onClick={open} className="miji-card w-full rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-4 text-left shadow-[0_4px_24px_rgba(0,0,0,0.25)] transition hover:border-[#06B6D4]/40">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <span className="font-mono text-2xl font-semibold tracking-wide text-[#E6EDF3]">{row?.ticker ?? ""}</span>
            <span className={`rounded-lg border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${actionClass(row?.suggested_action ?? "Hold")}`}>
              {row?.suggested_action ?? "Hold"}
            </span>
          </div>
          <p className="mt-1 truncate text-sm text-[#9BA7B4]">{sanitizeCompanyName(row?.company_name) || "Unknown Company"}</p>
          <p className="mt-1 text-xs font-medium text-[#06B6D4]">{row?.sector ?? "Unknown Sector"}</p>
          <p className="mt-2 font-mono text-xs text-[#C9D1D9]">
            {price !== null ? `$${price.toFixed(2)}` : "--"}
            <span className={change === null ? "ml-2 text-[#6E7681]" : change >= 0 ? "ml-2 text-emerald-300" : "ml-2 text-rose-300"}>
              {change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "--"}
            </span>
          </p>
        </div>
        <div className="text-right">
          <p className={`font-mono text-3xl font-semibold ${scoreColor(row?.alpha_score ?? 0)}`}>{(row?.alpha_score ?? 0).toFixed(1)}</p>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Alpha Score</p>
          <p className="mt-1 text-[10px] font-medium text-[#9BA7B4]">
            Rank in {row?.universe ?? "Universe"}: <span className="font-mono text-[#C9D1D9]">#{row?.rank_in_universe ?? "--"}</span>
          </p>
          <p className="text-[10px] font-medium text-[#9BA7B4]">
            Percentile: <span className="font-mono text-[#C9D1D9]">{typeof row?.universe_percentile === "number" ? `${row.universe_percentile.toFixed(0)}%` : "--"}</span>
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-[#9BA7B4]">
        <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-2 py-1">
          Base <b className="font-mono text-[#C9D1D9]">{typeof row?.base_alpha_score === "number" ? row.base_alpha_score.toFixed(1) : "--"}</b>
        </span>
        <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-2 py-1">
          Adj <b className="font-mono text-[#C9D1D9]">{typeof row?.universe_adjustment === "number" ? `${row.universe_adjustment >= 0 ? "+" : ""}${row.universe_adjustment.toFixed(1)}` : "--"}</b>
        </span>
      </div>
      <div className="miji-factor-grid mt-4 grid gap-3 md:grid-cols-3">
        <FactorBar label="Smart Money" value={row?.smart_money ?? 0} />
        <FactorBar label="Earnings Quality" value={row?.earnings_quality ?? 0} />
        <FactorBar label="Bubble Risk" value={row?.bubble_risk ?? 0} />
      </div>
    </button>
  );
}

export default function AlphaQuantPage({ onTickerSelect }: AlphaQuantPageProps) {
  const [universe, setUniverse] = useState("sp500");
  const [data, setData] = useState<AlphaQuantResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchAlphaQuant(universe);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Alpha Quant pipeline failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [universe]);

  // One-shot retry: if the response indicates a backend fallback (qlib_engine.mode is
  // "fallback"), the alpha pipeline was still warming up. Wait 12s and try once more.
  // The ref prevents retrying more than once per universe selection.
  const alphaRetryFiredRef = useRef(false);
  useEffect(() => {
    alphaRetryFiredRef.current = false;
  }, [universe]);
  useEffect(() => {
    if (loading) return;
    if (alphaRetryFiredRef.current) return;
    if (data?.qlib_engine?.mode !== "fallback") return;
    alphaRetryFiredRef.current = true;
    const handle = window.setTimeout(async () => {
      try {
        const result = await fetchAlphaQuant(universe);
        setData(result);
      } catch {
        // Retry failure is silent — original fallback state remains.
      }
    }, 12_000);
    return () => window.clearTimeout(handle);
  }, [loading, data, universe]);


  const recommendations = useMemo(() => data?.recommendations ?? [], [data]);
  const topAlpha = useMemo(() => data?.top_alpha ?? [], [data]);
  const factorImportance = useMemo(() => Object.entries(data?.factor_importance ?? {}), [data]);

  return (
    <main className="miji-page miji-alpha-page min-h-full bg-[#0B0E14] p-5 text-[#E6EDF3]">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#06B6D4]">Institutional Alpha Quant Screener</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Alpha Intelligence Platform</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#9BA7B4]">
            Market regime, sector rotation, smart money, earnings quality, bubble intelligence, and Qlib Alpha158-style factor ranking.
          </p>
        </div>
        <div className="miji-page-actions flex items-center gap-3">
          <select
            value={universe}
            onChange={(event) => setUniverse(event.target.value)}
            className="miji-universe-select h-10 min-w-[220px] rounded-xl border border-[#2A2F3D] bg-[#151922] px-3 text-sm font-medium text-[#E6EDF3] outline-none focus:border-[#06B6D4]/40"
          >
            {UNIVERSE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          {loading && <span className="flex items-center gap-2 text-sm text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Updating institutional data</span>}
        </div>
      </div>

      {error && <div className="mb-5 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-amber-200">Live engine delayed. Showing cached institutional intelligence.</div>}

      <div className="miji-alpha-overview-grid mb-5 grid gap-4 xl:grid-cols-4">
        <section className="miji-card rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] xl:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-[#06B6D4]">
            <BrainCircuit size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">AI Quant Summary</h2>
          </div>
          <p className="text-sm leading-relaxed text-[#C9D1D9]">{data?.summary ?? "Preparing institutional alpha intelligence."}</p>
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-[#9BA7B4]">
            <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-3 py-2">Regime: <b className="text-[#E6EDF3]">{data?.market_regime?.name ?? "Unknown"}</b></span>
            <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-3 py-2">Confidence: <b className="text-[#10B981]">{(data?.market_regime?.confidence ?? 0).toFixed(1)}</b></span>
            <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-3 py-2">Qlib: <b className="text-[#06B6D4]">{data?.qlib_engine?.factor_set ?? "Alpha158"}</b></span>
          </div>
        </section>
        <section className="miji-card rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] xl:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-[#10B981]">
            <BarChart3 size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Dynamic Factor Ranking</h2>
          </div>
          <div className="miji-factor-grid grid gap-3 md:grid-cols-2">
            {factorImportance.map(([factor, weight]) => (
              <FactorBar key={factor} label={factor.replace("_", " ").toUpperCase()} value={(weight ?? 0) * 100} />
            ))}
            {factorImportance.length === 0 && ["Quality", "Growth", "Smart Money", "Theme"].map((factor) => (
              <FactorBar key={factor} label={factor.toUpperCase()} value={50} />
            ))}
          </div>
        </section>
      </div>

      <div className="miji-alpha-main-grid grid gap-5 xl:grid-cols-[minmax(0,1fr)_440px]">
        <section className="miji-alpha-table-wrap min-w-0">
          <div className="mb-3 flex items-center gap-2 text-[#06B6D4]">
            <TrendingUp size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Daily Top 10 Alpha Stocks</h2>
          </div>
          <div className="miji-alpha-list space-y-3">
            {topAlpha.map((row) => <AlphaRowCard key={row.ticker} row={row} onOpen={onTickerSelect} />)}
            {topAlpha.length === 0 && (
              <div className="miji-card rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 text-sm text-[#9BA7B4]">
                Awaiting institutional alpha data. The screener is using cached intelligence as soon as it becomes available.
              </div>
            )}
          </div>
        </section>
        <aside className="miji-card rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <div className="mb-4 flex items-center gap-2 text-[#10B981]">
            <ShieldCheck size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Daily Institutional Recommendations</h2>
          </div>
          <div className="space-y-3">
            {recommendations.map((row) => (
              <button key={row.ticker} onClick={() => onTickerSelect(row.ticker)} className="w-full rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-3 text-left transition hover:border-[#10B981]/35">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-lg font-semibold text-[#E6EDF3]">{row.ticker}</span>
                  <span className={scoreColor(row.alpha_score)}>{row.alpha_score.toFixed(1)}</span>
                </div>
                <p className="mt-1 truncate text-xs text-[#9BA7B4]">{sanitizeCompanyName(row.company_name)}</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] uppercase tracking-wide text-[#9BA7B4]">
                  <span>Smart <b className="block text-[#10B981]">{row.smart_money.toFixed(0)}</b></span>
                  <span>Bubble <b className="block text-red-400">{row.bubble_risk.toFixed(0)}</b></span>
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}
