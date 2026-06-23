"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BarChart3, BrainCircuit, Loader2, ShieldCheck, TrendingUp } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { fetchAlphaQuant } from "@/services/stockApi";
import type { AlphaQuantResponse, AlphaQuantRow } from "@/types/stock";
import { sanitizeCompanyName } from "@/lib/sanitize";
import type { DrilldownTarget } from "@/lib/drilldown";
import { BilingualLabel, ChangeCell, ConfidenceMeter, HeatStrip, MarketCell, MarketRow, MarketTable, NumericCell, StatusDot, TerminalPanel, TickerCell, TickerLogo } from "./terminal";

interface AlphaQuantPageProps {
  onTickerSelect: (ticker: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

function scoreColor(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "text-[var(--theme-accent)]";
  if (value >= 85) return "text-[var(--theme-bullish)]";
  if (value >= 70) return "text-[var(--theme-highlight)]";
  if (value >= 55) return "text-[var(--theme-warning)]";
  return "text-[var(--theme-bearish)]";
}

function finiteScore(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatScore(value: number | null | undefined, digits = 1): string {
  const score = finiteScore(value);
  return score === null ? "--" : score.toFixed(digits);
}

function actionClass(action: AlphaQuantRow["suggested_action"]): string {
  if (action === "Strong Buy" || action === "Accumulation") return "text-[var(--theme-bullish)]";
  if (action === "Bubble Risk" || action === "Avoid") return "text-[var(--theme-bearish)]";
  if (action === "Watchlist") return "text-[var(--theme-highlight)]";
  return "text-[var(--theme-warning)]";
}

const FactorBar = memo(function FactorBar({ label, value }: { label: string; value: number | null | undefined }) {
  const score = finiteScore(value);
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] font-medium text-[var(--theme-muted)]">
        <span>{label}</span>
        <span className="font-mono text-[var(--theme-text-secondary)]">{formatScore(score, 0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--theme-bg)]">
        <div className={`h-full rounded-full ${score === null ? "bg-[var(--theme-border)]" : "bg-[var(--theme-highlight)]"}`} style={{ width: `${score === null ? 0 : Math.min(100, Math.max(0, score))}%` }} />
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

function AlphaRankingTape({ rows }: { rows: AlphaQuantRow[] }) {
  const leaders = rows.slice(0, 10);
  return (
    <div className="alpha-ranking-tape mb-5">
      {leaders.map((row, index) => {
        const score = primaryAlphaScore(row);
        const width = score === null ? 8 : Math.max(8, Math.min(100, score));
        return (
          <div key={row.ticker} className="alpha-tape-node">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-2">
                <TickerLogo ticker={row.ticker} />
                <span className="min-w-0">
                  <span className="block truncate font-mono text-sm font-semibold text-[var(--theme-text)]">{row.ticker}</span>
                  <span className="block truncate text-[10px] text-[var(--theme-muted)]">#{index + 1} / {row.sector ?? "Sector"}</span>
                </span>
              </span>
              <span className={`font-mono text-lg font-semibold ${scoreColor(score)}`}>{formatScore(score)}</span>
            </div>
            <div className="h-16 border-l border-[var(--theme-divider)] pl-2">
              <div className="alpha-tape-bar" style={{ height: `${width}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between gap-2">
              <HeatStrip value={score} />
              <StatusDot state={row.suggested_action} label={row.suggested_action ?? "Hold"} />
            </div>
          </div>
        );
      })}
      {leaders.length === 0 && <div className="border-y border-[var(--theme-divider)] py-5 text-sm text-[var(--theme-muted)]">Ranking tape warming.</div>}
    </div>
  );
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
  { value: "glass_substrate", label: "Substrate" },
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

const ALPHA_ROW_COLUMNS = "90px minmax(0,1fr) 70px 68px 54px minmax(86px,0.65fr)";
const SCREENER_ROW_COLUMNS = "150px 76px 70px minmax(0,1fr)";
const RECOMMENDATION_ROW_COLUMNS = "84px minmax(0,1fr) 62px 54px 82px";

function AlphaRowCard({ row, onPreview, onPreviewEnd, onContext, onOpen }: { row: AlphaQuantRow; onPreview?: (target: DrilldownTarget) => void; onPreviewEnd?: () => void; onContext?: (target: DrilldownTarget) => void; onOpen: (ticker: string) => void }) {
  const price = typeof row.price === "number" && Number.isFinite(row.price) && row.price > 0 ? row.price : null;
  const change = typeof row.change_percent === "number" && Number.isFinite(row.change_percent) ? row.change_percent : null;
  const alphaScore = primaryAlphaScore(row);
  const ranking = row.universe_ranking;
  return (
    <MarketRow
      columns={ALPHA_ROW_COLUMNS}
      onClick={() => onContext?.({ kind: "stock", symbol: row.ticker, label: sanitizeCompanyName(row.company_name) || row.ticker, value: alphaScore, meta: row.suggested_action ?? "Alpha candidate" })}
      onDoubleClick={() => onOpen(row.ticker)}
      onPreview={() => onPreview?.({ kind: "stock", symbol: row.ticker, label: sanitizeCompanyName(row.company_name) || row.ticker, value: alphaScore, meta: row.suggested_action ?? "Alpha candidate" })}
      onPreviewEnd={onPreviewEnd}
    >
      <TickerCell>
        <span className="flex items-center gap-2"><TickerLogo ticker={row?.ticker} /><span className="truncate">{row?.ticker ?? ""}</span></span>
        <span className="mt-0.5 block text-[10px] font-normal text-[var(--theme-muted)]">{price !== null ? `$${price.toFixed(2)}` : "--"}</span>
      </TickerCell>
      <MarketCell>
        <span className="block truncate text-sm font-medium text-[var(--theme-text-secondary)]">{sanitizeCompanyName(row?.company_name) || "Unknown Company"}</span>
        <span className="mt-0.5 block truncate text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">
          {row?.sector ?? "Unknown Sector"} / #{row?.rank_in_universe ?? "--"} / {formatScore(row?.universe_percentile, 0)}{finiteScore(row?.universe_percentile) !== null ? "%" : ""}
        </span>
      </MarketCell>
      <ChangeCell value={change} className="text-sm font-semibold">{change !== null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "--"}</ChangeCell>
      <NumericCell className={`text-sm font-semibold ${scoreColor(alphaScore)}`}>{formatScore(alphaScore)}</NumericCell>
      <MarketCell><HeatStrip value={alphaScore} /></MarketCell>
      <MarketCell className={`truncate text-right text-[11px] font-semibold uppercase tracking-wide ${actionClass(row?.suggested_action ?? "Hold")}`}>
        {row?.suggested_action ?? "Hold"}
        {ranking && <span className="mt-0.5 block truncate text-[10px] font-medium text-[var(--theme-muted)]">{ranking.market_classification.replaceAll("_", " ")}</span>}
      </MarketCell>
    </MarketRow>
  );
}

export default function AlphaQuantPage({ onTickerSelect, onPreview, onPreviewEnd, onContext, onDrilldown }: AlphaQuantPageProps) {
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
        // Retry failure is silent; original fallback state remains.
      }
    }, 12_000);
    return () => window.clearTimeout(handle);
  }, [loading, data, universe]);


  const recommendations = useMemo(() => data?.recommendations ?? [], [data]);
  const topAlpha = useMemo(() => data?.top_alpha ?? [], [data]);
  const factorImportance = useMemo(() => Object.entries(data?.factor_importance ?? {}), [data]);
  const screener = data?.universe_screener?.screener ?? [];

  return (
    <main className="miji-page miji-alpha-page min-h-full bg-[var(--theme-bg)] p-5 text-[var(--theme-text)]">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="terminal-micro-label">訊號 Signals</p>
          <h1 className="terminal-page-title mt-1 text-[var(--theme-text)]">Alpha Ranking</h1>
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Focus: {selectedAlphaView}</p>
          <p className="mt-2 text-sm text-[var(--theme-text-secondary)]">Regime, flow, quality, risk, factor rank.</p>
        </div>
        <div className="miji-page-actions flex items-center gap-3">
          <select
            value={universe}
            onChange={(event) => setUniverse(event.target.value)}
            className="miji-universe-select h-9 min-w-[220px] rounded-[6px] border border-[var(--theme-divider)] bg-transparent px-3 text-sm font-medium text-[var(--theme-text)] outline-none focus:border-[var(--theme-border-strong)]"
          >
            {UNIVERSE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          {loading && <span className="flex items-center gap-2 text-sm text-[var(--theme-muted)]"><Loader2 className="animate-spin" size={16} /> Updating institutional data</span>}
        </div>
      </div>

      {error && <div className="mb-5 border-y border-[var(--theme-divider)] py-3 text-sm text-[var(--theme-warning)]">Live engine delayed. Showing cached institutional intelligence.</div>}

      <AlphaRankingTape rows={topAlpha} />

      <div className="miji-alpha-overview-grid mb-5 grid gap-4 xl:grid-cols-4">
        <TerminalPanel className="xl:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-[var(--theme-highlight)]">
            <BrainCircuit size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">量化摘要 Quant Summary</h2>
          </div>
          <details className="interaction-detail">
            <summary>Regime note</summary>
            <p className="mt-3 text-sm leading-6 text-[var(--theme-text-secondary)]">{data?.summary ?? "Preparing institutional alpha intelligence."}</p>
          </details>
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-[var(--theme-border)] pt-3 text-xs text-[var(--theme-muted)]">
            <span>Regime <b className="text-[var(--theme-text)]">{data?.market_regime?.name ?? "Unknown"}</b></span>
            <span>Confidence <b className="font-mono text-[var(--theme-bullish)]">{formatScore(data?.market_regime?.confidence)}</b></span>
            <span>Qlib <b className="text-[var(--theme-highlight)]">{data?.qlib_engine?.factor_set ?? "Alpha158"}</b></span>
          </div>
        </TerminalPanel>
        <TerminalPanel className="xl:col-span-2">
          <div className="mb-3 flex items-center gap-2 text-[var(--theme-bullish)]">
            <BarChart3 size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">因子權重 Factor Rank</h2>
          </div>
          <div className="miji-factor-grid grid gap-3 md:grid-cols-2">
            {factorImportance.map(([factor, weight]) => (
              <FactorBar key={factor} label={factor.replace("_", " ").toUpperCase()} value={finiteScore(weight) === null ? null : Number(weight) * 100} />
            ))}
            {factorImportance.length === 0 && (
              <div className="border-t border-[var(--theme-border)] pt-3 text-sm text-[var(--theme-muted)] md:col-span-2">
                Factor weights are warming. No neutral placeholder weights are displayed until backend inputs are finite.
              </div>
            )}
          </div>
        </TerminalPanel>
      </div>

      <TerminalPanel className="mb-5">
        <div className="mb-3 flex items-center gap-2 text-[var(--theme-highlight)]">
          <TrendingUp size={18} />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">篩選器 Screener</h2>
        </div>
        <MarketTable
          columns={SCREENER_ROW_COLUMNS}
          header={
            <>
              <MarketCell><BilingualLabel zh="標的" en="Symbol" /></MarketCell>
              <NumericCell>分數</NumericCell>
              <MarketCell>信心</MarketCell>
              <MarketCell>分類</MarketCell>
            </>
          }
        >
          {screener.slice(0, 4).map((row) => (
            <MarketRow
              key={`${row.symbol}-${row.market_classification}`}
              columns={SCREENER_ROW_COLUMNS}
              onClick={() => onContext?.({ kind: "stock", symbol: row.symbol, label: row.symbol, value: row.ranking_score, meta: row.market_classification.replaceAll("_", " ") })}
              onDoubleClick={() => onDrilldown?.({ kind: "stock", symbol: row.symbol, label: row.symbol, value: row.ranking_score, meta: row.market_classification.replaceAll("_", " ") })}
              onPreview={() => onPreview?.({ kind: "stock", symbol: row.symbol, label: row.symbol, value: row.ranking_score, meta: row.market_classification.replaceAll("_", " ") })}
              onPreviewEnd={onPreviewEnd}
            >
              <TickerCell>
                <p className="flex items-center gap-2 truncate font-mono text-sm font-bold text-[var(--theme-text)]"><TickerLogo ticker={row.symbol} />{row.symbol}</p>
                <p className="mt-1 text-[10px] font-semibold text-[var(--theme-highlight)]">{row.market_classification.replaceAll("_", " ")}</p>
              </TickerCell>
              <NumericCell className={`text-lg font-semibold ${scoreColor(row.ranking_score)}`}>{formatScore(row.ranking_score)}</NumericCell>
              <MarketCell><ConfidenceMeter value={row.confidence ?? row.ranking_score} /></MarketCell>
              <MarketCell className="line-clamp-2 text-xs leading-5 text-[var(--theme-muted)]">{row.explanation}</MarketCell>
            </MarketRow>
          ))}
          {screener.length === 0 && (
            <div className="py-3 text-sm text-[var(--theme-muted)]">
              Universe screener awaits finite factor inputs.
            </div>
          )}
        </MarketTable>
      </TerminalPanel>

      <div className="miji-alpha-main-grid grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section id="alpha-momentum" tabIndex={-1} className="miji-alpha-table-wrap terminal-panel min-w-0 p-4 outline-none ring-0">
          <div className="mb-3 flex items-center gap-2 text-[var(--theme-highlight)]">
            <TrendingUp size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">Alpha Stocks</h2>
          </div>
          <MarketTable
            columns={ALPHA_ROW_COLUMNS}
            header={
              <>
              <MarketCell>股票</MarketCell>
              <MarketCell>Company</MarketCell>
              <NumericCell>Move</NumericCell>
              <NumericCell>Alpha</NumericCell>
              <MarketCell>熱度</MarketCell>
              <MarketCell className="text-right">Action</MarketCell>
              </>
            }
            className="miji-alpha-list"
          >
            {topAlpha.map((row) => <AlphaRowCard key={row.ticker} row={row} onPreview={onPreview} onPreviewEnd={onPreviewEnd} onContext={onContext} onOpen={onTickerSelect} />)}
            {topAlpha.length === 0 && (
              <div className="py-5 text-sm text-[var(--theme-muted)]">
                Awaiting institutional alpha data.
              </div>
            )}
          </MarketTable>
        </section>
        <aside className="terminal-panel p-4">
          <div className="mb-4 flex items-center gap-2 text-[var(--theme-bullish)]">
            <ShieldCheck size={18} />
            <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-text)]">Daily Institutional Recommendations</h2>
          </div>
          <MarketTable
            columns={RECOMMENDATION_ROW_COLUMNS}
            header={
              <>
                <MarketCell>股票</MarketCell>
                <MarketCell>因子</MarketCell>
                <NumericCell>Score</NumericCell>
                <MarketCell>狀態</MarketCell>
                <MarketCell className="text-right">Action</MarketCell>
              </>
            }
          >
            {recommendations.map((row) => (
              <MarketRow
                key={row.ticker}
                columns={RECOMMENDATION_ROW_COLUMNS}
                onClick={() => onContext?.({ kind: "stock", symbol: row.ticker, label: sanitizeCompanyName(row.company_name) || row.ticker, value: primaryAlphaScore(row), meta: row.suggested_action ?? "Hold" })}
                onDoubleClick={() => {
                  if (onDrilldown) onDrilldown({ kind: "stock", symbol: row.ticker, label: sanitizeCompanyName(row.company_name) || row.ticker, value: primaryAlphaScore(row), meta: row.suggested_action ?? "Hold" });
                  else onTickerSelect(row.ticker);
                }}
                onPreview={() => onPreview?.({ kind: "stock", symbol: row.ticker, label: sanitizeCompanyName(row.company_name) || row.ticker, value: primaryAlphaScore(row), meta: row.suggested_action ?? "Hold" })}
                onPreviewEnd={onPreviewEnd}
              >
                <TickerCell><span className="flex items-center gap-2"><TickerLogo ticker={row.ticker} />{row.ticker}</span></TickerCell>
                <MarketCell>
                  <p className="truncate text-xs text-[var(--theme-muted)]">{sanitizeCompanyName(row.company_name)}</p>
                  <p className="mt-1 text-[10px] text-[var(--theme-muted)]">Lead {formatScore(row.leadership, 0)} / Mom {formatScore(row.momentum, 0)}</p>
                </MarketCell>
                <NumericCell className={`text-sm font-semibold ${scoreColor(primaryAlphaScore(row))}`}>{formatScore(primaryAlphaScore(row))}</NumericCell>
                <MarketCell><StatusDot state={row.suggested_action} /></MarketCell>
                <MarketCell className={`truncate text-right text-[10px] font-semibold uppercase tracking-wide ${actionClass(row.suggested_action)}`}>{row.suggested_action ?? "Hold"}</MarketCell>
              </MarketRow>
            ))}
          </MarketTable>
        </aside>
      </div>
    </main>
  );
}
