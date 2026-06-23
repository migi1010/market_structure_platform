import type { ReactNode } from "react";
import { Cpu, Layers3, Network, RadioTower } from "lucide-react";

type ScanState = "accumulation" | "neutral" | "overheating" | "distribution" | "warming" | "live" | "degraded";
type Tone = "positive" | "neutral" | "warning" | "negative" | "info";

interface StatusDotProps {
  state?: ScanState | string | null;
  label?: ReactNode;
  className?: string;
}

interface ScoreProps {
  value?: number | null;
  label?: ReactNode;
  className?: string;
}

interface TickerLogoProps {
  ticker?: string | null;
  name?: string | null;
  className?: string;
}

interface NamedIconProps {
  sector?: string | null;
  theme?: string | null;
  label?: string | null;
  className?: string;
}

interface SparklineMiniProps {
  values?: Array<number | null | undefined>;
  className?: string;
}

interface BilingualLabelProps {
  zh: ReactNode;
  en: ReactNode;
  className?: string;
  inline?: boolean;
}

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function clampScore(value: number | null | undefined): number | null {
  const score = finite(value);
  if (score === null) return null;
  return Math.min(100, Math.max(0, score));
}

function toneFromScore(value: number | null | undefined, inverse = false): Tone {
  const score = clampScore(value);
  if (score === null) return "neutral";
  const adjusted = inverse ? 100 - score : score;
  if (adjusted >= 70) return "positive";
  if (adjusted >= 45) return "warning";
  return "negative";
}

function stateTone(state?: string | null): Tone {
  const normalized = (state ?? "").toLowerCase().replace(/[_\s-]+/g, " ");
  if (normalized.includes("accum") || normalized.includes("live") || normalized.includes("leader")) return "positive";
  if (normalized.includes("overheat") || normalized.includes("crowd") || normalized.includes("risk")) return "negative";
  if (normalized.includes("distrib") || normalized.includes("weak") || normalized.includes("degrad")) return "negative";
  if (normalized.includes("warm") || normalized.includes("partial") || normalized.includes("watch")) return "warning";
  return "neutral";
}

function initials(value?: string | null): string {
  const compact = (value ?? "").trim().toUpperCase();
  if (!compact) return "--";
  const parts = compact.split(/[\s:/.-]+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2);
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.slice(0, 2);
}

function iconKey(value?: string | null): "chip" | "flow" | "network" | "signal" {
  const lower = (value ?? "").toLowerCase();
  if (lower.includes("semi") || lower.includes("ai") || lower.includes("tech")) return "chip";
  if (lower.includes("supply") || lower.includes("chain") || lower.includes("grid")) return "network";
  if (lower.includes("flow") || lower.includes("capital") || lower.includes("energy") || lower.includes("financial")) return "flow";
  return "signal";
}

function MiniIcon({ value, size = 14 }: { value?: string | null; size?: number }) {
  const key = iconKey(value);
  if (key === "chip") return <Cpu size={size} />;
  if (key === "network") return <Network size={size} />;
  if (key === "flow") return <Layers3 size={size} />;
  return <RadioTower size={size} />;
}

export function StatusDot({ state = "neutral", label, className = "" }: StatusDotProps) {
  return (
    <span className={`scan-status ${className}`} data-tone={stateTone(state)}>
      <span className="scan-status-dot" aria-hidden="true" />
      {label && <span className="scan-status-label">{label}</span>}
    </span>
  );
}

export function HeatStrip({ value, label, className = "" }: ScoreProps) {
  const score = clampScore(value);
  return (
    <span className={`scan-heat-strip ${className}`} data-tone={toneFromScore(score)} aria-label={typeof label === "string" ? label : undefined}>
      <span style={{ width: `${score ?? 0}%` }} />
    </span>
  );
}

export function ConfidenceMeter({ value, label, className = "" }: ScoreProps) {
  const score = clampScore(value);
  return (
    <span className={`scan-confidence ${className}`} data-tone={toneFromScore(score)}>
      {label && <span className="scan-confidence-label">{label}</span>}
      <span className="scan-confidence-track"><span style={{ width: `${score ?? 0}%` }} /></span>
      <span className="scan-confidence-value">{score === null ? "--" : score.toFixed(0)}</span>
    </span>
  );
}

export function TickerLogo({ ticker, name, className = "" }: TickerLogoProps) {
  const symbol = (ticker ?? name ?? "").trim().toUpperCase();
  return <span className={`scan-logo scan-logo-ticker ${className}`} aria-label={symbol || "Ticker"}>{initials(symbol)}</span>;
}

export function SectorIcon({ sector, label, className = "" }: NamedIconProps) {
  const text = sector ?? label ?? "Sector";
  return (
    <span className={`scan-logo scan-logo-sector ${className}`} aria-label={text}>
      <MiniIcon value={text} />
    </span>
  );
}

export function ThemeIcon({ theme, label, className = "" }: NamedIconProps) {
  const text = theme ?? label ?? "Theme";
  return (
    <span className={`scan-logo scan-logo-theme ${className}`} aria-label={text}>
      <MiniIcon value={text} />
    </span>
  );
}

export function FlowIndicator({ value, label, className = "" }: ScoreProps) {
  const score = clampScore(value);
  return (
    <span className={`scan-flow ${className}`} data-tone={toneFromScore(score)}>
      <span className="scan-flow-mark" aria-hidden="true" />
      {label && <span>{label}</span>}
      <span className="font-mono">{score === null ? "--" : score.toFixed(0)}</span>
    </span>
  );
}

export function SparklineMini({ values = [], className = "" }: SparklineMiniProps) {
  const points = values.map(finite).filter((value): value is number => value !== null).slice(-8);
  const rangeMin = points.length ? Math.min(...points) : 0;
  const rangeMax = points.length ? Math.max(...points) : 1;
  const range = rangeMax - rangeMin || 1;
  const bars = points.length ? points : [0, 0, 0, 0];
  const rising = bars[bars.length - 1] >= bars[0];
  return (
    <span className={`scan-spark ${className}`} data-tone={rising ? "positive" : "negative"} aria-hidden="true">
      {bars.map((value, index) => (
        <span
          key={`${value}-${index}`}
          style={{ height: `${26 + ((value - rangeMin) / range) * 70}%` }}
        />
      ))}
    </span>
  );
}

export function BilingualLabel({ zh, en, className = "", inline = false }: BilingualLabelProps) {
  return (
    <span className={`scan-label ${inline ? "scan-label-inline" : ""} ${className}`}>
      <span className="scan-label-zh">{zh}</span>
      <span className="scan-label-en">{en}</span>
    </span>
  );
}
