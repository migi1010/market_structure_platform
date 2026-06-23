import type { SectorCompany, SectorRotation } from "@/types/stock";
import { safeArray } from "./payloadSafety";

export type TreemapDetailLevel = "large" | "medium" | "small" | "tiny";
export type RotationScoreBand = "strong-green" | "green" | "yellow" | "orange" | "red" | "unavailable";
export type MomentumVisualState = "improving" | "deteriorating" | "flat" | "unavailable";
export type InstitutionalRotationState = "strong-leader" | "leader" | "neutral" | "weakening" | "laggard" | "unavailable";
export type RotationFillFamily = "cyan-green" | "teal" | "graphite" | "amber" | "magenta-red" | "unavailable";
export type RotationMomentumAccent = "positive" | "negative" | "flat" | "unavailable";

export interface RotationVisual {
  state: InstitutionalRotationState;
  fillFamily: RotationFillFamily;
  intensity: number;
  momentumAccent: RotationMomentumAccent;
  fill: string;
  border: string;
  glow: string;
}

export interface RotationDiagnostic {
  labelZh: string;
  labelEn: string;
  value: string;
  score: number | null;
  state: string;
}

export interface RotationWorkspaceModel {
  leaders: SectorRotation[];
  selected: SectorRotation | null;
  selectedCompanies: SectorCompany[];
  diagnostics: RotationDiagnostic[];
}

export interface TreemapLabelPolicy {
  showName: boolean;
  showScore: boolean;
  showFlow: boolean;
  showRegime: boolean;
  showMomentum: boolean;
  showRelativeStrength: boolean;
}

export interface RotationLayoutProjection {
  treemapBasisPercent: number;
  secondaryPanel: "diagnostic-intelligence";
  rightRail: Array<"market-diagnostics" | "capital-flow-story" | "selected-sector-intelligence">;
  duplicatedPrimarySurfaces: string[];
}

function finite(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function capitalFlowWeight(value: number | null | undefined): number {
  const numeric = finite(value);
  return numeric === null || numeric === 0 ? 1 : Math.abs(numeric);
}

export function rotationScoreBand(value: number | null | undefined): RotationScoreBand {
  const score = finite(value);
  if (score === null) return "unavailable";
  if (score >= 90) return "strong-green";
  if (score >= 70) return "green";
  if (score >= 50) return "yellow";
  if (score >= 30) return "orange";
  return "red";
}

export function momentumVisualState(value: number | null | undefined): MomentumVisualState {
  const momentum = finite(value);
  if (momentum === null) return "unavailable";
  if (momentum > 0) return "improving";
  if (momentum < 0) return "deteriorating";
  return "flat";
}

export function projectRotationState(
  scoreValue: number | null | undefined,
  momentumValue: number | null | undefined,
  flowValue: number | null | undefined,
): InstitutionalRotationState {
  const score = finite(scoreValue);
  const momentum = finite(momentumValue);
  const flow = finite(flowValue);
  if (score === null) return "unavailable";
  if (score >= 80 && (momentum ?? 0) > 0 && (flow ?? 0) > 0) return "strong-leader";
  if (score >= 60 && (momentum ?? 0) > 0 && (flow ?? 0) >= 0) return "leader";
  if (score < 30 && (momentum ?? 0) < 0 && (flow ?? 0) < 0) return "laggard";
  if (score < 50 && (momentum ?? 0) < 0) return "weakening";
  return "neutral";
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

const ROTATION_VISUAL_BANDS: Record<InstitutionalRotationState, readonly [number, number]> = {
  "strong-leader": [80, 100],
  leader: [60, 80],
  neutral: [40, 60],
  weakening: [30, 50],
  laggard: [0, 30],
  unavailable: [0, 1],
};

export function normalizeRotationBandIntensity(
  state: InstitutionalRotationState,
  scoreValue: number | null | undefined,
): number {
  const score = finite(scoreValue);
  if (score === null || state === "unavailable") return 0;
  const [minimum, maximum] = ROTATION_VISUAL_BANDS[state];
  return clamp01((score - minimum) / Math.max(1, maximum - minimum));
}

export function projectRotationVisual(
  scoreValue: number | null | undefined,
  momentumValue: number | null | undefined,
  flowValue: number | null | undefined,
): RotationVisual {
  const state = projectRotationState(scoreValue, momentumValue, flowValue);
  const score = finite(scoreValue);
  const momentum = finite(momentumValue);
  const intensity = normalizeRotationBandIntensity(state, score);
  const momentumAccent: RotationMomentumAccent = momentum === null
    ? "unavailable"
    : momentum > 0
      ? "positive"
      : momentum < 0
        ? "negative"
        : "flat";
  const palette: Record<InstitutionalRotationState, {
    fillFamily: RotationFillFamily;
    low: string;
    high: string;
    border: string;
    glow: string;
  }> = {
    "strong-leader": { fillFamily: "cyan-green", low: "#063f36", high: "#00a978", border: "#5fffd0", glow: "rgba(0, 255, 190, .36)" },
    leader: { fillFamily: "teal", low: "#08353d", high: "#087f83", border: "#46dbe0", glow: "rgba(40, 211, 218, .25)" },
    neutral: { fillFamily: "graphite", low: "#151a20", high: "#2c343e", border: "#596571", glow: "rgba(125, 145, 162, .12)" },
    weakening: { fillFamily: "amber", low: "#3c2415", high: "#a95317", border: "#ffad5c", glow: "rgba(255, 145, 60, .24)" },
    laggard: { fillFamily: "magenta-red", low: "#3d1424", high: "#9e203f", border: "#ff6686", glow: "rgba(255, 64, 105, .32)" },
    unavailable: { fillFamily: "unavailable", low: "#12161a", high: "#20262c", border: "#424b54", glow: "transparent" },
  };
  const selected = palette[state];
  const accentBorder = state === "neutral"
    ? momentumAccent === "positive"
      ? "#4f8f86"
      : momentumAccent === "negative"
        ? "#8e5c59"
        : selected.border
    : momentumAccent === "positive"
      ? "#6bffd0"
      : momentumAccent === "negative"
        ? "#ff7b70"
        : selected.border;
  const glowStrength = Math.min(0.52, 0.12 + Math.abs(momentum ?? 0) / 20);
  return {
    state,
    fillFamily: selected.fillFamily,
    intensity,
    momentumAccent,
    fill: `linear-gradient(145deg, color-mix(in srgb, ${selected.high} ${Math.round(24 + intensity * 68)}%, ${selected.low}), ${selected.low})`,
    border: accentBorder,
    glow: selected.glow === "transparent"
      ? "none"
      : `inset 4px 0 ${accentBorder}, 0 0 18px color-mix(in srgb, ${selected.glow} ${Math.round(glowStrength * 100)}%, transparent)`,
  };
}

export function rotationStateLabel(state: InstitutionalRotationState): string {
  const labels: Record<InstitutionalRotationState, string> = {
    "strong-leader": "Strong Leader",
    leader: "Leader",
    neutral: "Neutral",
    weakening: "Weakening",
    laggard: "Laggard",
    unavailable: "Unavailable",
  };
  return labels[state];
}

export function marketTreemapLabelPolicy(size: TreemapDetailLevel): TreemapLabelPolicy {
  return {
    showName: true,
    showScore: false,
    showFlow: size === "small" || size === "medium" || size === "large",
    showRegime: size === "medium" || size === "large",
    showMomentum: size === "large",
    showRelativeStrength: false,
  };
}

export function projectRotationLayout(): RotationLayoutProjection {
  return {
    treemapBasisPercent: 62,
    secondaryPanel: "diagnostic-intelligence",
    rightRail: ["market-diagnostics", "capital-flow-story", "selected-sector-intelligence"],
    duplicatedPrimarySurfaces: [],
  };
}

function average(rows: SectorRotation[], getter: (row: SectorRotation) => unknown): number | null {
  const values = rows.map(getter).map(finite).filter((value): value is number => value !== null);
  return values.length > 0 ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function regime(score: number | null): string {
  if (score === null) return "資料校準中";
  if (score >= 62) return "擴張";
  if (score <= 45) return "收縮";
  return "中性";
}

function riskAppetite(score: number | null): string {
  if (score === null) return "資料校準中";
  if (score >= 60) return "風險偏好";
  if (score <= 42) return "風險趨避";
  return "中性";
}

function volatility(score: number | null): string {
  if (score === null) return "正常";
  if (score >= 65) return "穩定";
  if (score <= 42) return "升溫";
  return "正常";
}

export function abbreviateSector(label: string): string {
  const normalized = label.trim();
  const known: Record<string, string> = {
    "Communication Services": "COMM",
    "Consumer Discretionary": "DISC",
    "Consumer Staples": "STPL",
    "Real Estate": "REIT",
  };
  return known[normalized] ?? (normalized.split(/\s+/).map((part) => part[0]).join("").slice(0, 4).toUpperCase() || "--");
}

export function treemapDetailLevel(width: number, height: number): TreemapDetailLevel {
  const area = width * height;
  if (area >= 40000 && width >= 210 && height >= 145) return "large";
  if (area >= 18000 && width >= 135 && height >= 90) return "medium";
  if (area >= 6500 && width >= 82 && height >= 54) return "small";
  return "tiny";
}

export function buildRotationWorkspace(sectors: SectorRotation[], selectedSector?: string | null): RotationWorkspaceModel {
  const safeSectors = safeArray(sectors).filter((row) => row?.sector);
  const leaders = [...safeSectors]
    .sort((left, right) => (finite(right.score) ?? -1) - (finite(left.score) ?? -1))
    .slice(0, 5);
  const selected = safeSectors.find((row) => row.sector === selectedSector) ?? leaders[0] ?? null;
  const selectedCompanies = safeArray(selected?.companies).filter((company) => company?.ticker).slice(0, 5);
  const averageScore = average(safeSectors, (row) => row.score);
  const averageFlow = average(safeSectors, (row) => row.flow);
  const volatilityQuality = average(safeSectors, (row) => row.volatility_quality);
  const strengthening = safeSectors.filter((row) => (finite(row.momentum) ?? finite(row.momentum_20d) ?? 0) > 0).length;
  const weakening = safeSectors.filter((row) => (finite(row.momentum) ?? finite(row.momentum_20d) ?? 0) < 0).length;
  const biasScore = safeSectors.length > 0 ? 50 + ((strengthening - weakening) / safeSectors.length) * 50 : null;
  const bias = biasScore === null ? "資料校準中" : strengthening > weakening ? "偏多" : weakening > strengthening ? "偏空" : "平衡";

  return {
    leaders,
    selected,
    selectedCompanies,
    diagnostics: [
      { labelZh: "市場狀態", labelEn: "Market Regime", value: regime(averageScore), score: averageScore, state: averageScore !== null && averageScore >= 55 ? "live" : "neutral" },
      { labelZh: "風險偏好", labelEn: "Risk Appetite", value: riskAppetite(averageFlow), score: averageFlow, state: averageFlow !== null && averageFlow >= 55 ? "accumulation" : "neutral" },
      { labelZh: "波動狀態", labelEn: "Volatility", value: volatility(volatilityQuality), score: volatilityQuality, state: volatilityQuality !== null && volatilityQuality <= 42 ? "overheating" : "neutral" },
      { labelZh: "輪動方向", labelEn: "Rotation Bias", value: bias, score: biasScore, state: bias === "偏多" ? "accumulation" : bias === "偏空" ? "distribution" : "neutral" },
    ],
  };
}
