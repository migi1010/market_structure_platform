"use client";

import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";

interface BubbleGaugeProps {
  score: number;
}

function clampScore(score: number): number {
  if (Number.isNaN(score)) return 0;
  return Math.min(100, Math.max(0, score));
}

export default function BubbleGauge({ score }: BubbleGaugeProps) {
  const normalized = clampScore(score);
  const circumference = 2 * Math.PI * 86;
  const strokeDashoffset = circumference - (normalized / 100) * circumference;
  const isHigh = normalized >= 70;
  const isSafe = normalized <= 40;
  const label = isHigh ? "高度泡沫警戒" : isSafe ? "基本面安全" : "中性觀察";
  const colorClass = isHigh
    ? "text-rose-300 border-rose-300/40"
    : isSafe
      ? "text-emerald-300 border-emerald-300/40"
      : "text-amber-200 border-amber-400/30";
  const stroke = isHigh ? "#fda4af" : isSafe ? "#86efac" : "#fcd34d";

  return (
    <div className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-6 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-md">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-200">Weighted Bubble Index</p>
          <h3 className="mt-1 text-lg font-semibold tracking-wide text-[#E6EDF3]">Valuation Risk HUD</h3>
        </div>
        <ShieldAlert className={isHigh ? "text-rose-300" : "text-amber-200"} size={24} />
      </div>

      <div className="flex flex-col items-center">
        <div className="relative h-56 w-56">
          <svg viewBox="0 0 220 220" className="relative h-full w-full -rotate-90">
            <circle cx="110" cy="110" r="86" fill="none" stroke="#222833" strokeWidth="16" />
            <motion.circle
              cx="110"
              cy="110"
              r="86"
              fill="none"
              stroke={stroke}
              strokeLinecap="round"
              strokeWidth="16"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 0.9, ease: "easeOut" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-5xl font-semibold tracking-wide text-[#E6EDF3]">{normalized.toFixed(0)}</span>
            <span className="mt-1 text-xs font-medium uppercase tracking-wide text-[#9BA7B4]">0-100</span>
          </div>
        </div>

        <div className={`mt-4 rounded-2xl border px-4 py-2 text-sm font-semibold tracking-wide ${colorClass}`}>
          {label}
        </div>
      </div>
    </div>
  );
}
