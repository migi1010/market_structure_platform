"use client";

import React, { memo, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Blocks,
  BrainCircuit,
  CheckCircle2,
  Loader2,
  Network,
  RadioTower,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  fetchThemeCapitalFlow,
  fetchThemeDetail,
  fetchThemeEmerging,
  fetchThemeNarrative,
  fetchThemeRotation,
  fetchThemeSupplyChain,
  fetchThemeTop,
} from "@/services/stockApi";
import type {
  EmergingThemeResponse,
  ThemeCapitalFlowResponse,
  ThemeDetailResponse,
  ThemeLeader,
  ThemeNarrativeResponse,
  NarrativeIntelligence,
  ThemeRotationResponse,
  ThemeScore,
  ThemeSupplyChainResponse,
  ThemeTopResponse,
} from "@/types/stock";

const cardClass = "miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md";
const warmupMessages = [
  "Initializing Capital Flow Engine...",
  "Mapping Supply Chains...",
  "Building Theme Rotation Matrix...",
  "Syncing Institutional Positioning...",
  "Scanning Emerging Narratives...",
  "Loading Macro Regime...",
  "Theme Intelligence Online",
];

function finiteScore(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function scoreTone(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "text-[#6E7681]";
  if (value >= 75) return "text-emerald-300";
  if (value >= 55) return "text-amber-200";
  return "text-rose-300";
}

function barTone(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "bg-[#2B313C]";
  if (value >= 75) return "bg-emerald-300";
  if (value >= 55) return "bg-amber-200";
  return "bg-rose-300";
}

function pct(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  if (numeric === null) return "--";
  return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(1)}%`;
}

function ratio(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  return numeric === null ? "--" : `${numeric.toFixed(2)}x`;
}

function relatedStocksForTheme(theme: ThemeScore): ThemeLeader[] {
  const explicit = theme.related_stocks ?? theme.top_alpha_stocks ?? [];
  if (explicit.length > 0) return explicit;
  return theme.leaders ?? [];
}

function formatOptionalScore(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "--";
}

function isNarrativeIntelligence(value: ThemeScore["narrative_intelligence"]): value is NarrativeIntelligence {
  return Boolean(value?.narrative_id && value?.narrative_name);
}

function ShimmerBlock({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-[#1C2128] ${className}`} />;
}

function EmptyState({
  title = "Awaiting institutional data flow...",
  detail = "Theme engine calibrating live market inputs.",
}: {
  title?: string;
  detail?: string;
}) {
  return (
    <div className="rounded-2xl border border-[#2B313C] bg-[#111318] p-5">
      <p className="font-semibold tracking-wide text-[#E6EDF3]">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-[#9BA7B4]">{detail}</p>
    </div>
  );
}

function WarmupExperience({ progress, messageIndex }: { progress: number; messageIndex: number }) {
  const activeIndex = Math.min(messageIndex, warmupMessages.length - 1);
  return (
    <section className={`${cardClass} mb-4 overflow-hidden transition-opacity duration-300`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Institutional System Boot</p>
          <h2 className="mt-2 text-xl font-semibold tracking-wide text-[#E6EDF3]">Theme Intelligence Engine</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#9BA7B4]">
            Calibrating live market structure, supply chain exposure, capital flow and macro regime data. Render cold starts may take a moment.
          </p>
        </div>
        <div className="rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2 font-mono text-xs text-[#C9D1D9]">
          {progress.toFixed(0)}% READY
        </div>
      </div>

      <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#0A0C10]">
        <div className="h-full rounded-full bg-amber-200 transition-all duration-700 ease-out" style={{ width: `${Math.min(100, Math.max(6, progress))}%` }} />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-2 rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
          {warmupMessages.map((message, index) => {
            const complete = index < activeIndex || progress >= 100;
            const active = index === activeIndex && progress < 100;
            const tone = complete
              ? "border-emerald-300/30 text-emerald-300"
              : active
                ? "border-amber-400/30 text-amber-200"
                : "border-[#2B313C] text-[#6E7681]";
            return (
              <div key={message} className="flex items-center gap-3 text-sm">
                <div className={`flex h-5 w-5 items-center justify-center rounded-full border ${tone}`}>
                  {complete ? <CheckCircle2 size={13} /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
                </div>
                <span className={complete ? "text-[#C9D1D9]" : active ? "text-[#E6EDF3]" : "text-[#6E7681]"}>{message}</span>
              </div>
            );
          })}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
              <div className="flex items-center justify-between gap-3">
                <ShimmerBlock className="h-4 w-32" />
                <ShimmerBlock className="h-7 w-12" />
              </div>
              <ShimmerBlock className="mt-4 h-2 w-full" />
              <div className="mt-4 grid grid-cols-3 gap-2">
                <ShimmerBlock className="h-10" />
                <ShimmerBlock className="h-10" />
                <ShimmerBlock className="h-10" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ThemeRow({
  theme,
  onTickerSelect,
  onThemeSelect,
}: {
  theme: ThemeScore;
  onTickerSelect: (ticker: string) => void;
  onThemeSelect: (theme: string) => void;
}) {
  const score = finiteScore(theme?.ranking_score) ?? finiteScore(theme?.theme_strength_score);
  const leadership = theme.leadership_intelligence;
  const leadershipScore = typeof theme.leadership_score === "number" ? theme.leadership_score : leadership?.leadership_score;
  const ranking = theme.universe_ranking;
  const leaders = relatedStocksForTheme(theme);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onThemeSelect(theme.theme)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onThemeSelect(theme.theme);
      }}
      className="w-full cursor-pointer rounded-2xl border border-[#2B313C] bg-[#111318] p-4 text-left transition-colors hover:border-amber-400/20 hover:bg-[#151922]"
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold tracking-wide text-[#E6EDF3]">{theme?.theme ?? "Theme"}</p>
          <p className="mt-1 truncate text-xs text-[#9BA7B4]">{theme?.category ?? "Universal Market Theme"}</p>
        </div>
        <div className={`font-mono text-xl font-semibold ${scoreTone(score)}`}>{formatOptionalScore(score)}</div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[#0A0C10]">
        <div className={`h-full rounded-full ${barTone(score)}`} style={{ width: `${score === null ? 0 : Math.min(100, Math.max(0, score))}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          <p className="text-[#6E7681]">Flow</p>
          <p className={`font-mono font-semibold ${scoreTone(theme?.theme_capital_flow_score)}`}>{formatOptionalScore(theme?.theme_capital_flow_score)}</p>
        </div>
        <div>
          <p className="text-[#6E7681]">RS vs SPY</p>
          <p className="font-mono font-semibold text-[#C9D1D9]">{pct(theme?.relative_strength_vs_spy)}</p>
        </div>
        <div>
          <p className="text-[#6E7681]">Breadth</p>
          <p className="font-mono font-semibold text-[#C9D1D9]">{formatOptionalScore(theme?.breadth_participation)}{finiteScore(theme?.breadth_participation) !== null ? "%" : ""}</p>
        </div>
      </div>
      {leadership && (
        <div className="mt-3 rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-200">Leadership</p>
            <p className="font-mono text-sm font-semibold text-[#E6EDF3]">{formatOptionalScore(leadershipScore)}</p>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-[#9BA7B4]">{leadership.capital_rotation}</p>
        </div>
      )}
      {ranking && (
        <div className="mt-3 rounded-xl border border-[#2B313C] bg-[#0A0C10] p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Universe Rank</p>
            <p className="font-mono text-sm font-semibold text-[#E6EDF3]">{formatOptionalScore(ranking.ranking_score)}</p>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-[#9BA7B4]">{ranking.market_classification.replaceAll("_", " ")} - {ranking.risk_state ?? "balanced"}</p>
        </div>
      )}
      {leaders.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[#6E7681]">Top Related</p>
          <div className="flex flex-wrap gap-2">
          {leaders.slice(0, 4).map((leader) => (
            <button
              key={`${theme.theme}-${leader.ticker}`}
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onTickerSelect(leader.ticker);
              }}
              className="rounded-lg border border-[#2B313C] bg-[#0A0C10] px-2 py-1 font-mono text-[11px] font-semibold text-[#C9D1D9]"
            >
              {leader.ticker}
            </button>
          ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, sublabel, icon }: { label: string; value: string; sublabel: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">{label}</p>
        <div className="text-amber-200">{icon}</div>
      </div>
      <p className="text-xl font-semibold tracking-wide text-[#E6EDF3]">{value}</p>
      <p className="mt-2 text-xs leading-relaxed text-[#9BA7B4]">{sublabel}</p>
    </div>
  );
}

function ThemeDetailPanel({
  detail,
  loading,
  onTickerSelect,
}: {
  detail: ThemeDetailResponse | null;
  loading: boolean;
  onTickerSelect: (ticker: string) => void;
}) {
  if (loading) {
    return (
      <section id="theme-detail" tabIndex={-1} className={`${cardClass} mb-4 outline-none ring-0`}>
        <div className="grid gap-4 md:grid-cols-3">
          <ShimmerBlock className="h-24" />
          <ShimmerBlock className="h-24" />
          <ShimmerBlock className="h-24" />
        </div>
        <ShimmerBlock className="mt-4 h-28" />
      </section>
    );
  }
  if (!detail) return null;
  const related = detail.related_stocks ?? [];
  const alpha = detail.top_alpha_stocks ?? related;
  const chainRoles = Object.entries(detail.supply_chain ?? {}).slice(0, 4);
  return (
    <section id="theme-detail" tabIndex={-1} className={`${cardClass} mb-4 outline-none ring-0 animate-[mijiResultGlow_1.4s_ease-out_1]`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Theme Detail / 主題拆解</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-wide text-[#E6EDF3]">{detail.theme}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#9BA7B4]">{detail.description ?? detail.summary}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-right text-xs">
          <div className="rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2">
            <p className="text-[#6E7681]">Score</p>
            <p className={`font-mono text-lg font-semibold ${scoreTone(detail.theme_score ?? undefined)}`}>{formatOptionalScore(detail.theme_score)}</p>
          </div>
          <div className="rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2">
            <p className="text-[#6E7681]">Confidence</p>
            <p className="font-semibold text-[#C9D1D9]">{detail.confidence ?? "Partial"}</p>
          </div>
          <div className="rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2">
            <p className="text-[#6E7681]">Status</p>
            <p className="font-semibold text-amber-200">{detail.status ?? "Watchlist"}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Related Stocks / 受惠股</p>
          <div className="grid gap-2 md:grid-cols-2">
            {related.slice(0, 8).map((stock) => (
              <button
                key={`${detail.theme}-${stock.ticker}`}
                type="button"
                onClick={() => onTickerSelect(stock.ticker)}
                className="rounded-xl border border-[#2B313C] bg-[#111318] p-3 text-left"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-mono text-sm font-semibold text-[#E6EDF3]">{stock.ticker}</p>
                    <p className="truncate text-xs text-[#9BA7B4]">{stock.company_name ?? stock.role ?? "Theme exposure"}</p>
                    <p className="mt-1 text-[11px] text-[#6E7681]">{stock.role ?? "related stock"}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm font-semibold text-[#C9D1D9]">{typeof stock.price === "number" ? `$${stock.price.toFixed(2)}` : "--"}</p>
                    <p className={finiteScore(stock.change_percent) === null ? "font-mono text-[11px] text-[#6E7681]" : Number(stock.change_percent) >= 0 ? "font-mono text-[11px] text-emerald-300" : "font-mono text-[11px] text-rose-300"}>
                      {pct(stock.change_percent)}
                    </p>
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
                  <span className="rounded-lg bg-[#0A0C10] px-2 py-1 text-[#9BA7B4]">Alpha {formatOptionalScore(stock.alpha_score)}</span>
                  <span className="rounded-lg bg-[#0A0C10] px-2 py-1 text-[#9BA7B4]">SM {formatOptionalScore(stock.smart_money)}</span>
                  <span className="rounded-lg bg-[#0A0C10] px-2 py-1 text-[#9BA7B4]">Bubble {formatOptionalScore(stock.bubble_risk)}</span>
                </div>
              </button>
            ))}
            {related.length === 0 && <EmptyState detail="Theme stock universe is calibrating. Related tickers will appear once backend mapping returns." />}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Top Alpha Stocks</p>
            <div className="flex flex-wrap gap-2">
              {alpha.slice(0, 6).map((stock) => (
                <button key={`alpha-${stock.ticker}`} type="button" onClick={() => onTickerSelect(stock.ticker)} className="rounded-lg border border-[#2B313C] bg-[#0A0C10] px-2.5 py-1.5 font-mono text-xs font-semibold text-[#C9D1D9]">
                  {stock.ticker} {formatOptionalScore(stock.alpha_score)}
                </button>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Supply Chain Map</p>
            <div className="space-y-2">
              {chainRoles.map(([role, stocks]) => (
                <div key={role} className="flex items-start justify-between gap-3 text-xs">
                  <span className="capitalize text-[#9BA7B4]">{role.replaceAll("_", " ")}</span>
                  <span className="max-w-[70%] text-right font-mono text-[#C9D1D9]">{stocks.slice(0, 4).map((stock) => stock.ticker).join(" · ")}</span>
                </div>
              ))}
              {chainRoles.length === 0 && <p className="text-sm text-[#9BA7B4]">Supply chain map calibrating...</p>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
              <p className="text-[11px] text-[#6E7681]">Capital Flow</p>
              <p className={`font-mono text-lg font-semibold ${scoreTone(detail.capital_flow ?? undefined)}`}>{formatOptionalScore(detail.capital_flow)}</p>
            </div>
            <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
              <p className="text-[11px] text-[#6E7681]">Bubble Risk</p>
              <p className={`font-mono text-lg font-semibold ${scoreTone(finiteScore(detail.bubble_risk) === null ? null : 100 - Number(detail.bubble_risk))}`}>{formatOptionalScore(detail.bubble_risk)}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ThemeIntelligenceDashboard({ onTickerSelect }: { onTickerSelect: (ticker: string) => void }) {
  const { selectedTheme, setSelectedTheme } = useWorkspace();
  const [top, setTop] = useState<ThemeTopResponse | null>(null);
  const [emerging, setEmerging] = useState<EmergingThemeResponse | null>(null);
  const [rotation, setRotation] = useState<ThemeRotationResponse | null>(null);
  const [flow, setFlow] = useState<ThemeCapitalFlowResponse | null>(null);
  const [narrative, setNarrative] = useState<ThemeNarrativeResponse | null>(null);
  const [supplyChain, setSupplyChain] = useState<ThemeSupplyChainResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [bootIndex, setBootIndex] = useState(0);
  const [bootProgress, setBootProgress] = useState(8);
  const [themeDetail, setThemeDetail] = useState<ThemeDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const timeout = window.setTimeout(() => {
      if (!cancelled) {
        setLoading(false);
        setError("Live engine delayed. Showing cached institutional intelligence.");
      }
    }, 15_000);

    fetchThemeTop()
      .then((value) => {
        if (!cancelled) setTop(value);
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Theme engine calibrating...");
      })
      .finally(() => {
        if (!cancelled) {
          window.clearTimeout(timeout);
          setLoading(false);
        }
      });

    fetchThemeEmerging().then((value) => !cancelled && setEmerging(value)).catch(() => {});
    fetchThemeRotation().then((value) => !cancelled && setRotation(value)).catch(() => {});
    fetchThemeCapitalFlow().then((value) => !cancelled && setFlow(value)).catch(() => {});
    fetchThemeNarrative().then((value) => !cancelled && setNarrative(value)).catch(() => {});
    fetchThemeSupplyChain().then((value) => !cancelled && setSupplyChain(value)).catch(() => {});
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, []);

  useEffect(() => {
    if (!loading) {
      setBootIndex(warmupMessages.length - 1);
      setBootProgress(100);
      return;
    }
    const interval = window.setInterval(() => {
      setBootIndex((current) => Math.min(current + 1, warmupMessages.length - 2));
      setBootProgress((current) => Math.min(current + 13, 92));
    }, 1300);
    return () => window.clearInterval(interval);
  }, [loading]);

  useEffect(() => {
    if (!selectedTheme) return;
    let cancelled = false;
    setDetailLoading(true);
    fetchThemeDetail(selectedTheme)
      .then((value) => {
        if (!cancelled) setThemeDetail(value);
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedTheme]);

  useEffect(() => {
    if (!selectedTheme || detailLoading) return;
    window.setTimeout(() => {
      const element = document.getElementById("theme-detail");
      element?.scrollIntoView({ behavior: "smooth", block: "start" });
      element?.focus({ preventScroll: true });
    }, 80);
  }, [detailLoading, selectedTheme, themeDetail]);

  const topThemes = top?.themes ?? [];
  const emergingThemes = emerging?.emerging_themes ?? [];
  const flowItems = flow?.capital_flow ?? topThemes;
  const narrativeItems = narrative?.top_narratives?.length
    ? narrative.top_narratives
    : topThemes.map((theme) => theme.narrative_intelligence).filter(isNarrativeIntelligence);
  const overheatedThemes = rotation?.overheated_themes ?? [];
  const undervaluedThemes = rotation?.undervalued_themes ?? [];
  const regime = top?.cross_asset_regime;
  const supplyLeaders = useMemo(() => {
    return (supplyChain?.themes ?? []).flatMap((theme) => theme.leaders.slice(0, 2).map((leader) => ({ ...leader, theme: theme.theme }))).slice(0, 10);
  }, [supplyChain]);

  return (
    <main className="miji-page p-5 text-[#E6EDF3]">
      <div className="miji-page-header mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Theme Intelligence / Market Themes</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Universal Capital Flow Command</h1>
          {selectedTheme && <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-amber-200">Focus: {selectedTheme}</p>}
          <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#9BA7B4]">
            Cross-asset theme discovery across capital flow, supply chains, macro regime, narrative acceleration and institutional positioning.
          </p>
        </div>
        {loading && (
          <div className="flex items-center gap-2 text-sm font-medium text-[#9BA7B4]">
            <Loader2 className="animate-spin" size={16} /> {warmupMessages[Math.min(bootIndex, warmupMessages.length - 1)]}
          </div>
        )}
      </div>

      {loading && topThemes.length === 0 && <WarmupExperience progress={bootProgress} messageIndex={bootIndex} />}

      {!loading && error && !top && (
        <div className={`${cardClass} mb-4`}>
          <p className="font-semibold text-amber-200">Theme engine calibrating...</p>
          <p className="mt-2 text-sm text-[#9BA7B4]">{error}</p>
          <p className="mt-2 text-sm text-[#9BA7B4]">Awaiting institutional data flow from the production quant engine.</p>
        </div>
      )}

      <div className="miji-card-grid mb-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Risk Regime" value={regime?.risk_on_off ?? "Warming"} sublabel={`Risk score ${formatOptionalScore(regime?.risk_on_score)} - liquidity ${regime?.liquidity_regime ?? "pending"}`} icon={<Activity size={17} />} />
        <MetricCard label="AI CapEx Regime" value={regime?.AI_capex_regime ?? "Warming"} sublabel={`AI capex score ${formatOptionalScore(regime?.AI_capex_score)} from SOXX, QQQ and growth proxies`} icon={<BrainCircuit size={17} />} />
        <MetricCard label="Volatility" value={regime?.volatility_regime ?? "Warming"} sublabel={`Volatility score ${formatOptionalScore(regime?.volatility_score)} using VIX proxy and equity vol`} icon={<ShieldAlert size={17} />} />
        <MetricCard label="Inflation" value={regime?.inflation_regime ?? "Warming"} sublabel={`Inflation score ${formatOptionalScore(regime?.inflation_score)} from oil, gold and yields`} icon={<RadioTower size={17} />} />
      </div>

      <section className={`${cardClass} mb-4`}>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Narrative Acceleration / Cross-Theme Ranking</p>
            <p className="mt-1 text-sm text-[#9BA7B4]">{narrative?.summary ?? "Ranking leadership, participation, acceleration and institutional alignment across themes."}</p>
          </div>
          <Activity className="text-amber-200" size={19} />
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {narrativeItems.slice(0, 4).map((item) => (
            <div key={item.narrative_id} className="rounded-xl border border-[#2B313C] bg-[#111318] p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[#E6EDF3]">{item.narrative_name}</p>
                  <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-amber-200">{item.narrative_state.replaceAll("_", " ")}</p>
                </div>
                <p className={`font-mono text-lg font-semibold ${scoreTone(item.narrative_strength)}`}>{formatOptionalScore(item.narrative_strength)}</p>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-[#9BA7B4]">{item.capital_flow_semantics ?? item.explanation}</p>
            </div>
          ))}
          {loading && narrativeItems.length === 0 && Array.from({ length: 4 }).map((_, index) => <ShimmerBlock key={index} className="h-28" />)}
          {!loading && narrativeItems.length === 0 && <EmptyState detail="Narrative acceleration appears once theme leadership factors are available." />}
        </div>
      </section>

      <ThemeDetailPanel detail={themeDetail} loading={detailLoading} onTickerSelect={onTickerSelect} />

      <div className="miji-card-grid grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <section className={cardClass}>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Top Themes / Market Leadership</p>
              <p className="mt-1 text-sm text-[#9BA7B4]">{top?.summary ?? "Scoring universal themes across market structure and capital flow."}</p>
            </div>
            <TrendingUp className="text-amber-200" size={20} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {topThemes.slice(0, 8).map((theme) => (
              <ThemeRow key={theme.theme} theme={theme} onTickerSelect={onTickerSelect} onThemeSelect={setSelectedTheme} />
            ))}
            {loading && topThemes.length === 0 && Array.from({ length: 4 }).map((_, index) => <ShimmerBlock key={index} className="h-36" />)}
            {!loading && topThemes.length === 0 && (
              <EmptyState detail="No ranked themes returned yet. The engine will populate this panel once market data confirms a theme signal." />
            )}
          </div>
        </section>

        <section className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <ArrowUpRight className="text-emerald-300" size={20} />
            <div>
              <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Emerging Themes / Early Rotation</p>
              <p className="mt-1 text-sm text-[#9BA7B4]">{emerging?.summary ?? "Detecting early capital-flow acceleration."}</p>
            </div>
          </div>
          <div className="space-y-3">
            {emergingThemes.slice(0, 7).map((theme) => (
              <div key={theme.theme} className="rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-[#E6EDF3]">{theme.theme}</p>
                    <p className="mt-1 text-xs text-[#9BA7B4]">{theme.category}</p>
                  </div>
                  <p className={`font-mono text-lg font-semibold ${scoreTone(theme.emerging_score)}`}>{formatOptionalScore(theme.emerging_score)}</p>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-[#9BA7B4]">{theme.explainability?.[0] ?? "Acceleration detected across theme proxies."}</p>
              </div>
            ))}
            {loading && emergingThemes.length === 0 && Array.from({ length: 4 }).map((_, index) => <ShimmerBlock key={index} className="h-24" />)}
            {!loading && emergingThemes.length === 0 && (
              <EmptyState title="Theme engine calibrating..." detail="Emerging theme signals require acceleration across flow, narrative and supply chain inputs." />
            )}
          </div>
        </section>
      </div>

      <div className="miji-card-grid mt-4 grid gap-4 xl:grid-cols-3">
        <section className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <Network className="text-amber-200" size={19} />
            <div>
              <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Capital Flow / Flow Intelligence</p>
              <p className="mt-1 text-sm text-[#9BA7B4]">{flow?.summary ?? "Ranking flow by breadth, relative volume and ETF leadership."}</p>
            </div>
          </div>
          <div className="space-y-3">
            {flowItems.slice(0, 6).map((item) => (
              <div key={item.theme} className="flex items-center justify-between gap-3 rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[#E6EDF3]">{item.theme}</p>
                  <p className="text-xs text-[#9BA7B4]">Volume {ratio(item.volume_expansion)} - Breadth {formatOptionalScore(item.breadth_participation)}{finiteScore(item.breadth_participation) !== null ? "%" : ""}</p>
                </div>
                <p className={`font-mono font-semibold ${scoreTone(item.theme_capital_flow_score)}`}>{formatOptionalScore(item.theme_capital_flow_score)}</p>
              </div>
            ))}
            {loading && flowItems.length === 0 && Array.from({ length: 4 }).map((_, index) => <ShimmerBlock key={index} className="h-16" />)}
            {!loading && flowItems.length === 0 && <EmptyState detail="Awaiting confirmed institutional flow readings across theme baskets." />}
          </div>
        </section>

        <section className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <Blocks className="text-amber-200" size={19} />
            <div>
              <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Supply Chain Leaders / Exposure Map</p>
              <p className="mt-1 text-sm text-[#9BA7B4]">Upstream, equipment, infrastructure and downstream exposure.</p>
            </div>
          </div>
          <div className="space-y-3">
            {supplyLeaders.map((leader) => (
              <button
                key={`${leader.theme}-${leader.ticker}`}
                type="button"
                onClick={() => onTickerSelect(leader.ticker)}
                className="flex w-full items-center justify-between gap-3 rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-3 text-left"
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm font-semibold text-[#E6EDF3]">{leader.ticker}</p>
                  <p className="truncate text-xs text-[#9BA7B4]">{leader.theme} - {leader.role ?? "leader"}</p>
                </div>
                <p className={typeof leader.change_percent !== "number" ? "font-mono text-sm font-semibold text-[#6E7681]" : leader.change_percent >= 0 ? "font-mono text-sm font-semibold text-emerald-300" : "font-mono text-sm font-semibold text-rose-300"}>
                  {typeof leader.change_percent === "number" ? pct(leader.change_percent) : "--"}
                </p>
              </button>
            ))}
            {loading && supplyLeaders.length === 0 && Array.from({ length: 4 }).map((_, index) => <ShimmerBlock key={index} className="h-16" />)}
            {!loading && supplyLeaders.length === 0 && (
              <EmptyState detail="Supply chain exposure will appear once the engine maps leaders to upstream, equipment, infrastructure and downstream roles." />
            )}
          </div>
        </section>

        <section className={cardClass}>
          <div className="mb-4 flex items-center gap-3">
            <ArrowDownRight className="text-rose-300" size={19} />
            <div>
              <p className="text-lg font-semibold tracking-wide text-[#E6EDF3]">Crowding Monitor / Risk Watch</p>
              <p className="mt-1 text-sm text-[#9BA7B4]">Overheated and undervalued theme divergence.</p>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-rose-300">Overheated Themes</p>
              {overheatedThemes.slice(0, 4).map((theme) => (
                <div key={theme.theme} className="mb-2 flex items-center justify-between rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2">
                  <span className="truncate text-sm text-[#C9D1D9]">{theme.theme}</span>
                  <span className="font-mono text-sm font-semibold text-rose-300">{formatOptionalScore(theme.overheating_score)}</span>
                </div>
              ))}
              {loading && overheatedThemes.length === 0 && <ShimmerBlock className="h-20" />}
              {!loading && overheatedThemes.length === 0 && (
                <EmptyState title="No overheated themes detected" detail="Crowding monitor has not identified a high-saturation theme cluster." />
              )}
            </div>
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-300">Undervalued Themes</p>
              {undervaluedThemes.slice(0, 4).map((theme) => (
                <div key={theme.theme} className="mb-2 flex items-center justify-between rounded-xl border border-[#2B313C] bg-[#111318] px-3 py-2">
                  <span className="truncate text-sm text-[#C9D1D9]">{theme.theme}</span>
                  <span className="font-mono text-sm font-semibold text-emerald-300">{formatOptionalScore(theme.theme_strength_score)}</span>
                </div>
              ))}
              {loading && undervaluedThemes.length === 0 && <ShimmerBlock className="h-20" />}
              {!loading && undervaluedThemes.length === 0 && (
                <EmptyState title="No undervalued themes detected" detail="Waiting for stronger divergence between theme strength and crowding risk." />
              )}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export default memo(ThemeIntelligenceDashboard);
