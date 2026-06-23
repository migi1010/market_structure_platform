import type { ReactNode } from "react";
import { SignalPulse } from "./InteractionPrimitives";

interface TerminalRailButtonProps {
  label: string;
  secondaryLabel?: string;
  icon: ReactNode;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}

export default function TerminalRailButton({
  label,
  secondaryLabel,
  icon,
  active = false,
  onClick,
  className = "",
}: TerminalRailButtonProps) {
  return (
    <button
      type="button"
      aria-label={secondaryLabel ? `${label} ${secondaryLabel}` : label}
      title={secondaryLabel ? `${label} / ${secondaryLabel}` : label}
      data-active={active}
      onClick={onClick}
      className={`terminal-rail-button group relative flex h-9 w-full items-center gap-3 rounded-[6px] px-3 text-left ${className}`}
    >
      <span className="shrink-0">{icon}</span>
      <span className="terminal-rail-label min-w-0 overflow-hidden whitespace-nowrap">
        <span className="flex min-w-0 items-center gap-2">
          <span className="block truncate text-[13px] font-semibold leading-tight">{label}</span>
          {active && <SignalPulse tone="positive" />}
        </span>
        {secondaryLabel && <span className="block truncate text-[10px] font-medium leading-tight text-[var(--theme-muted)]">{secondaryLabel}</span>}
      </span>
    </button>
  );
}
