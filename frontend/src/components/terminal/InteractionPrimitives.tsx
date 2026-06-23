import type { KeyboardEvent, ReactNode } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { ConfidenceMeter, HeatStrip, StatusDot } from "./Scanability";

type Tone = "positive" | "neutral" | "warning" | "negative" | "info";

interface ContextDockProps {
  open?: boolean;
  collapsed?: boolean;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  onClose?: () => void;
  onToggle?: () => void;
  children: ReactNode;
  className?: string;
}

interface InteractiveTileProps {
  label: ReactNode;
  value?: number | null;
  meta?: ReactNode;
  selected?: boolean;
  tone?: Tone;
  onClick?: () => void;
  onDoubleClick?: () => void;
  onPreview?: () => void;
  onPreviewEnd?: () => void;
  children?: ReactNode;
  className?: string;
}

interface TreemapSurfaceProps {
  children: ReactNode;
  columns?: string;
  className?: string;
}

interface FlowNodeProps {
  label: ReactNode;
  value?: number | null;
  active?: boolean;
  onClick?: () => void;
  onDoubleClick?: () => void;
  onPreview?: () => void;
  onPreviewEnd?: () => void;
  children?: ReactNode;
  className?: string;
}

interface RiskOverlayProps {
  label: ReactNode;
  value?: number | null;
  state?: string | null;
  onClick?: () => void;
  onDoubleClick?: () => void;
  onPreview?: () => void;
  onPreviewEnd?: () => void;
  children?: ReactNode;
  className?: string;
}

interface DrilldownTriggerProps {
  label: ReactNode;
  meta?: ReactNode;
  onClick?: () => void;
  className?: string;
}

interface HoverPreviewProps {
  label: ReactNode;
  preview?: ReactNode;
  children: ReactNode;
  className?: string;
}

interface SignalPulseProps {
  tone?: Tone;
  active?: boolean;
  className?: string;
}

export function ContextDock({ open = false, collapsed = true, title, subtitle, actions, onClose, onToggle, children, className = "" }: ContextDockProps) {
  return (
    <aside className={`context-dock ${open ? "context-dock-open" : ""} ${className}`} data-collapsed={collapsed} aria-hidden={!open}>
      <div className="context-dock-header">
        <div className="context-dock-heading min-w-0">
          <h2 className="truncate text-sm font-semibold text-[var(--theme-text)]">{title}</h2>
          {subtitle && <p className="mt-1 truncate text-xs text-[var(--theme-muted)]">{subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {onToggle && (
            <button type="button" className="context-icon-button" aria-label={collapsed ? "Expand context dock" : "Collapse context dock"} onClick={onToggle}>
              {collapsed ? <ChevronLeft size={14} /> : <ChevronRight size={14} />}
            </button>
          )}
          {actions}
          {onClose && (
            <button type="button" className="context-icon-button" aria-label="Close context dock" onClick={onClose}>
              <X size={14} />
            </button>
          )}
        </div>
      </div>
      {!collapsed && <div className="context-dock-body">{children}</div>}
    </aside>
  );
}

export function InteractiveTile({ label, value, meta, selected = false, tone = "neutral", onClick, onDoubleClick, onPreview, onPreviewEnd, children, className = "" }: InteractiveTileProps) {
  const Component = onClick || onDoubleClick ? "button" : "div";
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" || !onDoubleClick) return;
    event.preventDefault();
    onDoubleClick();
  };
  return (
    <Component
      type={onClick || onDoubleClick ? "button" : undefined}
      data-selected={selected}
      data-tone={tone}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onKeyDown={handleKeyDown}
      onMouseEnter={onPreview}
      onMouseLeave={onPreviewEnd}
      onFocus={onPreview}
      onBlur={onPreviewEnd}
      className={`interactive-tile ${onClick || onDoubleClick ? "w-full text-left" : ""} ${className}`}
    >
      <span className="flex min-w-0 items-start justify-between gap-3">
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold text-[var(--theme-text)]">{label}</span>
          {meta && <span className="mt-1 block truncate text-[11px] text-[var(--theme-muted)]">{meta}</span>}
        </span>
        <span className="shrink-0 font-mono text-lg font-semibold text-[var(--theme-text-secondary)]">
          {typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "--"}
        </span>
      </span>
      <span className="mt-4 flex items-center justify-between gap-3">
        <HeatStrip value={value} className="w-full" />
        <SignalPulse tone={tone} active={selected} />
      </span>
      {children && <span className="mt-3 block text-xs text-[var(--theme-muted)]">{children}</span>}
    </Component>
  );
}

export function TreemapSurface({ children, columns = "repeat(4, minmax(0, 1fr))", className = "" }: TreemapSurfaceProps) {
  return (
    <div className={`treemap-surface ${className}`} style={{ gridTemplateColumns: columns }}>
      {children}
    </div>
  );
}

export function FlowNode({ label, value, active = false, onClick, onDoubleClick, onPreview, onPreviewEnd, children, className = "" }: FlowNodeProps) {
  const Component = onClick || onDoubleClick ? "button" : "div";
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" || !onDoubleClick) return;
    event.preventDefault();
    onDoubleClick();
  };
  return (
    <Component type={onClick || onDoubleClick ? "button" : undefined} data-active={active} onClick={onClick} onDoubleClick={onDoubleClick} onKeyDown={handleKeyDown} onMouseEnter={onPreview} onMouseLeave={onPreviewEnd} onFocus={onPreview} onBlur={onPreviewEnd} className={`flow-node ${onClick || onDoubleClick ? "w-full text-left" : ""} ${className}`}>
      <span className="flex items-center justify-between gap-3">
        <span className="truncate text-sm font-semibold text-[var(--theme-text)]">{label}</span>
        <ConfidenceMeter value={value} />
      </span>
      {children && <span className="mt-3 block text-xs text-[var(--theme-muted)]">{children}</span>}
    </Component>
  );
}

export function RiskOverlay({ label, value, state = "neutral", onClick, onDoubleClick, onPreview, onPreviewEnd, children, className = "" }: RiskOverlayProps) {
  const Component = onClick || onDoubleClick ? "button" : "div";
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" || !onDoubleClick) return;
    event.preventDefault();
    onDoubleClick();
  };
  return (
    <Component type={onClick || onDoubleClick ? "button" : undefined} onClick={onClick} onDoubleClick={onDoubleClick} onKeyDown={handleKeyDown} onMouseEnter={onPreview} onMouseLeave={onPreviewEnd} onFocus={onPreview} onBlur={onPreviewEnd} className={`risk-overlay ${onClick || onDoubleClick ? "w-full text-left" : ""} ${className}`}>
      <span className="flex items-center justify-between gap-3">
        <span className="truncate text-sm font-semibold text-[var(--theme-text)]">{label}</span>
        <StatusDot state={state} label={state} />
      </span>
      <span className="mt-3 flex items-center justify-between gap-3">
        <HeatStrip value={value} className="w-full" />
        <span className="font-mono text-lg font-semibold text-[var(--theme-text-secondary)]">
          {typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "--"}
        </span>
      </span>
      {children && <span className="mt-3 block text-xs text-[var(--theme-muted)]">{children}</span>}
    </Component>
  );
}

export function DrilldownTrigger({ label, meta, onClick, className = "" }: DrilldownTriggerProps) {
  return (
    <button type="button" onClick={onClick} className={`drilldown-trigger ${className}`}>
      <span className="min-w-0 truncate">{label}</span>
      {meta && <span className="ml-auto shrink-0 text-[10px] text-[var(--theme-muted)]">{meta}</span>}
      <ChevronRight size={14} className="shrink-0 text-[var(--theme-muted)]" />
    </button>
  );
}

export function HoverPreview({ label, preview, children, className = "" }: HoverPreviewProps) {
  return (
    <span className={`hover-preview ${className}`}>
      {children}
      <span className="hover-preview-panel" role="tooltip">
        <span className="block text-[11px] font-semibold text-[var(--theme-text)]">{label}</span>
        {preview && <span className="mt-1 block text-xs text-[var(--theme-muted)]">{preview}</span>}
      </span>
    </span>
  );
}

export function SignalPulse({ tone = "neutral", active = true, className = "" }: SignalPulseProps) {
  return <span className={`signal-pulse ${className}`} data-tone={tone} data-active={active} aria-hidden="true" />;
}
