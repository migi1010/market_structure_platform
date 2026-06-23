"use client";

import { Info } from "lucide-react";

interface InstitutionalTooltipProps {
  label: string;
  description: string;
}

export default function InstitutionalTooltip({ label, description }: InstitutionalTooltipProps) {
  return (
    <span className="group relative inline-flex items-center">
      <button
        type="button"
        aria-label={label}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[var(--theme-divider)] bg-transparent text-[var(--theme-muted)] transition hover:border-[var(--theme-hover-edge)] hover:text-[var(--theme-warning)]"
      >
        <Info size={12} />
      </button>
      <span className="pointer-events-none absolute left-1/2 top-7 z-[80] hidden w-72 -translate-x-1/2 rounded-[6px] border border-[var(--theme-divider)] bg-[var(--theme-bg)] p-3 text-xs leading-relaxed text-[var(--theme-text-secondary)] group-hover:block group-focus-within:block">
        {description}
      </span>
    </span>
  );
}
