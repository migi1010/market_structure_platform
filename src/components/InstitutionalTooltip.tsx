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
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-[#2B313C] bg-[#111318] text-[#9BA7B4] transition hover:border-amber-400/30 hover:text-amber-200"
      >
        <Info size={12} />
      </button>
      <span className="pointer-events-none absolute left-1/2 top-7 z-[80] hidden w-72 -translate-x-1/2 rounded-xl border border-[#2B313C] bg-[#0A0C10]/95 p-3 text-xs leading-relaxed text-[#C9D1D9] shadow-[0_18px_48px_rgba(0,0,0,0.42)] backdrop-blur-md group-hover:block group-focus-within:block">
        {description}
      </span>
    </span>
  );
}
