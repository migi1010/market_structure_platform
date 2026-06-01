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
  const label = isHigh ? "High Bubble Risk" : isSafe ? "Fundamental Safety Zone" : "Neutral Observation";
  const colorClass = isHigh
    ? "text-[var(--theme-bearish)] border-[var(--theme-bearish)] bg-[var(--theme-negative-tag-bg)]"
    : isSafe
      ? "text-[var(--theme-bullish)] border-[var(--theme-bullish)] bg-[var(--theme-positive-tag-bg)]"
      : "text-[var(--theme-warning)] border-[var(--theme-warning)] bg-[var(--theme-panel-inset)]";
  const stroke = isHigh ? "var(--theme-bearish)" : isSafe ? "var(--theme-bullish)" : "var(--theme-warning)";

  return (
    <div className="miji-card terminal-panel p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="terminal-micro-label">Weighted Bubble Index</p>
          <h3 className="terminal-panel-title mt-1 text-[var(--theme-text)]">Valuation Risk HUD</h3>
        </div>
        <ShieldAlert className={isHigh ? "text-[var(--theme-bearish)]" : "text-[var(--theme-warning)]"} size={24} />
      </div>

      <div className="flex flex-col items-center">
        <div className="relative h-56 w-56">
          <svg viewBox="0 0 220 220" className="relative h-full w-full -rotate-90">
            <circle cx="110" cy="110" r="86" fill="none" stroke="var(--theme-panel-inset)" strokeWidth="16" />
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
            <span className="font-mono text-5xl font-bold tracking-wide text-[var(--theme-highlight)]">{normalized.toFixed(0)}</span>
            <span className="mt-1 text-xs font-medium uppercase tracking-wide text-[var(--theme-muted)]">0-100</span>
          </div>
        </div>

        <div className={`mt-4 rounded-2xl border px-4 py-2 text-sm font-semibold tracking-wide ${colorClass}`}>
          {label}
        </div>
      </div>
    </div>
  );
}
