import type { KeyboardEvent, ReactNode } from "react";

interface MarketTableProps {
  columns: string;
  header?: ReactNode;
  children: ReactNode;
  className?: string;
  density?: "compact" | "normal";
}

interface MarketRowProps {
  columns: string;
  active?: boolean;
  selected?: boolean;
  onClick?: () => void;
  onDoubleClick?: () => void;
  onPreview?: () => void;
  onPreviewEnd?: () => void;
  children: ReactNode;
  className?: string;
}

interface MarketCellProps {
  children: ReactNode;
  className?: string;
}

interface ChangeCellProps extends MarketCellProps {
  value?: number | null;
}

interface HoverSurfaceProps {
  active?: boolean;
  selected?: boolean;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
}

function directionFromValue(value: number | null | undefined): "positive" | "negative" | "neutral" {
  if (typeof value !== "number" || !Number.isFinite(value) || value === 0) return "neutral";
  return value > 0 ? "positive" : "negative";
}

export function MarketTable({ columns, header, children, className = "", density = "compact" }: MarketTableProps) {
  return (
    <div className={`market-table ${className}`} data-density={density}>
      {header && (
        <div className="market-table-header" style={{ gridTemplateColumns: columns }}>
          {header}
        </div>
      )}
      {children}
    </div>
  );
}

export function MarketRow({ columns, active = false, selected = false, onClick, onDoubleClick, onPreview, onPreviewEnd, children, className = "" }: MarketRowProps) {
  const Component = onClick || onDoubleClick ? "button" : "div";
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" || !onDoubleClick) return;
    event.preventDefault();
    onDoubleClick();
  };
  return (
    <Component
      type={onClick || onDoubleClick ? "button" : undefined}
      data-active={active}
      data-selected={selected}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={onPreview}
      onMouseLeave={onPreviewEnd}
      onFocus={onPreview}
      onBlur={onPreviewEnd}
      className={`market-row w-full text-left ${className}`}
      style={{ gridTemplateColumns: columns }}
    >
      {children}
    </Component>
  );
}

export function MarketCell({ children, className = "" }: MarketCellProps) {
  return <div className={`market-cell ${className}`}>{children}</div>;
}

export function NumericCell({ children, className = "" }: MarketCellProps) {
  return <MarketCell className={`numeric-cell ${className}`}>{children}</MarketCell>;
}

export function TickerCell({ children, className = "" }: MarketCellProps) {
  return <MarketCell className={`ticker-cell ${className}`}>{children}</MarketCell>;
}

export function ChangeCell({ children, value, className = "" }: ChangeCellProps) {
  return (
    <div className={`market-cell numeric-cell change-cell ${className}`} data-direction={directionFromValue(value)}>
      {children}
    </div>
  );
}

export function HoverSurface({ active = false, selected = false, onClick, children, className = "" }: HoverSurfaceProps) {
  const Component = onClick ? "button" : "div";
  return (
    <Component
      type={onClick ? "button" : undefined}
      data-active={active}
      data-selected={selected}
      onClick={onClick}
      className={`hover-surface ${onClick ? "w-full text-left" : ""} ${className}`}
    >
      {children}
    </Component>
  );
}
