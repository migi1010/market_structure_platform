"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Loader2, Radar } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { fetchSectorRotation } from "@/services/stockApi";
import type { SectorRotation } from "@/types/stock";

interface SectorRotationPanelProps {
  onTickerSelect: (ticker: string) => void;
}

const CANONICAL_SECTORS = [
  "Semiconductors",
  "Technology",
  "Energy",
  "Healthcare",
  "Financials",
  "Industrials",
  "Utilities",
  "Consumer Discretionary",
  "Consumer Staples",
  "Materials",
  "Real Estate",
  "Communication Services",
];

const FALLBACK_COMPANIES: Record<string, string[]> = {
  Technology: ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "PLTR"],
  Energy: ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"],
  Healthcare: ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"],
  Financials: ["JPM", "BAC", "GS", "MS", "V", "MA"],
  Industrials: ["GE", "CAT", "BA", "HON", "UPS", "RTX"],
  Utilities: ["NEE", "SO", "DUK", "AEP", "SRE", "D"],
  "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX"],
  "Consumer Staples": ["WMT", "COST", "PG", "KO", "PEP", "PM"],
  Materials: ["LIN", "SHW", "APD", "ECL", "FCX", "NEM"],
  "Real Estate": ["PLD", "AMT", "EQIX", "WELL", "SPG", "O"],
  "Communication Services": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "TMUS"],
};

function finiteScore(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function money(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  if (numeric === null) return "--";
  const abs = Math.abs(numeric);
  if (abs >= 1e12) return `$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(2)}M`;
  return `$${abs.toFixed(0)}`;
}

function gradient(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "from-[#1C2128] to-[#111318]";
  if (value >= 90) return "from-emerald-300 to-teal-400";
  if (value >= 75) return "from-emerald-500 to-cyan-500";
  if (value >= 50) return "from-slate-500 to-slate-700";
  if (value >= 25) return "from-orange-500 to-rose-500";
  return "from-rose-600 to-red-700";
}

function scoreLabel(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "Partial Data";
  if (value >= 90) return "Exceptional";
  if (value >= 75) return "Strong";
  if (value >= 50) return "Neutral";
  if (value >= 25) return "Weak";
  return "Distressed";
}

function formatOptionalScore(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "--";
}

function formatPercent(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  return numeric === null ? "--" : `${numeric >= 0 ? "+" : ""}${numeric.toFixed(2)}%`;
}

function averageFinite(values: Array<number | null | undefined>): number | null {
  const finite = values.map(finiteScore).filter((value): value is number => value !== null);
  if (finite.length === 0) return null;
  return finite.reduce((sum, value) => sum + value, 0) / finite.length;
}

function sectorExplanation(sector: SectorRotation | undefined, name: string): string {
  if (!sector) return `${name} live rotation data is calibrating.`;
  if (sector.capital_rotation) return sector.capital_rotation;
  const score = finiteScore(sector.score);
  if (score === null) return `${sector.sector} rotation factors are warming.`;
  if (score >= 75) return `${sector.sector} is showing leadership with positive capital flow and relative momentum.`;
  if (score >= 50) return `${sector.sector} remains balanced; monitor breadth and institutional flow for confirmation.`;
  return `${sector.sector} is lagging the market with weaker flow and momentum conditions.`;
}

function SectorSkeleton() {
  return (
    <div className="miji-sector-heatmap grid auto-rows-[138px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 9 }).map((_, index) => (
        <div key={index} className="animate-pulse rounded-2xl border border-[#2B313C] bg-[#1C2128]" />
      ))}
    </div>
  );
}

export default function SectorRotationPanel({ onTickerSelect }: SectorRotationPanelProps) {
  const { selectedSector, setSelectedSector } = useWorkspace();
  const [sectors, setSectors] = useState<SectorRotation[]>([]);
  const [activeSector, setActiveSector] = useState<string>(selectedSector || "Technology");
  const [sectorDropdownOpen, setSectorDropdownOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!selectedSector) return;
    setActiveSector(selectedSector);
  }, [selectedSector]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await fetchSectorRotation();
        if (!cancelled) {
          setSectors(result);
          setActiveSector((current) => current || result?.[0]?.sector || selectedSector || "Technology");
        }
      } catch {
        if (!cancelled) setSectors([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onOutside(event: MouseEvent | TouchEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setSectorDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside, { passive: true });
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
    };
  }, []);

  const active = sectors.find((sector) => sector.sector.toLowerCase() === activeSector.toLowerCase());
  const activeRanking = active?.universe_ranking;
  const activeCompanies = useMemo(() => {
    if ((active?.companies ?? []).length > 0) return active?.companies ?? [];
    return (FALLBACK_COMPANIES[activeSector] ?? []).map((ticker, index) => ({
      ticker,
      company_name: ticker,
      market_cap: null,
      alpha_score: null,
      bubble_score: null,
      relative_strength: null,
      change_percent: null,
      sector_rank: index + 1,
    }));
  }, [active?.companies, activeSector]);
  const sectorOptions = useMemo(
    () => Array.from(new Set([...CANONICAL_SECTORS, ...sectors.map((sector) => sector.sector)])),
    [sectors],
  );

  const selectSector = (sector: string) => {
    setActiveSector(sector);
    setSelectedSector(sector);
    setSectorDropdownOpen(false);
  };

  return (
    <section className="miji-page miji-sector-page bg-[#0A0C10] p-5 text-[#E6EDF3]">
      <div className="miji-page-header mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Capital Rotation System</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Sector Rotation Heatmap</h1>
          <p className="mt-2 text-sm text-[#9BA7B4]">Momentum, relative strength, volume participation, cap-weighted flow, volatility and bubble risk.</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Loading live sector tape</div>}
      </div>

      <div className="miji-card-grid mb-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Leadership</p>
          <p className="mt-2 text-xl font-semibold text-[#E6EDF3]">{sectors?.[0]?.sector ?? "Calibrating"}</p>
          <p className="mt-1 text-sm text-[#9BA7B4]">Top sector by composite strength</p>
        </div>
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Avg Strength</p>
          <p className="mt-2 font-mono text-xl font-semibold text-amber-200">{formatOptionalScore(averageFinite(sectors.map((item) => item.score)))}</p>
          <p className="mt-1 text-sm text-[#9BA7B4]">Across institutional sector universe</p>
        </div>
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Flow Bias</p>
          <p className="mt-2 font-mono text-xl font-semibold text-emerald-300">{formatOptionalScore(active?.flow)}</p>
          <p className="mt-1 text-sm text-[#9BA7B4]">{active?.sector ?? activeSector} capital flow score</p>
        </div>
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Screener Rank</p>
          <p className="mt-2 font-mono text-xl font-semibold text-amber-200">{formatOptionalScore(activeRanking?.ranking_score)}</p>
          <p className="mt-1 text-sm text-[#9BA7B4]">{activeRanking?.market_classification?.replaceAll("_", " ") ?? "Awaiting factors"}</p>
        </div>
        <div className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Rotation State</p>
          <p className="mt-2 text-xl font-semibold text-[#E6EDF3]">{active?.narrative_state?.replaceAll("_", " ") ?? active?.leadership_state ?? active?.rotation_state ?? scoreLabel(active?.score)}</p>
          <p className="mt-1 text-sm text-[#9BA7B4]">Momentum and risk-adjusted sector status</p>
        </div>
      </div>

      <div className="miji-sector-grid grid gap-5 xl:grid-cols-[minmax(0,1fr)_500px]">
        {loading && sectors.length === 0 ? (
          <SectorSkeleton />
        ) : (
          <div className="miji-sector-heatmap grid auto-rows-[148px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sectors.map((sector) => (
              <motion.button
                key={sector.sector}
                onClick={() => selectSector(sector.sector)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className={`miji-card relative overflow-hidden rounded-2xl border p-5 text-left shadow-[0_4px_24px_rgba(0,0,0,0.25)] transition ${
                  activeSector === sector.sector ? "border-amber-400/30" : "border-[#2B313C]"
                } bg-gradient-to-br ${gradient(sector.score)}`}
              >
                <div className="absolute inset-0 bg-[#0A0C10]/20" />
                <div className="relative flex h-full flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-semibold tracking-wide text-[#E6EDF3]">{sector.sector}</span>
                    <Radar size={18} className="text-[#E6EDF3]/75" />
                  </div>
                  <div>
                    <div className="flex items-end justify-between">
                      <p className="font-mono text-4xl font-semibold text-[#E6EDF3]">{formatOptionalScore(sector.score)}</p>
                      <span className="rounded-lg border border-white/20 bg-black/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#E6EDF3]/85">{scoreLabel(sector.score)}</span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] font-semibold uppercase tracking-wide text-[#E6EDF3]/80">
                      <span>RS {formatOptionalScore(sector.relative_strength)}</span>
                      <span>Flow {formatOptionalScore(sector.flow)}</span>
                    </div>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        )}

        <aside id="sector-drilldown" tabIndex={-1} className="miji-card rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] outline-none ring-0 backdrop-blur-md">
          <div ref={dropdownRef} className="relative z-30 mb-5">
            <button
              type="button"
              onClick={() => setSectorDropdownOpen((open) => !open)}
              onTouchStart={(event) => {
                event.preventDefault();
                setSectorDropdownOpen((open) => !open);
              }}
              className="flex w-full items-center justify-between gap-4 text-left"
              aria-expanded={sectorDropdownOpen}
              aria-label="Select sector"
            >
              <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Sector Drilldown</p>
              <h2 className="text-2xl font-semibold tracking-wide text-[#E6EDF3]">{active?.sector ?? activeSector}</h2>
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">
                {active?.momentum_direction ? `${active.momentum_direction} / rank ${active.sector_rank ?? "--"}` : "Workspace Focus"}
              </p>
              </div>
              <ChevronDown className={`shrink-0 text-[#9BA7B4] transition ${sectorDropdownOpen ? "rotate-180" : ""}`} size={20} />
            </button>
            {sectorDropdownOpen && (
              <div className="absolute left-0 right-0 top-full z-[80] mt-3 max-h-[60dvh] overflow-y-auto rounded-2xl border border-[#2B313C] bg-[#0A0C10]/98 p-2 shadow-[0_18px_48px_rgba(0,0,0,0.48)] backdrop-blur-md">
                {sectorOptions.map((sector) => (
                  <button
                    key={sector}
                    type="button"
                    onClick={() => selectSector(sector)}
                    onTouchStart={(event) => {
                      event.preventDefault();
                      selectSector(sector);
                    }}
                    className={`w-full rounded-xl px-3 py-3 text-left text-sm font-semibold tracking-wide transition ${
                      activeSector === sector ? "bg-[#1D2430] text-[#E6EDF3]" : "text-[#9BA7B4] hover:bg-[#151922] hover:text-[#E6EDF3]"
                    }`}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="mb-5 rounded-2xl border border-[#2B313C] bg-[#111318] p-4">
            <p className="text-sm font-semibold tracking-wide text-[#E6EDF3]">Sector Explanation</p>
            <p className="mt-2 text-sm leading-relaxed text-[#9BA7B4]">{sectorExplanation(active, activeSector)}</p>
            {active?.leadership_intelligence?.explanation && (
              <p className="mt-2 text-sm leading-relaxed text-[#C9D1D9]">{active.leadership_intelligence.explanation}</p>
            )}
            {active?.narrative_intelligence?.explanation && (
              <p className="mt-2 text-sm leading-relaxed text-amber-100/80">{active.narrative_intelligence.explanation}</p>
            )}
            {activeRanking?.explanation && (
              <p className="mt-2 text-sm leading-relaxed text-[#C9D1D9]">{activeRanking.explanation}</p>
            )}
            <div className="mt-4 space-y-3">
              {[
                ["Strength", active?.score],
                ["Capital Flow", active?.flow],
                ["Relative Momentum", active?.relative_strength],
                ["Narrative Velocity", active?.acceleration_velocity],
                ["Bubble Risk", averageFinite(activeCompanies.map((item) => item.bubble_score))],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div className="mb-1 flex justify-between text-[11px] font-semibold uppercase tracking-wide text-[#9BA7B4]">
                    <span>{label}</span>
                    <span className="font-mono text-[#C9D1D9]">{formatOptionalScore(value as number | null | undefined)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[#0A0C10]">
                    <div className="h-full rounded-full bg-amber-200" style={{ width: `${finiteScore(value as number | null | undefined) === null ? 0 : Math.min(100, Math.max(0, Number(value)))}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            {(active?.companies ?? []).length === 0 && (
              <div className="rounded-xl border border-[#2B313C] bg-[#111318] p-4 text-sm text-[#9BA7B4]">
                Using latest cached sector constituents while live {activeSector} rotation data warms up.
              </div>
            )}
            {activeCompanies.map((company) => (
              <button
                key={company.ticker}
                onClick={() => onTickerSelect(company.ticker)}
                className="group w-full rounded-xl border border-[#2B313C] bg-[#111318] p-4 text-left transition hover:border-amber-400/20"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-mono text-xl font-semibold text-[#E6EDF3] group-hover:text-amber-200">{company.ticker}</p>
                      <span className="rounded border border-[#2B313C] px-1.5 py-0.5 text-[10px] font-semibold text-[#9BA7B4]">#{company.sector_rank ?? "-"}</span>
                    </div>
                    <p className="mt-1 truncate text-sm text-[#9BA7B4]">{sanitizeCompanyName(company.company_name)}</p>
                  </div>
                  <span className={finiteScore(company.change_percent) === null ? "font-mono text-sm font-semibold text-[#6E7681]" : Number(company.change_percent) >= 0 ? "font-mono text-sm font-semibold text-emerald-300" : "font-mono text-sm font-semibold text-rose-300"}>
                    {formatPercent(company.change_percent)}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-4 gap-2 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">
                  <span>Cap <b className="block text-[#C9D1D9]">{money(company.market_cap)}</b></span>
                  <span>Alpha <b className="block text-amber-200">{formatOptionalScore(company.alpha_score)}</b></span>
                  <span>Bubble <b className={Number(company.bubble_score) >= 70 ? "block text-rose-300" : "block text-[#C9D1D9]"}>{formatOptionalScore(company.bubble_score)}</b></span>
                  <span>RS <b className="block text-emerald-300">{formatOptionalScore(company.relative_strength)}</b></span>
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
