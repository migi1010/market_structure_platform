"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { fetchSectorRotation } from "@/services/stockApi";
import type { SectorRotation } from "@/types/stock";
import { BilingualLabel, ChangeCell, FlowIndicator, HeatStrip, MarketCell, MarketRow, MarketTable, NumericCell, SectorIcon, StatusDot, TickerCell, TickerLogo } from "./terminal";

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

const SECTOR_ROTATION_COLUMNS = "minmax(0,1fr) 62px 62px 62px 46px 100px";
const SECTOR_COMPANY_COLUMNS = "90px minmax(0,1fr) 70px 70px 70px 42px";

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

function finiteScore(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number.parseFloat(value.replace(/[$,%\s,]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
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

function scoreLabel(score: number | null | undefined): string {
  const value = finiteScore(score);
  if (value === null) return "Partial Data";
  if (value >= 90) return "Exceptional";
  if (value >= 75) return "Strong";
  if (value >= 50) return "Neutral";
  return "Weak";
}

function formatOptionalScore(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  return numeric === null ? "--" : numeric.toFixed(2);
}

function formatPercent(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  return numeric === null ? "--" : `${numeric >= 0 ? "+" : ""}${numeric.toFixed(2)}%`;
}

function formatRank(value: number | null | undefined): string {
  const numeric = finiteScore(value);
  return numeric === null ? "-" : numeric.toFixed(0);
}

function averageFinite(values: Array<number | null | undefined>): number | null {
  const finite = values.map(finiteScore).filter((value): value is number => value !== null);
  if (finite.length === 0) return null;
  return finite.reduce((sum, value) => sum + value, 0) / finite.length;
}

function firstFiniteScore(...values: Array<number | null | undefined>): number | null {
  for (const value of values) {
    const score = finiteScore(value);
    if (score !== null) return score;
  }
  return null;
}

function metricBarWidth(value: number | null | undefined): string {
  const score = finiteScore(value);
  if (score === null) return "0%";
  if (score < 0) return "0%";
  if (score > 100) return "100%";
  return `${score}%`;
}

function sectorFactorScore(sector: SectorRotation | undefined): number | null {
  if (!sector) return null;
  return finiteScore(sector.score);
}

function sectorExplanation(sector: SectorRotation | undefined, name: string): string {
  if (!sector) return `${name} live rotation data is calibrating.`;
  if (sector.capital_rotation) return sector.capital_rotation;
  const score = sectorFactorScore(sector);
  if (score === null) return `${sector.sector} rotation factors are warming.`;
  if (score >= 75) return `${sector.sector} is showing leadership with positive capital flow and relative momentum.`;
  if (score >= 50) return `${sector.sector} remains balanced; monitor breadth and institutional flow for confirmation.`;
  return `${sector.sector} is lagging the market with weaker flow and momentum conditions.`;
}

function SectorSkeleton() {
  return (
    <div className="miji-sector-heatmap grid auto-rows-[138px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 9 }).map((_, index) => (
        <div key={index} className="animate-pulse rounded-[8px] border border-[var(--theme-divider)] bg-[rgba(255,255,255,0.018)]" />
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
    if (sectors.length > 0 && !sectors.some((sector) => sector.sector.toLowerCase() === selectedSector.toLowerCase())) return;
    setActiveSector(selectedSector);
  }, [selectedSector, sectors]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      try {
        const snapshot = await fetchSectorRotation({ signal: controller.signal });
        const result = snapshot.sector_ranking;
        if (!cancelled) {
          setSectors(result);
          setActiveSector((current) => {
            const currentMatch = result.find((sector) => sector.sector.toLowerCase() === current.toLowerCase());
            if (currentMatch) return currentMatch.sector;
            const selectedMatch = selectedSector
              ? result.find((sector) => sector.sector.toLowerCase() === selectedSector.toLowerCase())
              : undefined;
            return selectedMatch?.sector ?? result?.[0]?.sector ?? "Technology";
          });
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
      controller.abort();
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

  const renderArray = sectors;
  const active = renderArray.find((sector) => sector.sector.toLowerCase() === activeSector.toLowerCase());
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
    () => Array.from(new Set([...CANONICAL_SECTORS, ...renderArray.map((sector) => sector.sector)])),
    [renderArray],
  );

  const selectSector = (sector: string) => {
    setActiveSector(sector);
    setSelectedSector(sector);
    setSectorDropdownOpen(false);
  };

  return (
    <section className="miji-page miji-sector-page bg-[var(--theme-bg)] p-5 text-[var(--theme-text)]">
      <div className="miji-page-header mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="terminal-micro-label">板塊輪動 Rotation</p>
          <h1 className="terminal-page-title mt-1 text-[var(--theme-text)]">資金輪動 Capital Rotation</h1>
          <p className="mt-2 text-sm text-[var(--theme-text-secondary)]">Strength, RS, flow, risk state.</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[var(--theme-muted)]"><Loader2 className="animate-spin" size={16} /> Loading live sector tape</div>}
      </div>

      <div className="mb-6 flex flex-wrap gap-x-6 gap-y-2 border-y border-[rgba(255,255,255,0.026)] py-4 text-sm">
        <span><span className="text-[var(--theme-muted)]">Leadership</span> <b className="text-[var(--theme-text)]">{renderArray?.[0]?.sector ?? "Calibrating"}</b></span>
        <span><span className="text-[var(--theme-muted)]">Avg Strength</span> <b className="font-mono text-[var(--theme-warning)]">{formatOptionalScore(averageFinite(renderArray.map(sectorFactorScore)))}</b></span>
        <span><span className="text-[var(--theme-muted)]">Flow</span> <b className="font-mono text-[var(--theme-bullish)]">{formatOptionalScore(active?.flow)}</b></span>
        <span><span className="text-[var(--theme-muted)]">Rotation</span> <b className="text-[var(--theme-text)]">{active?.rotation_state ?? active?.narrative_state?.replaceAll("_", " ") ?? active?.leadership_state ?? scoreLabel(active?.score)}</b></span>
      </div>

      <div className="miji-sector-grid grid gap-6 xl:grid-cols-[minmax(0,1fr)_500px]">
        {loading && renderArray.length === 0 ? (
          <SectorSkeleton />
        ) : (
          <MarketTable
            columns={SECTOR_ROTATION_COLUMNS}
            header={
              <>
                <MarketCell><BilingualLabel zh="板塊" en="Sector" /></MarketCell>
                <NumericCell>強度</NumericCell>
                <NumericCell>RS</NumericCell>
                <NumericCell>資金</NumericCell>
                <MarketCell>熱度</MarketCell>
                <MarketCell className="text-right">狀態</MarketCell>
              </>
            }
            className="terminal-panel p-3"
          >
            {renderArray.map((sector) => {
              return (
                <MarketRow
                  key={sector.sector}
                  onClick={() => selectSector(sector.sector)}
                  columns={SECTOR_ROTATION_COLUMNS}
                  selected={activeSector === sector.sector}
                >
                  <MarketCell className="truncate text-sm font-semibold text-[var(--theme-text)]">
                    <span className="flex min-w-0 items-center gap-2">
                      <SectorIcon sector={sector.sector} />
                      <span className="min-w-0">
                        <span className="block truncate">{sector.sector}</span>
                        <span className="mt-0.5 block truncate text-[10px] font-medium text-[var(--theme-muted)]">{sector.momentum_direction ?? sector.leadership_state ?? "Rotation"}</span>
                      </span>
                    </span>
                  </MarketCell>
                  <NumericCell className="text-sm font-semibold text-[var(--theme-text)]">{formatOptionalScore(sector.score)}</NumericCell>
                  <NumericCell className="text-sm font-semibold text-[var(--theme-text-secondary)]">{formatOptionalScore(sector.relative_strength)}</NumericCell>
                  <NumericCell><FlowIndicator value={finiteScore(sector.flow)} /></NumericCell>
                  <MarketCell><HeatStrip value={finiteScore(sector.score)} /></MarketCell>
                  <MarketCell className="truncate text-right"><StatusDot state={sector.rotation_state ?? sector.lifecycle_state} label={sector.rotation_state ?? scoreLabel(sector.score)} /></MarketCell>
                </MarketRow>
              );
            })}
          </MarketTable>
        )}

        <aside id="sector-drilldown" tabIndex={-1} className="terminal-panel p-5 outline-none ring-0">
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
              <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">板塊焦點 Sector Focus</p>
              <h2 className="text-2xl font-semibold tracking-wide text-[var(--theme-text)]">{active?.sector ?? activeSector}</h2>
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">
                {active?.momentum_direction ? `${active.momentum_direction} / rank ${formatRank(active.sector_rank)}` : "Workspace Focus"}
              </p>
              </div>
              <ChevronDown className={`shrink-0 text-[var(--theme-muted)] transition ${sectorDropdownOpen ? "rotate-180" : ""}`} size={20} />
            </button>
            {sectorDropdownOpen && (
              <div className="absolute left-0 right-0 top-full z-[80] mt-3 max-h-[60dvh] overflow-y-auto rounded-[8px] border border-[var(--theme-divider)] bg-[var(--theme-bg)] p-1">
                {sectorOptions.map((sector) => (
                  <button
                    key={sector}
                    type="button"
                    onClick={() => selectSector(sector)}
                    onTouchStart={(event) => {
                      event.preventDefault();
                      selectSector(sector);
                    }}
                    className={`w-full rounded-[6px] px-2.5 py-2 text-left text-sm font-semibold tracking-wide transition ${
                      activeSector === sector ? "bg-[rgba(255,255,255,0.045)] text-[var(--theme-text)]" : "text-[var(--theme-muted)] hover:bg-[rgba(255,255,255,0.028)] hover:text-[var(--theme-text)]"
                    }`}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="mb-6 border-y border-[rgba(255,255,255,0.026)] py-5">
            <p className="text-sm font-semibold tracking-wide text-[var(--theme-text)]">狀態摘要 State</p>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--theme-muted)]">{sectorExplanation(active, activeSector)}</p>
            {active?.leadership_intelligence?.explanation && (
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--theme-text-secondary)]">{active.leadership_intelligence.explanation}</p>
            )}
            {active?.narrative_intelligence?.explanation && (
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--theme-warning)]/80">{active.narrative_intelligence.explanation}</p>
            )}
            {activeRanking?.explanation && (
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--theme-text-secondary)]">{activeRanking.explanation}</p>
            )}
            <div className="mt-4 space-y-3">
              {[
                ["Strength", sectorFactorScore(active)],
                ["Capital Flow", active?.flow],
                ["Relative Momentum", active?.relative_strength],
                ["Acceleration", active?.acceleration],
                ["Bubble Risk", averageFinite(activeCompanies.map((item) => item.bubble_score))],
              ].map(([label, value]) => (
                <div key={label as string}>
                  <div className="mb-1 flex justify-between text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">
                    <span>{label}</span>
                    <span className="font-mono text-[var(--theme-text-secondary)]">{formatOptionalScore(value as number | null | undefined)}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[var(--theme-bg)]">
                    <div className="h-full rounded-full bg-[var(--theme-warning)]" style={{ width: metricBarWidth(value as number | null | undefined) }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            {(active?.companies ?? []).length === 0 && (
              <div className="py-4 text-sm text-[var(--theme-muted)]">
                Using latest cached sector constituents while live {activeSector} rotation data warms up.
              </div>
            )}
            <MarketTable
              columns={SECTOR_COMPANY_COLUMNS}
              className="p-0"
              header={
                <>
                  <MarketCell>股票</MarketCell>
                  <MarketCell>公司</MarketCell>
                  <NumericCell>動能</NumericCell>
                  <NumericCell>Alpha</NumericCell>
                  <NumericCell>Bubble</NumericCell>
                  <MarketCell>熱度</MarketCell>
                </>
              }
            >
              {activeCompanies.map((company) => {
                const change = finiteScore(company.change_percent);
                const bubble = finiteScore(company.bubble_score);
                return (
                  <MarketRow key={company.ticker} columns={SECTOR_COMPANY_COLUMNS} onClick={() => onTickerSelect(company.ticker)}>
                    <TickerCell>
                      <span className="flex items-center gap-2"><TickerLogo ticker={company.ticker} /><span className="truncate">{company.ticker}</span></span>
                      <span className="mt-0.5 block text-[10px] font-normal text-[var(--theme-muted)]">#{company.sector_rank ?? "-"}</span>
                    </TickerCell>
                    <MarketCell className="min-w-0">
                      <span className="block truncate text-sm font-medium text-[var(--theme-text-secondary)]">{sanitizeCompanyName(company.company_name)}</span>
                      <span className="mt-0.5 block truncate text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Cap {money(company.market_cap)} / RS {formatOptionalScore(company.relative_strength)}</span>
                    </MarketCell>
                    <ChangeCell value={change} className="text-sm font-semibold">{formatPercent(company.change_percent)}</ChangeCell>
                    <NumericCell className="text-sm font-semibold text-[var(--theme-warning)]">{formatOptionalScore(company.alpha_score)}</NumericCell>
                    <NumericCell className={(bubble ?? -Infinity) >= 70 ? "text-sm font-semibold text-[var(--theme-bearish)]" : "text-sm font-semibold text-[var(--theme-text-secondary)]"}>{formatOptionalScore(company.bubble_score)}</NumericCell>
                    <MarketCell><HeatStrip value={company.alpha_score} /></MarketCell>
                  </MarketRow>
                );
              })}
            </MarketTable>
          </div>
        </aside>
      </div>
    </section>
  );
}
