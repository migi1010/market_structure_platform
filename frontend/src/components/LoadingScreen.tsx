"use client";

import { Activity, Cpu, Radar } from "lucide-react";

export default function LoadingScreen() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#0A0C10] px-6 text-[#E6EDF3]">
      <div className="w-full max-w-xl rounded-2xl border border-[#2B313C] bg-[#161B22] p-8 shadow-sm">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-amber-200">Institutional Terminal</p>
            <h1 className="mt-2 text-2xl font-black text-[#E6EDF3]">Quant Engine Booting</h1>
          </div>
          <div className="relative flex h-16 w-16 items-center justify-center">
            <div className="absolute inset-0 rounded-full border border-amber-400/30" />
            <div className="absolute inset-2 rounded-full bg-amber-400/10" />
            <Radar className="relative animate-spin text-amber-200" size={30} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-amber-200">
              <Activity size={16} />
              Loading Market Intelligence...
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div className="h-full w-2/3 animate-pulse rounded-full bg-emerald-300" />
            </div>
          </div>
          <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-200">
              <Cpu size={16} className="text-emerald-300" />
              Initializing Quant Systems...
            </div>
            <div className="grid grid-cols-12 gap-1">
              {Array.from({ length: 24 }).map((_, index) => (
                <div
                  key={index}
                  className="h-7 rounded border border-amber-400/20 bg-amber-400/10 shadow-none"
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
