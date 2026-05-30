"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Activity, BrainCircuit, CheckCircle2, Loader2, ShieldAlert, TrendingDown, TrendingUp } from "lucide-react";
import { fetchThemeForecast, fetchThemeForecastValidation } from "@/services/stockApi";
import type { ForecastHorizon, ThemeForecastRecord, ThemeForecastResponse, ThemeForecastValidationResponse } from "@/types/stock";

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
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[#8B949E]">{title}</p>
      <div className="flex flex-wrap gap-2">
        {(items.length ? items : ["awaiting confirmation"]).map((item) => (
          <span key={item} className={tone === "positive" ? "rounded border border-emerald-300/20 bg-emerald-300/10 px-2 py-1 text-[11px] text-emerald-200" : "rounded border border-rose-300/20 bg-rose-300/10 px-2 py-1 text-[11px] text-rose-200"}>
            {item.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    </div>
  );
}

function ForecastCard({ item }: { item: ThemeForecastRecord }) {
  const score = item.forecast_score ?? null;
  const scoreTone = finite(score) && score >= 65 ? "text-emerald-300" : finite(score) && score <= 45 ? "text-rose-300" : "text-amber-200";
  return (
    <article className="rounded-lg border border-[#2B313C] bg-[#111318] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-[#E6EDF3]">{item.theme}</p>
          <p className="mt-1 text-[11px] uppercase tracking-wide text-[#8B949E]">{item.forecast_label} · {item.lifecycle_state}</p>
        </div>
        <div className={`font-mono text-2xl font-semibold ${scoreTone}`}>{fmtScore(score)}</div>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="rounded border border-[#2B313C] bg-[#0D1117] p-2">
          <p className="text-[9px] uppercase text-[#8B949E]">Excess</p>
          <p className="mt-1 font-mono text-sm text-[#E6EDF3]">{fmtPct(item.expected_excess_return)}</p>
        </div>
        <div className="rounded border border-[#2B313C] bg-[#0D1117] p-2">
          <p className="text-[9px] uppercase text-[#8B949E]">Prob.</p>
          <p className="mt-1 font-mono text-sm text-[#E6EDF3]">{fmtPct(item.outperformance_probability)}</p>
        </div>
        <div className="rounded border border-[#2B313C] bg-[#0D1117] p-2">
          <p className="text-[9px] uppercase text-[#8B949E]">Conf.</p>
          <p className="mt-1 font-mono text-sm text-[#E6EDF3]">{fmtScore(item.confidence)}</p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
        <span className="rounded border border-cyan-300/20 bg-cyan-300/10 px-2 py-1 text-cyan-200">Risk {item.risk_state}</span>
        <span className="rounded border border-amber-200/20 bg-amber-200/10 px-2 py-1 text-amber-100">Crowding {item.crowding_state}</span>
      </div>
      <p className="mt-4 text-sm leading-6 text-[#C9D1D9]">{item.explanation}</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <DriverList title="Positive Drivers" items={item.top_positive_drivers ?? []} tone="positive" />
        <DriverList title="Negative Drivers" items={item.top_negative_drivers ?? []} tone="negative" />
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="rounded-lg border border-[#2B313C] bg-[#0D1117] p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[#8B949E]">{label}</p>
      <p className="mt-2 font-mono text-lg font-semibold text-[#E6EDF3]">{finite(value) ? value.toFixed(2) : "--"}</p>
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
    <main id="theme-forecast" tabIndex={-1} className="miji-page p-5 text-[#E6EDF3] outline-none">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-cyan-200">Local Research Engine</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide">Theme Forecast AI</h1>
          <p className="mt-2 max-w-3xl text-sm text-[#9BA7B4]">Explainable theme leadership forecasts with regime context, driver decomposition, and walk-forward validation discipline.</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-[#2B313C] bg-[#111318] p-1">
          {HORIZONS.map((item) => (
            <button key={item} onClick={() => setHorizon(item)} className={item === horizon ? "rounded bg-cyan-300 px-3 py-2 text-xs font-semibold text-[#061018]" : "rounded px-3 py-2 text-xs font-semibold text-[#9BA7B4] hover:text-[#E6EDF3]"}>
              {item.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <section className="mb-5 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-[#2B313C] bg-[#111318] p-4">
          <div className="flex items-center gap-2 text-cyan-200"><BrainCircuit size={16} /><span className="text-[10px] font-semibold uppercase tracking-wide">Forecast State</span></div>
          <p className="mt-3 text-lg font-semibold">{forecast?.status ?? "loading"}</p>
          <p className="mt-1 text-xs text-[#8B949E]">{forecast?.lifecycle_state ?? "warming"}</p>
        </div>
        <div className="rounded-lg border border-[#2B313C] bg-[#111318] p-4">
          <div className="flex items-center gap-2 text-emerald-200"><Activity size={16} /><span className="text-[10px] font-semibold uppercase tracking-wide">Regime</span></div>
          <p className="mt-3 text-lg font-semibold">{regimeName}</p>
          <p className="mt-1 text-xs text-[#8B949E]">Overlay context</p>
        </div>
        <Metric label="Hit Rate" value={validation?.hit_rate ?? null} />
        <Metric label="Precision@5" value={validation?.precision_at_5 ?? null} />
      </section>

      {loading && <div className="mb-5 flex items-center gap-2 text-sm text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Recomputing forecast horizon</div>}

      {forecast?.available === false ? (
        <section className="rounded-lg border border-[#2B313C] bg-[#111318] p-6">
          <div className="flex items-center gap-3 text-amber-200"><ShieldAlert size={18} /><span className="font-semibold">Theme Forecast AI disabled</span></div>
          <p className="mt-3 text-sm text-[#C9D1D9]">{forecast.message}</p>
        </section>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <section>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[#E6EDF3]"><TrendingUp size={16} /> Top Future Themes</div>
            <div className="grid gap-4">
              {top.map((item) => <ForecastCard key={`${item.theme}-${item.forecast_horizon}`} item={item} />)}
            </div>
          </section>
          <aside className="space-y-4">
            <section className="rounded-lg border border-[#2B313C] bg-[#111318] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><CheckCircle2 size={16} /> Validation</div>
              <div className="grid grid-cols-2 gap-3">
                <Metric label="Info Ratio" value={validation?.information_ratio ?? null} />
                <Metric label="Max DD" value={validation?.max_drawdown ?? null} />
                <Metric label="Calibration" value={validation?.calibration_quality ?? null} />
                <Metric label="Turnover" value={validation?.turnover ?? null} />
              </div>
              {validation?.reason && <p className="mt-3 text-xs leading-5 text-[#8B949E]">{validation.reason}</p>}
            </section>
            <section className="rounded-lg border border-[#2B313C] bg-[#111318] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><TrendingDown size={16} /> Risk Buckets</div>
              <p className="text-xs uppercase text-[#8B949E]">Emerging</p>
              <p className="mb-3 text-sm text-[#E6EDF3]">{forecast?.emerging_themes?.map((item) => item.theme).join(", ") || "--"}</p>
              <p className="text-xs uppercase text-[#8B949E]">Crowded</p>
              <p className="mb-3 text-sm text-[#E6EDF3]">{forecast?.crowded_themes?.map((item) => item.theme).join(", ") || "--"}</p>
              <p className="text-xs uppercase text-[#8B949E]">Weakening</p>
              <p className="text-sm text-[#E6EDF3]">{forecast?.weakening_themes?.map((item) => item.theme).join(", ") || "--"}</p>
            </section>
          </aside>
        </div>
      )}
    </main>
  );
}
