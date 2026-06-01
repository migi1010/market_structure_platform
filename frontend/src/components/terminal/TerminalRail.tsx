import type { ReactNode } from "react";

interface TerminalRailProps {
  brand?: ReactNode;
  top?: ReactNode;
  middle?: ReactNode;
  bottom?: ReactNode;
  className?: string;
}

export default function TerminalRail({ brand, top, middle, bottom, className = "" }: TerminalRailProps) {
  return (
    <aside className={`terminal-rail hidden h-full shrink-0 flex-col items-center justify-between py-3 md:flex ${className}`}>
      <div className="flex flex-col items-center gap-5">
        {brand}
        {top && <nav className="flex flex-col items-center gap-3">{top}</nav>}
      </div>
      {middle && <nav className="flex flex-col items-center gap-3">{middle}</nav>}
      {bottom && <nav className="flex flex-col items-center gap-3">{bottom}</nav>}
    </aside>
  );
}

