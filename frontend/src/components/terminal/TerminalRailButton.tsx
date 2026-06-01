import type { ReactNode } from "react";

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
      className={`terminal-rail-button group relative flex h-10 w-10 items-center justify-center rounded-[10px] ${className}`}
    >
      {icon}
      <span className="pointer-events-none absolute left-[48px] z-[100] hidden whitespace-nowrap rounded-md border border-[var(--theme-border)] bg-[var(--theme-panel-hover)] px-2 py-1 text-[11px] font-semibold text-[var(--theme-text)] shadow-sm group-hover:block">
        {label}
        {secondaryLabel && <span className="ml-1 text-[var(--theme-muted)]">{secondaryLabel}</span>}
      </span>
    </button>
  );
}

