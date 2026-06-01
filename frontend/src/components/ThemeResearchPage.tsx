"use client";

import { useEffect, useMemo, useState } from "react";
import { Activity, BarChart3, Boxes, ChevronRight, Layers3, LineChart, ShieldAlert, Target, Workflow } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  fetchSectorRotation,
  fetchThemeCapitalFlow,
  fetchThemeDetail,
  fetchThemeEmerging,
  fetchThemeForecast,
  fetchThemeForecastValidation,
  fetchThemeNarrative,
  fetchThemeRotation,
  fetchThemeSupplyChain,
  fetchThemeTop,
} from "@/services/stockApi";
import type {
  ForecastHorizon,
  SectorRotation,
  ThemeDetailResponse,
  ThemeForecastRecord,
  ThemeForecastValidationResponse,
  ThemeLeader,
  ThemeNarrativeResponse,
  ThemeScore,
  ThemeSupplyChainResponse,
} from "@/types/stock";
import { TerminalPanel } from "./terminal";

type ThemeResearchTab = "command" | "forecast" | "rotation" | "stocks" | "supply-chain" | "risk";

interface ThemeResearchPageProps {
  onTickerSelect?: (ticker: string) => void;
}

interface ThemeDataState {
  topThemes: ThemeScore[];
  emergingThemes: ThemeScore[];
  rotationMap: ThemeScore[];
  capitalFlow: Array<Partial<ThemeScore> & { theme: string; category: string }>;
  sectors: SectorRotation[];
  narratives: ThemeNarrativeResponse | null;
  supplyChain: ThemeSupplyChainResponse | null;
  detail: ThemeDetailResponse | null;
  forecast: ThemeForecastRecord[];
  validation: ThemeForecastValidationResponse | null;
  loading: boolean;
}

const THEME_TABS: Array<{ id: ThemeResearchTab; labelZh: string; labelEn: string; icon: typeof Activity }> = [
  { id: "command", labelZh: "指揮", labelEn: "Command", icon: Target },
  { id: "forecast", labelZh: "預測", labelEn: "Forecast", icon: LineChart },
  { id: "rotation", labelZh: "輪動", labelEn: "Rotation", icon: Workflow },
  { id: "stocks", labelZh: "個股", labelEn: "Stocks", icon: BarChart3 },
  { id: "supply-chain", labelZh: "供應鏈", labelEn: "Supply Chain", icon: Boxes },
  { id: "risk", labelZh: "風險", labelEn: "Risk", icon: ShieldAlert },
];

const TAB_ALIASES: Record<string, ThemeResearchTab> = {
  command: "command",
  forecast: "forecast",
  rotation: "rotation",
  stocks: "stocks",
  "supply-chain": "supply-chain",
  risk: "risk",
};

const EMPTY_STATE: ThemeDataState = {
  topThemes: [],
  emergingThemes: [],
  rotationMap: [],
  capitalFlow: [],
  sectors: [],
  narratives: null,
  supplyChain: null,
  detail: null,
  forecast: [],
  validation: null,
  loading: true,
};

function finite(value: unknown): number | null {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

function formatScore(value: unknown, digits = 1): string {
  const numberValue = finite(value);
  return numberValue === null ? "--" : numberValue.toFixed(digits);
}

function formatPercent(value: unknown, digits = 1): string {
  const numberValue = finite(value);
  if (numberValue === null) return "--";
  return `${numberValue >= 0 ? "+" : ""}${numberValue.toFixed(digits)}%`;
}

function themeScore(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.score)
    ?? finite(theme?.theme_strength_score)
    ?? finite(theme?.leadership_score)
    ?? finite(theme?.ranking_score)
    ?? finite(theme?.narrative_strength)
    ?? finite(theme?.relative_strength_vs_spy);
}

function themeFlow(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.flow)
    ?? finite(theme?.theme_capital_flow_score)
    ?? finite(theme?.institutional_alignment)
    ?? finite(theme?.participation_breadth)
    ?? finite(theme?.volume_expansion);
}

function themeMomentum(theme: Partial<ThemeScore> | null | undefined): number | null {
  return finite(theme?.momentum)
    ?? finite(theme?.momentum_strength)
    ?? finite(theme?.relative_momentum)
    ?? finite(theme?.acceleration_velocity)
    ?? finite(theme?.trend_consistency);
}

function themeName(theme: Partial<ThemeScore> | null | undefined): string {
  return theme?.theme ?? "Theme";
}

function classForScore(value: unknown): string {
  const numberValue = finite(value);
  if (numberValue === null) return "text-[var(--theme-muted)]";
  if (numberValue >= 70) return "text-[var(--theme-bullish)]";
  if (numberValue <= 40) return "text-[var(--theme-bearish)]";
  return "text-[var(--theme-warning)]";
}

function compactLifecycle(value?: string | null): string {
  return value ? value.replace(/_/g, " ") : "partial live";
}

function topLeaders(detail: ThemeDetailResponse | null, activeTheme: ThemeScore | null): ThemeLeader[] {
  const detailRows = [...(detail?.top_alpha_stocks ?? []), ...(detail?.related_stocks ?? [])];
  const themeRows = [...(activeTheme?.top_alpha_stocks ?? []), ...(activeTheme?.related_stocks ?? []), ...(activeTheme?.leaders ?? [])];
  const rows = detailRows.length > 0 ? detailRows : themeRows;
  const seen = new Set<string>();
  return rows.filter((row) => {
    const ticker = row.ticker?.toUpperCase();
    if (!ticker || seen.has(ticker)) return false;
    seen.add(ticker);
    return true;
  }).slice(0, 10);
}

function supplyRoles(supplyChain: ThemeSupplyChainResponse | null, selectedTheme: string): Array<{ role: string; leaders: ThemeLeader[] }> {
  const row = supplyChain?.themes?.find((item) => item.theme.toLowerCase() === selectedTheme.toLowerCase()) ?? supplyChain?.themes?.[0];
  return Object.entries(row?.supply_chain ?? {}).slice(0, 6).map(([role, leaders]) => ({ role, leaders: leaders.slice(0, 4) }));
}

function forecastForTheme(records: ThemeForecastRecord[], theme: string): ThemeForecastRecord | null {
  return records.find((record) => record.theme.toLowerCase() === theme.toLowerCase()) ?? records[0] ?? null;
}

function ThemeRankRow({
  theme,
  active,
  onSelect,
}: {
  theme: ThemeScore;
  active: boolean;
  onSelect: (theme: string) => void;
}) {
  const score = themeScore(theme);
  return (
    <button
      type="button"
      onClick={() => onSelect(theme.theme)}
      className={`flex w-full items-center justify-between gap-3 rounded-[10px] border px-3 py-2 text-left transition ${
        active ? "border-[var(--theme-border-strong)] bg-[var(--theme-panel-hover)]" : "border-[var(--theme-border)] bg-[var(--theme-panel-inset)] hover:border-[var(--theme-border-strong)]"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[var(--theme-text)]">{theme.theme}</span>
        <span className="mt-0.5 block truncate text-[11px] text-[var(--theme-muted)]">{theme.category || theme.status || "Theme basket"}</span>
      </span>
      <span className={`font-mono text-lg font-semibold ${classForScore(score)}`}>{formatScore(score)}</span>
    </button>
  );
}

function SectorRow({ sector, active, onSelect }: { sector: SectorRotation; active: boolean; onSelect: (sector: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(sector.sector)}
      className={`grid w-full grid-cols-[1fr_auto] gap-3 rounded-[10px] border px-3 py-2 text-left transition ${
        active ? "border-[var(--theme-border-strong)] bg-[var(--theme-panel-hover)]" : "border-[var(--theme-border)] bg-[var(--theme-panel-inset)] hover:border-[var(--theme-border-strong)]"
      }`}
    >
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-[var(--theme-text)]">{sector.sector}</span>
        <span className="mt-0.5 block text-[11px] text-[var(--theme-muted)]">RS {formatScore(sector.relative_strength)} · Flow {formatScore(sector.flow)}</span>
      </span>
      <span className={`font-mono text-lg font-semibold ${classForScore(sector.score)}`}>{formatScore(sector.score)}</span>
    </button>
  );
}

function BeneficiaryList({ rows, onTickerSelect }: { rows: ThemeLeader[]; onTickerSelect?: (ticker: string) => void }) {
  return (
    <div className="space-y-2">
      {rows.length === 0 ? (
        <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3 text-sm text-[var(--theme-muted)]">No beneficiary stock payload yet.</div>
      ) : rows.map((row) => (
        <button
          key={`${row.ticker}-${row.role ?? "leader"}`}
          type="button"
          onClick={() => row.ticker && onTickerSelect?.(row.ticker)}
          className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] px-3 py-2 text-left transition hover:border-[var(--theme-border-strong)]"
        >
          <span className="font-mono text-base font-semibold text-[var(--theme-text)]">{row.ticker}</span>
          <span className="min-w-0">
            <span className="block truncate text-xs text-[var(--theme-text-secondary)]">{row.company_name || row.role || "Theme leader"}</span>
            <span className="block truncate text-[10px] uppercase text-[var(--theme-muted)]">{row.role || row.quote_status || "beneficiary"}</span>
          </span>
          <span className={`font-mono text-sm font-semibold ${classForScore(row.alpha_score ?? row.confidence_score ?? row.change_percent)}`}>
            {finite(row.alpha_score) !== null ? formatScore(row.alpha_score) : formatPercent(row.change_percent)}
          </span>
        </button>
      ))}
    </div>
  );
}

function ForecastTab({
  forecast,
  validation,
  selectedTheme,
}: {
  forecast: ThemeForecastRecord[];
  validation: ThemeForecastValidationResponse | null;
  selectedTheme: string;
}) {
  const selectedForecast = forecastForTheme(forecast, selectedTheme);
  return (
    <div id="theme-forecast" tabIndex={-1} className="grid gap-4 outline-none xl:grid-cols-[1.2fr_0.8fr]">
      <TerminalPanel
        eyebrow="預測 Forecast"
        title={selectedForecast ? `${selectedForecast.theme} Forecast Alignment` : "Theme Forecast AI"}
        description="Forward-looking theme ranking with confidence, risk, crowding, and regime context."
      >
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
            <p className="terminal-micro-label">Forecast Score</p>
            <p className={`mt-2 font-mono text-3xl font-semibold ${classForScore(selectedForecast?.forecast_score)}`}>{formatScore(selectedForecast?.forecast_score)}</p>
          </div>
          <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
            <p className="terminal-micro-label">Expected Excess</p>
            <p className={`mt-2 font-mono text-3xl font-semibold ${classForScore(selectedForecast?.expected_excess_return)}`}>{formatPercent(selectedForecast?.expected_excess_return)}</p>
          </div>
          <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
            <p className="terminal-micro-label">Probability</p>
            <p className={`mt-2 font-mono text-3xl font-semibold ${classForScore((selectedForecast?.outperformance_probability ?? 0) * 100)}`}>{selectedForecast?.outperformance_probability !== null && selectedForecast?.outperformance_probability !== undefined ? `${(selectedForecast.outperformance_probability * 100).toFixed(1)}%` : "--"}</p>
          </div>
        </div>
        <div className="mt-4 rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-4 text-sm leading-relaxed text-[var(--theme-text-secondary)]">
          {selectedForecast?.explanation || "Forecast engine is warming. Live theme research remains available from lightweight factors."}
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
            <p className="terminal-micro-label">Positive Drivers</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--theme-text-secondary)]">
              {(selectedForecast?.top_positive_drivers ?? []).slice(0, 5).map((driver) => <li key={driver}>+ {driver}</li>)}
            </ul>
          </div>
          <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
            <p className="terminal-micro-label">Negative Drivers</p>
            <ul className="mt-2 space-y-1 text-sm text-[var(--theme-text-secondary)]">
              {(selectedForecast?.top_negative_drivers ?? []).slice(0, 5).map((driver) => <li key={driver}>- {driver}</li>)}
            </ul>
          </div>
        </div>
      </TerminalPanel>
      <TerminalPanel eyebrow="驗證 Validation" title="Walk-Forward Discipline" description="Forecast performance is chronological only; no random shuffle validation.">
        <div className="grid grid-cols-2 gap-3">
          {[
            ["Hit Rate", validation?.hit_rate],
            ["Precision@5", validation?.precision_at_5],
            ["Info Ratio", validation?.information_ratio],
            ["Stability", validation?.excess_return_stability],
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
              <p className="terminal-micro-label">{String(label)}</p>
              <p className="mt-1 font-mono text-xl font-semibold text-[var(--theme-text)]">{formatScore(value)}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] p-3 text-xs leading-relaxed text-[var(--theme-muted)]">
          Status: {compactLifecycle(validation?.lifecycle_state)} · Observations: {validation?.observations ?? 0}
        </div>
      </TerminalPanel>
    </div>
  );
}

export default function ThemeResearchPage({ onTickerSelect }: ThemeResearchPageProps) {
  const {
    selectedTheme,
    selectedSector,
    selectedThemeView,
    setSelectedTheme,
    setSelectedSector,
    setSelectedThemeView,
  } = useWorkspace();
  const [horizon] = useState<ForecastHorizon>("1m");
  const [data, setData] = useState<ThemeDataState>(EMPTY_STATE);
  const activeTab = TAB_ALIASES[selectedThemeView] ?? "command";

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setData((current) => ({ ...current, loading: true }));
      const [top, emerging, rotation, flow, sectors, narratives, forecast, validation] = await Promise.all([
        fetchThemeTop().catch(() => null),
        fetchThemeEmerging().catch(() => null),
        fetchThemeRotation().catch(() => null),
        fetchThemeCapitalFlow().catch(() => null),
        fetchSectorRotation().catch(() => [] as SectorRotation[]),
        fetchThemeNarrative().catch(() => null),
        fetchThemeForecast(horizon).catch(() => null),
        fetchThemeForecastValidation(horizon).catch(() => null),
      ]);
      if (cancelled) return;
      setData((current) => ({
        ...current,
        topThemes: top?.themes ?? [],
        emergingThemes: emerging?.emerging_themes ?? [],
        rotationMap: rotation?.rotation_map ?? [],
        capitalFlow: flow?.capital_flow ?? [],
        sectors: sectors ?? [],
        narratives,
        forecast: forecast?.forecasts?.length ? forecast.forecasts : [...(forecast?.top_future_themes ?? []), ...(forecast?.emerging_themes ?? [])],
        validation,
        loading: false,
      }));
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [horizon]);

  const selectedThemeName = selectedTheme || data.topThemes[0]?.theme || data.capitalFlow[0]?.theme || "AI Infrastructure";

  useEffect(() => {
    if (!selectedTheme && selectedThemeName) setSelectedTheme(selectedThemeName);
  }, [selectedTheme, selectedThemeName, setSelectedTheme]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      const [detail, supplyChain] = await Promise.all([
        fetchThemeDetail(selectedThemeName).catch(() => null),
        fetchThemeSupplyChain(selectedThemeName).catch(() => null),
      ]);
      if (!cancelled) {
        setData((current) => ({ ...current, detail, supplyChain }));
      }
    }
    if (selectedThemeName) void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedThemeName]);

  const activeTheme = useMemo(() => {
    const lower = selectedThemeName.toLowerCase();
    return data.topThemes.find((theme) => theme.theme.toLowerCase() === lower)
      ?? data.rotationMap.find((theme) => theme.theme.toLowerCase() === lower)
      ?? data.capitalFlow.find((theme) => theme.theme.toLowerCase() === lower) as ThemeScore | undefined
      ?? data.topThemes[0]
      ?? null;
  }, [data.capitalFlow, data.rotationMap, data.topThemes, selectedThemeName]);

  const forecast = useMemo(() => forecastForTheme(data.forecast, selectedThemeName), [data.forecast, selectedThemeName]);
  const leaders = useMemo(() => topLeaders(data.detail, activeTheme), [activeTheme, data.detail]);
  const roles = useMemo(() => supplyRoles(data.supplyChain, selectedThemeName), [data.supplyChain, selectedThemeName]);
  const narrative = data.narratives?.narratives?.find((item) => (item.theme ?? item.narrative_name).toLowerCase().includes(selectedThemeName.toLowerCase())) ?? data.narratives?.top_narratives?.[0] ?? null;
  const activeSector = data.sectors.find((sector) => sector.sector.toLowerCase() === selectedSector.toLowerCase()) ?? data.sectors[0] ?? null;
  const flowRows = data.capitalFlow.length > 0 ? data.capitalFlow : data.topThemes;

  const setTab = (tab: ThemeResearchTab) => setSelectedThemeView(tab);
  const selectTheme = (theme: string) => {
    setSelectedTheme(theme);
    setSelectedThemeView("command");
  };
  const selectSector = (sector: string) => {
    setSelectedSector(sector);
    setSelectedThemeView("rotation");
  };

  if (activeTab === "forecast") {
    return (
      <main id="theme-research" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
        <Header activeTab={activeTab} setTab={setTab} loading={data.loading} />
        <ForecastTab forecast={data.forecast} validation={data.validation} selectedTheme={selectedThemeName} />
      </main>
    );
  }

  return (
    <main id="theme-research" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
      <Header activeTab={activeTab} setTab={setTab} loading={data.loading} />
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
        <aside className="space-y-4">
          <TerminalPanel eyebrow="排名 Rankings" title="Theme Tape">
            <div className="space-y-2">
              {data.topThemes.slice(0, 8).map((theme) => (
                <ThemeRankRow key={theme.theme} theme={theme} active={theme.theme === selectedThemeName} onSelect={selectTheme} />
              ))}
            </div>
          </TerminalPanel>
          <TerminalPanel eyebrow="輪動 Rotation" title="Sector Strength">
            <div id="theme-rotation" tabIndex={-1} className="space-y-2 outline-none">
              {data.sectors.slice(0, 7).map((sector) => (
                <SectorRow key={sector.sector} sector={sector} active={activeSector?.sector === sector.sector} onSelect={selectSector} />
              ))}
            </div>
          </TerminalPanel>
        </aside>

        <section className="space-y-4">
          <TerminalPanel
            eyebrow="主題中樞 Theme Command"
            title={activeTab === "rotation" ? `${activeSector?.sector ?? selectedSector} Capital Rotation` : `${selectedThemeName} Research Overview`}
            description="One workspace for forecast alignment, capital flow, sector rotation, beneficiary stocks, supply-chain exposure, and risk."
            actions={<span className="rounded-[8px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] px-2 py-1 text-[11px] font-semibold uppercase text-[var(--theme-muted)]">{compactLifecycle(activeTheme?.lifecycle_state ?? activeSector?.lifecycle_state)}</span>}
          >
            <div className="grid gap-3 md:grid-cols-4">
              <Metric label="Leadership" value={themeScore(activeTheme)} />
              <Metric label="Flow" value={themeFlow(activeTheme)} />
              <Metric label="Momentum" value={themeMomentum(activeTheme)} />
              <Metric label="Forecast" value={forecast?.forecast_score} />
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
                <p className="terminal-micro-label">Capital Flow Map</p>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {[selectedThemeName, ...roles.map((role) => role.role), activeSector?.sector].filter(Boolean).slice(0, 7).map((node, index, list) => (
                    <span key={`${node}-${index}`} className="flex items-center gap-2">
                      <span className="rounded-[9px] border border-[var(--theme-border-strong)] bg-[var(--theme-bg-secondary)] px-3 py-2 text-xs font-semibold text-[var(--theme-text-secondary)]">{node}</span>
                      {index < list.length - 1 && <ChevronRight size={15} className="text-[var(--theme-muted)]" />}
                    </span>
                  ))}
                </div>
              </div>
              <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-4">
                <p className="terminal-micro-label">Forecast Alignment</p>
                <p className={`mt-3 font-mono text-3xl font-semibold ${classForScore(forecast?.forecast_score)}`}>{formatScore(forecast?.forecast_score)}</p>
                <p className="mt-2 text-sm leading-relaxed text-[var(--theme-text-secondary)]">{forecast?.explanation || narrative?.explanation || activeTheme?.explainability?.[0] || "Waiting for forecast alignment while live theme factors remain available."}</p>
              </div>
            </div>
          </TerminalPanel>

          <TerminalPanel
            eyebrow={activeTab === "risk" ? "風險 Risk" : activeTab === "supply-chain" ? "供應鏈 Supply Chain" : "資金流 Capital Flow"}
            title={activeTab === "risk" ? "Crowding And Drawdown Watch" : activeTab === "supply-chain" ? "Supply-Chain Exposure" : "Theme Flow Leaders"}
          >
            {activeTab === "supply-chain" ? (
              <div id="theme-supply-chain" tabIndex={-1} className="grid gap-3 outline-none md:grid-cols-2">
                {roles.map((role) => (
                  <div key={role.role} className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
                    <p className="text-sm font-semibold text-[var(--theme-text)]">{role.role}</p>
                    <p className="mt-2 text-xs text-[var(--theme-muted)]">{role.leaders.map((leader) => leader.ticker).join(" · ") || "No constituents yet"}</p>
                  </div>
                ))}
              </div>
            ) : activeTab === "risk" ? (
              <div className="grid gap-3 md:grid-cols-3">
                <Metric label="Crowding" value={activeTheme?.narrative_bubble_risk ?? forecast?.crowding_state} />
                <Metric label="Overheating" value={activeTheme?.overheating_score} />
                <Metric label="Saturation" value={activeTheme?.narrative_saturation} />
              </div>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {flowRows.slice(0, 8).map((theme) => (
                  <ThemeRankRow key={theme.theme} theme={theme as ThemeScore} active={theme.theme === selectedThemeName} onSelect={selectTheme} />
                ))}
              </div>
            )}
          </TerminalPanel>
        </section>

        <aside className="space-y-4">
          <TerminalPanel eyebrow="受益股 Beneficiaries" title="Stock Drilldown">
            <BeneficiaryList rows={leaders} onTickerSelect={onTickerSelect} />
          </TerminalPanel>
          <TerminalPanel eyebrow="新興 Emerging" title="Watch Themes">
            <div className="space-y-2">
              {data.emergingThemes.slice(0, 5).map((theme) => (
                <ThemeRankRow key={theme.theme} theme={theme} active={theme.theme === selectedThemeName} onSelect={selectTheme} />
              ))}
            </div>
          </TerminalPanel>
        </aside>
      </div>
    </main>
  );
}

function Header({ activeTab, setTab, loading }: { activeTab: ThemeResearchTab; setTab: (tab: ThemeResearchTab) => void; loading: boolean }) {
  return (
    <div className="mb-5 space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="terminal-micro-label text-[var(--theme-warning)]">AI Theme Command Center</p>
          <h1 className="terminal-page-title mt-1 text-[var(--theme-text)]">主題研究 Theme Research</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--theme-text-secondary)]">Forecast, capital rotation, supply-chain mapping, beneficiary stocks, and risk controls now live inside one institutional research workspace.</p>
        </div>
        <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel)] px-3 py-2 text-[11px] font-semibold uppercase text-[var(--theme-muted)]">
          {loading ? "Hydrating research tape" : "partial live research"}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {THEME_TABS.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setTab(tab.id)}
              className={`flex items-center gap-2 rounded-[10px] border px-3 py-2 text-sm font-semibold transition ${
                activeTab === tab.id ? "border-[var(--theme-border-strong)] bg-[var(--theme-panel-hover)] text-[var(--theme-text)]" : "border-[var(--theme-border)] bg-[var(--theme-panel)] text-[var(--theme-text-secondary)] hover:border-[var(--theme-border-strong)]"
              }`}
            >
              <Icon size={15} />
              <span>{tab.labelZh}</span>
              <span className="text-[11px] text-[var(--theme-muted)]">{tab.labelEn}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="rounded-[10px] border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
      <p className="terminal-micro-label">{label}</p>
      <p className={`mt-2 font-mono text-2xl font-semibold ${classForScore(value)}`}>{formatScore(value)}</p>
    </div>
  );
}
