"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("Quant Engine Crash Detected", error);
  }, [error]);

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[var(--theme-bg)] px-6 text-[var(--theme-text)]">
      <div className="terminal-panel max-w-lg p-8 text-center">
        <AlertTriangle className="mx-auto mb-5 text-rose-400" size={46} />
        <p className="text-[11px] font-semibold uppercase tracking-wide text-rose-300">System Failure</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--theme-text)]">Quant Engine Crash Detected</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">Retry System to reinitialize market intelligence, HMM inference, and terminal state.</p>
        <button
          onClick={reset}
          className="mt-6 inline-flex items-center gap-2 rounded-[6px] border border-[var(--theme-divider)] px-5 py-3 text-sm font-semibold text-[var(--theme-warning)] transition hover:border-[var(--theme-hover-edge)] hover:bg-[rgba(255,255,255,0.035)]"
        >
          <RotateCcw size={16} />
          Try Again
        </button>
      </div>
    </div>
  );
}
