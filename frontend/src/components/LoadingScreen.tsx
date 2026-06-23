"use client";

import { Activity, Cpu, Radar } from "lucide-react";

export default function LoadingScreen() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[var(--theme-bg)] px-6 text-[var(--theme-text)]">
      <div className="terminal-panel w-full max-w-xl p-8">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Institutional Terminal</p>
            <h1 className="mt-2 text-2xl font-semibold text-[var(--theme-text)]">Quant Engine Booting</h1>
          </div>
          <div className="relative flex h-16 w-16 items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-amber-400/30" />
            <div className="absolute inset-2 rounded-full bg-amber-400/10" />
            <Radar className="relative animate-spin text-amber-200" size={30} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="border-y border-[var(--theme-divider)] py-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-amber-200">
              <Activity size={16} />
              Loading Market Intelligence...
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[var(--theme-panel-inset)]">
              <div className="h-full w-2/3 animate-pulse rounded-full bg-emerald-300" />
            </div>
          </div>
          <div className="border-y border-[var(--theme-divider)] py-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-200">
              <Cpu size={16} className="text-emerald-300" />
              Initializing Quant Systems...
            </div>
            <div className="grid grid-cols-12 gap-1">
              {Array.from({ length: 24 }).map((_, index) => (
                <div
                  key={index}
                  className="h-7 rounded-[4px] border border-[var(--theme-divider)] bg-[rgba(255,255,255,0.025)]"
                  style={{ animation: `pulse 1.4s ease-in-out ${index * 0.04}s infinite` }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
