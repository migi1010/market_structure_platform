"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Activity, BrainCircuit, CheckCircle2, Loader2, ShieldAlert, TrendingDown, TrendingUp } from "lucide-react";
import { fetchThemeForecast, fetchThemeForecastValidation } from "@/services/stockApi";
import type { ForecastHorizon, ThemeForecastRecord, ThemeForecastResponse, ThemeForecastValidationResponse } from "@/types/stock";
import { TerminalPanel } from "./terminal";

const HORIZONS: ForecastHorizon[] = ["1w", "1m", "3m"];

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function fmtScore(value: number | null | undefined): string {
  return finite(value) ? value.toFixed(1) : "--";
}

function fmtPct(value: number | null | undefined): string {
  return finite(value) ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%` : "--";
}

function DriverList({ title, items, tone }: { title: string; items: string[]; tone: "positive" | "negative" }) {
  return (
    <div>
      <p className="mb-2 text-[10px] font-bold uppercase tracking-wide text-[var(--theme-muted)]">{title}</p>
      <div className="flex flex-wrap gap-2">
        {(items.length ? items : ["awaiting confirmation"]).map((item) => (
          <span
            key={item}
            className={
              tone === "positive"
                ? "rounded-md border border-[var(--theme-bullish)] bg-[var(--theme-positive-tag-bg)] px-2.5 py-1.5 text-[11px] font-semibold text-[var(--theme-bullish)]"
                : "rounded-md border border-[var(--theme-bearish)] bg-[var(--theme-negative-tag-bg)] px-2.5 py-1.5 text-[11px] font-semibold text-[var(--theme-bearish)]"
            }
          >
            {item.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    </div>
  );
}

function ForecastCard({ item }: { item: ThemeForecastRecord }) {
  const score = item.forecast_score ?? null;
  const scoreTone = finite(score) && score >= 65 ? "text-[var(--theme-bullish)]" : finite(score) && score <= 45 ? "text-[var(--theme-bearish)]" : "text-[var(--theme-highlight)]";
  return (
    <article className="terminal-panel terminal-panel-hover p-4">
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0">
          <p className="truncate text-lg font-bold text-[var(--theme-text)]">{item.theme}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-[var(--theme-border-strong)] bg-[var(--theme-panel-inset)] px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-[var(--theme-text-secondary)]">{item.lifecycle_state}</span>
            <span className="rounded-md border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">{item.forecast_label}</span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className={`font-mono text-4xl font-bold leading-none ${scoreTone}`}>{fmtScore(score)}</div>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-[var(--theme-muted)]">Forecast Score</p>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <Metric label="Excess" value={item.expected_excess_return} percent />
        <Metric label="Prob." value={item.outperformance_probability} percent />
        <Metric label="Conf." value={item.confidence} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold">
        <span className="rounded-md border border-[var(--theme-border-strong)] bg-[var(--theme-panel-inset)] px-2.5 py-1.5 text-[var(--theme-text-secondary)]">Risk {item.risk_state}</span>
        <span className="rounded-md border border-[var(--theme-border-strong)] bg-[var(--theme-panel-inset)] px-2.5 py-1.5 text-[var(--theme-warning)]">Crowding {item.crowding_state}</span>
      </div>
      <p className="mt-3 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] px-3 py-2 text-sm font-medium leading-6 text-[var(--theme-text-secondary)]">{item.explanation}</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <DriverList title="Positive Drivers" items={item.top_positive_drivers ?? []} tone="positive" />
        <DriverList title="Negative Drivers" items={item.top_negative_drivers ?? []} tone="negative" />
      </div>
    </article>
  );
}

function Metric({ label, value, percent = false }: { label: string; value: number | null | undefined; percent?: boolean }) {
  return (
    <div className="rounded-lg border border-[var(--theme-border)] bg-[var(--theme-panel-inset)] p-3">
      <p className="text-[10px] font-bold uppercase tracking-wide text-[var(--theme-muted)]">{label}</p>
      <p className="mt-2 font-mono text-lg font-bold text-[var(--theme-highlight)]">{percent ? fmtPct(value) : fmtScore(value)}</p>
    </div>
  );
}

export default function ThemeForecastAIPage() {
  const [horizon, setHorizon] = useState<ForecastHorizon>("1m");
  const [forecast, setForecast] = useState<ThemeForecastResponse | null>(null);
  const [validation, setValidation] = useState<ThemeForecastValidationResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const [forecastPayload, validationPayload] = await Promise.all([
        fetchThemeForecast(horizon),
        fetchThemeForecastValidation(horizon),
      ]);
      if (!cancelled) {
        setForecast(forecastPayload);
        setValidation(validationPayload);
        setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [horizon]);

  const top = useMemo(() => forecast?.top_future_themes?.length ? forecast.top_future_themes : forecast?.forecasts?.slice(0, 5) ?? [], [forecast]);
  const regimeName = String(forecast?.regime_context?.name ?? "Regime pending");

  return (
    <main id="theme-forecast" tabIndex={-1} className="miji-page bg-[var(--theme-bg)] p-5 text-[var(--theme-text)] outline-none">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="terminal-micro-label">主題預測 Forecast</p>
          <h1 className="terminal-page-title mt-1">Theme Forecast AI</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--theme-text-secondary)]">Explainable theme leadership forecasts with regime context, driver decomposition, and walk-forward validation discipline.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[var(--theme-border-strong)] bg-[var(--theme-panel)] p-1">
          {HORIZONS.map((item) => (
            <button key={item} onClick={() => setHorizon(item)} className={item === horizon ? "rounded bg-[var(--theme-panel-hover)] px-3 py-2 text-xs font-bold text-[var(--theme-highlight)]" : "rounded px-3 py-2 text-xs font-semibold text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}>
              {item.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <section className="mb-5 grid gap-3 md:grid-cols-4">
        <TerminalPanel>
          <div className="flex items-center gap-2 text-[var(--theme-accent-soft)]"><BrainCircuit size={16} /><span className="text-[10px] font-semibold uppercase tracking-wide">Forecast State</span></div>
          <p className="mt-3 text-lg font-bold text-[var(--theme-highlight)]">{forecast?.status ?? "loading"}</p>
          <p className="mt-1 text-xs text-[var(--theme-muted)]">{forecast?.lifecycle_state ?? "warming"}</p>
        </TerminalPanel>
        <TerminalPanel>
          <div className="flex items-center gap-2 text-[var(--theme-bullish)]"><Activity size={16} /><span className="text-[10px] font-semibold uppercase tracking-wide">Regime</span></div>
          <p className="mt-3 text-lg font-bold text-[var(--theme-highlight)]">{regimeName}</p>
          <p className="mt-1 text-xs text-[var(--theme-muted)]">Overlay context</p>
        </TerminalPanel>
        <Metric label="Hit Rate" value={validation?.hit_rate ?? null} />
        <Metric label="Precision@5" value={validation?.precision_at_5 ?? null} />
      </section>

      {loading && <div className="mb-5 flex items-center gap-2 text-sm text-[var(--theme-muted)]"><Loader2 className="animate-spin" size={16} /> Recomputing forecast horizon</div>}

      {forecast?.available === false ? (
        <TerminalPanel>
          <div className="flex items-center gap-3 text-[var(--theme-warning)]"><ShieldAlert size={18} /><span className="font-semibold">Theme Forecast AI disabled</span></div>
          <p className="mt-3 text-sm text-[var(--theme-text-secondary)]">{forecast.message}</p>
        </TerminalPanel>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <section>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[var(--theme-text)]"><TrendingUp size={16} /> 未來領導主題 Top Future Themes</div>
            <div className="grid gap-4">
              {top.map((item) => <ForecastCard key={`${item.theme}-${item.forecast_horizon}`} item={item} />)}
            </div>
          </section>
          <aside className="space-y-4">
            <TerminalPanel>
              <div className="mb-3 flex items-center gap-2 text-sm font-bold text-[var(--theme-text)]"><CheckCircle2 size={16} /> 驗證 Validation</div>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Info Ratio" value={validation?.information_ratio ?? null} />
                <Metric label="Max DD" value={validation?.max_drawdown ?? null} />
                <Metric label="Calibration" value={validation?.calibration_quality ?? null} />
                <Metric label="Turnover" value={validation?.turnover ?? null} />
              </div>
              {validation?.reason && <p className="mt-3 text-xs leading-5 text-[var(--theme-text-secondary)]">{validation.reason}</p>}
            </TerminalPanel>
            <TerminalPanel>
              <div className="mb-3 flex items-center gap-2 text-sm font-bold text-[var(--theme-text)]"><TrendingDown size={16} /> 風險分組 Risk Buckets</div>
              <p className="text-xs uppercase text-[var(--theme-muted)]">新興 Emerging</p>
              <p className="mb-3 text-sm text-[var(--theme-text)]">{forecast?.emerging_themes?.map((item) => item.theme).join(", ") || "--"}</p>
              <p className="text-xs uppercase text-[var(--theme-muted)]">擁擠 Crowded</p>
              <p className="mb-3 text-sm text-[var(--theme-text)]">{forecast?.crowded_themes?.map((item) => item.theme).join(", ") || "--"}</p>
              <p className="text-xs uppercase text-[var(--theme-muted)]">弱化 Weakening</p>
              <p className="text-sm text-[var(--theme-text)]">{forecast?.weakening_themes?.map((item) => item.theme).join(", ") || "--"}</p>
            </TerminalPanel>
          </aside>
        </div>
      )}
    </main>
  );
}
