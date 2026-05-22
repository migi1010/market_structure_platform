"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Loader2, Radar } from "lucide-react";
import { sanitizeCompanyName } from "@/lib/sanitize";
import { fetchSectorRotation } from "@/services/stockApi";
import type { SectorRotation } from "@/types/stock";

interface SectorRotationPanelProps {
  onTickerSelect: (ticker: string) => void;
}

function money(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e12) return `$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${(abs / 1e6).toFixed(2)}M`;
  return `$${abs.toFixed(0)}`;
}

function gradient(score: number): string {
  if (score >= 90) return "from-emerald-300 to-teal-400";
  if (score >= 75) return "from-emerald-500 to-cyan-500";
  if (score >= 50) return "from-slate-500 to-slate-700";
  if (score >= 25) return "from-orange-500 to-rose-500";
  return "from-rose-600 to-red-700";
}

function scoreLabel(score: number): string {
  if (score >= 90) return "Exceptional";
  if (score >= 75) return "Strong";
  if (score >= 50) return "Neutral";
  if (score >= 25) return "Weak";
  return "Distressed";
}

function SectorSkeleton() {
  return (
    <div className="grid auto-rows-[138px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 9 }).map((_, index) => (
        <div key={index} className="animate-pulse rounded-2xl border border-[#2B313C] bg-[#1C2128]" />
      ))}
    </div>
  );
}

export default function SectorRotationPanel({ onTickerSelect }: SectorRotationPanelProps) {
  const [sectors, setSectors] = useState<SectorRotation[]>([]);
  const [activeSector, setActiveSector] = useState<string>("Technology");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const result = await fetchSectorRotation();
        if (!cancelled) {
          setSectors(result);
          setActiveSector(result?.[0]?.sector ?? "Technology");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const active = sectors.find((sector) => sector.sector === activeSector) ?? sectors?.[0];

  return (
    <section className="bg-[#0A0C10] p-5 text-[#E6EDF3]">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Capital Rotation System</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-wide text-[#E6EDF3]">Sector Rotation Heatmap</h1>
          <p className="mt-2 text-sm text-[#9BA7B4]">Momentum, relative strength, volume participation, cap-weighted flow, volatility and bubble risk.</p>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm font-medium text-[#9BA7B4]"><Loader2 className="animate-spin" size={16} /> Loading live sector tape</div>}
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_500px]">
        {loading && sectors.length === 0 ? (
          <SectorSkeleton />
        ) : (
          <div className="grid auto-rows-[148px] grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sectors.map((sector) => (
              <motion.button
                key={sector.sector}
                onClick={() => setActiveSector(sector.sector)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18 }}
                className={`relative overflow-hidden rounded-2xl border p-5 text-left shadow-[0_4px_24px_rgba(0,0,0,0.25)] transition ${
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
                      <p className="font-mono text-4xl font-semibold text-[#E6EDF3]">{sector.score.toFixed(1)}</p>
                      <span className="rounded-lg border border-white/20 bg-black/15 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#E6EDF3]/85">{scoreLabel(sector.score)}</span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] font-semibold uppercase tracking-wide text-[#E6EDF3]/80">
                      <span>RS {sector.relative_strength.toFixed(1)}</span>
                      <span>Flow {sector.flow.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
              </motion.button>
            ))}
          </div>
        )}

        <aside className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Sector Drilldown</p>
              <h2 className="text-2xl font-semibold tracking-wide text-[#E6EDF3]">{active?.sector ?? "Technology"}</h2>
            </div>
            <ChevronDown className="text-[#9BA7B4]" size={20} />
          </div>
          <div className="space-y-3">
            {(active?.companies ?? []).map((company) => (
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
                  <span className={company.change_percent >= 0 ? "font-mono text-sm font-semibold text-emerald-300" : "font-mono text-sm font-semibold text-rose-300"}>
                    {company.change_percent >= 0 ? "+" : ""}{company.change_percent.toFixed(2)}%
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-4 gap-2 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">
                  <span>Cap <b className="block text-[#C9D1D9]">{money(company.market_cap)}</b></span>
                  <span>Alpha <b className="block text-amber-200">{company.alpha_score.toFixed(1)}</b></span>
                  <span>Bubble <b className={company.bubble_score >= 70 ? "block text-rose-300" : "block text-[#C9D1D9]"}>{company.bubble_score.toFixed(1)}</b></span>
                  <span>RS <b className="block text-emerald-300">{company.relative_strength.toFixed(1)}</b></span>
                </div>
              </button>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}
