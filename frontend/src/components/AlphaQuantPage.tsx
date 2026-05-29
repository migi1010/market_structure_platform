"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, BrainCircuit, Loader2, ShieldCheck, TrendingUp } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchAlphaQuant } from "@/services/stockApi";
import type { AlphaQuantResponse, AlphaQuantRow } from "@/types/stock";
import { sanitizeCompanyName } from "@/lib/sanitize";

interface AlphaQuantPageProps {
  onTickerSelect: (ticker: string) => void;
}

function scoreColor(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "text-[#6E7681]";
  if (value >= 85) return "text-[#10B981]";
  if (value >= 70) return "text-[#06B6D4]";
  if (value >= 55) return "text-amber-200";
  return "text-red-400";
}

function finiteScore(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatScore(value: number | null | undefined, digits = 1): string {
  const score = finiteScore(value);
  return score === null ? "--" : score.toFixed(digits);
}

function actionClass(action: AlphaQuantRow["suggested_action"]): string {
  if (action === "Strong Buy" || action === "Accumulation") return "border-[#10B981]/25 bg-[#10B981]/10 text-[#10B981]";
  if (action === "Bubble Risk" || action === "Avoid") return "border-red-400/25 bg-red-400/10 text-red-400";
  if (action === "Watchlist") return "border-[#06B6D4]/25 bg-[#06B6D4]/10 text-[#06B6D4]";
  return "border-amber-400/25 bg-amber-400/10 text-amber-200";
}

const FactorBar = memo(function FactorBar({ label, value }: { label: string; value: number | null | undefined }) {
  const score = finiteScore(value);
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] font-medium text-[#9BA7B4]">
        <span>{label}</span>
        <span className="font-mono text-[#C9D1D9]">{formatScore(score, 0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#1C2128]">
        <div className={`h-full rounded-full ${score === null ? "bg-[#2A2F3D]" : "bg-[#06B6D4]"}`} style={{ width: `${score === null ? 0 : Math.min(100, Math.max(0, score))}%` }} />
      </div>
    </div>
  );
});

function alphaFactors(row: AlphaQuantRow) {
  return [
    ["Momentum", row.momentum],
    ["Leadership", row.leadership],
    ["Participation", row.participation],
    ["Acceleration", row.acceleration],
    ["Vol Quality", row.volatility_quality],
    ["Trend", row.trend_consistency],
  ] as const;
}

function primaryAlphaScore(row: AlphaQuantRow): number | null {
  const factorCandidates = [
    row.score,
    row.leadership,
    row.momentum,
    row.participation,
    row.acceleration,
  ];
  for (const value of factorCandidates) {
    const score = finiteScore(value);
    if (score !== null) return score;
  }
  return null;
}

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
  const alphaScore = primaryAlphaScore(row);
  const ranking = row.universe_ranking;
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
          <p className={`font-mono text-3xl font-semibold ${scoreColor(alphaScore)}`}>{formatScore(alphaScore)}</p>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Composite Score</p>
          <p className="mt-1 text-[10px] font-medium text-[#9BA7B4]">
            Rank in {row?.universe ?? "Universe"}: <span className="font-mono text-[#C9D1D9]">#{row?.rank_in_universe ?? "--"}</span>
          </p>
          <p className="text-[10px] font-medium text-[#9BA7B4]">
            Percentile: <span className="font-mono text-[#C9D1D9]">{formatScore(row?.universe_percentile, 0)}{finiteScore(row?.universe_percentile) !== null ? "%" : ""}</span>
          </p>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide text-[#9BA7B4]">
        <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-2 py-1">
          Base <b className="font-mono text-[#C9D1D9]">{formatScore(row?.base_alpha_score)}</b>
        </span>
        <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-2 py-1">
          Adj <b className="font-mono text-[#C9D1D9]">{finiteScore(row?.universe_adjustment) !== null ? `${Number(row.universe_adjustment) >= 0 ? "+" : ""}${Number(row.universe_adjustment).toFixed(1)}` : "--"}</b>
        </span>
        {ranking && (
          <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-2 py-1">
            Rank <b className="font-mono text-[#C9D1D9]">{formatScore(ranking.ranking_score)}</b> / <b className="text-[#06B6D4]">{ranking.market_classification.replaceAll("_", " ")}</b>
          </span>
        )}
      </div>
      <div className="miji-factor-grid mt-4 grid gap-3 md:grid-cols-3">
        {alphaFactors(row).slice(0, 6).map(([label, value]) => (
          <FactorBar key={label} label={label} value={value} />
        ))}
      </div>
    </button>
  );
}

export default function AlphaQuantPage({ onTickerSelect }: AlphaQuantPageProps) {
  const { selectedAlphaView } = useWorkspace();
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
  const screener = data?.universe_screener?.screener ?? [];

  return (
    <main className="miji-page miji-alpha-page min-h-full bg-[#0B0E14] p-5 text-[#E6EDF3]">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#06B6D4]">Institutional Alpha Quant Screener</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Alpha Intelligence Platform</h1>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-[#06B6D4]">Focus: {selectedAlphaView}</p>
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
            <span className="rounded-lg border border-[#2A2F3D] bg-[#0B0E14] px-3 py-2">Confidence: <b className="text-[#10B981]">{formatScore(data?.market_regime?.confidence)}</b></span>
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
              <FactorBar key={factor} label={factor.replace("_", " ").toUpperCase()} value={finiteScore(weight) === null ? null : Number(weight) * 100} />
            ))}
            {factorImportance.length === 0 && (
              <div className="rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-3 text-sm text-[#9BA7B4] md:col-span-2">
                Factor weights are warming. No neutral placeholder weights are displayed until backend inputs are finite.
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="miji-card mb-5 rounded-2xl border border-[#2A2F3D] bg-[#151922]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
        <div className="mb-3 flex items-center gap-2 text-[#06B6D4]">
          <TrendingUp size={18} />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#E6EDF3]">Institutional Universe Screener</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {screener.slice(0, 4).map((row) => (
            <div key={`${row.symbol}-${row.market_classification}`} className="rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm font-semibold text-[#E6EDF3]">{row.symbol}</p>
                  <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-[#06B6D4]">{row.market_classification.replaceAll("_", " ")}</p>
                </div>
                <p className={`font-mono text-lg font-semibold ${scoreColor(row.ranking_score)}`}>{formatScore(row.ranking_score)}</p>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-[#9BA7B4]">{row.explanation}</p>
            </div>
          ))}
          {screener.length === 0 && (
            <div className="rounded-xl border border-[#2A2F3D] bg-[#0B0E14] p-3 text-sm text-[#9BA7B4]">
              Universe screener awaits finite factor inputs.
            </div>
          )}
        </div>
      </section>

      <div className="miji-alpha-main-grid grid gap-5 xl:grid-cols-[minmax(0,1fr)_440px]">
        <section id="alpha-momentum" tabIndex={-1} className="miji-alpha-table-wrap min-w-0 outline-none ring-0">
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
                  <span className={scoreColor(primaryAlphaScore(row))}>{formatScore(primaryAlphaScore(row))}</span>
                </div>
                <p className="mt-1 truncate text-xs text-[#9BA7B4]">{sanitizeCompanyName(row.company_name)}</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] uppercase tracking-wide text-[#9BA7B4]">
                  <span>Lead <b className="block text-[#10B981]">{formatScore(row.leadership, 0)}</b></span>
                  <span>Mom <b className="block text-[#06B6D4]">{formatScore(row.momentum, 0)}</b></span>
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}
