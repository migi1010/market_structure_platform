import {
  abbreviateSector,
  buildRotationWorkspace,
  capitalFlowWeight,
  marketTreemapLabelPolicy,
  momentumVisualState,
  normalizeRotationBandIntensity,
  projectRotationLayout,
  projectRotationVisual,
  projectRotationState,
  rotationStateLabel,
  rotationScoreBand,
  treemapDetailLevel,
} from "./rotationWorkspace";
import type { SectorRotation } from "@/types/stock";

const sectors: SectorRotation[] = [
  {
    sector: "Technology",
    score: 82,
    relative_strength: 78,
    flow: 74,
    momentum: 3.4,
    volatility_quality: 68,
    confidence_score: 81,
    rotation_state: "Accumulation",
    companies: [
      { ticker: "NVDA", company_name: "NVIDIA", alpha_score: 91 },
      { ticker: "MSFT", company_name: "Microsoft", alpha_score: 84 },
    ],
  },
  {
    sector: "Communication Services",
    score: 76,
    relative_strength: 71,
    flow: 67,
    momentum: 2.1,
    rotation_state: "Accumulation",
    companies: [],
  },
  {
    sector: "Energy",
    score: 42,
    relative_strength: 39,
    flow: 35,
    momentum: -1.8,
    rotation_state: "Distribution",
    companies: [],
  },
];

export function rotationWorkspaceContractTest() {
  const model = buildRotationWorkspace(sectors, "Technology");
  const missingCompanies = buildRotationWorkspace(
    [{ ...sectors[1], companies: undefined } as unknown as SectorRotation],
    "Communication Services",
  );

  return {
    leadersRanked: model.leaders.map((row) => row.sector).join(",") === "Technology,Communication Services,Energy",
    leadersLimited: model.leaders.length <= 5,
    selectedSector: model.selected?.sector === "Technology",
    selectedCompanies: model.selectedCompanies.map((row) => row.ticker).join(",") === "NVDA,MSFT",
    missingCompaniesSafe: missingCompanies.selectedCompanies.length === 0,
    diagnosticsPresent: model.diagnostics.every((item) => item.value !== undefined),
    diagnosticsChineseFirst: model.diagnostics.map((item) => item.labelZh).join(",") === "市場狀態,風險偏好,波動狀態,輪動方向",
    abbreviation: abbreviateSector("Communication Services") === "COMM",
    largeDetails: treemapDetailLevel(240, 180) === "large",
    tinyDetails: treemapDetailLevel(72, 42) === "tiny",
    scoreBands:
      rotationScoreBand(95) === "strong-green"
      && rotationScoreBand(75) === "green"
      && rotationScoreBand(55) === "yellow"
      && rotationScoreBand(35) === "orange"
      && rotationScoreBand(15) === "red",
    absoluteFlowSizing:
      capitalFlowWeight(-80) === 80
      && capitalFlowWeight(20) === 20
      && capitalFlowWeight(null) === 1,
    momentumProjection:
      momentumVisualState(1.2) === "improving"
      && momentumVisualState(-0.4) === "deteriorating"
      && momentumVisualState(0) === "flat"
      && momentumVisualState(null) === "unavailable",
    institutionalStates:
      projectRotationState(94, 2.4, 18) === "strong-leader"
      && projectRotationState(72, 1.2, 8) === "leader"
      && projectRotationState(55, 0, 0) === "neutral"
      && projectRotationState(43, -0.8, 4) === "weakening"
      && projectRotationState(24, -1.8, -12) === "laggard",
    stateLabels:
      rotationStateLabel("strong-leader") === "Strong Leader"
      && rotationStateLabel("leader") === "Leader"
      && rotationStateLabel("neutral") === "Neutral"
      && rotationStateLabel("weakening") === "Weakening"
      && rotationStateLabel("laggard") === "Laggard",
    visualStates:
      projectRotationVisual(94, 2.4, 18).fillFamily === "cyan-green"
      && projectRotationVisual(72, 1.2, 8).fillFamily === "teal"
      && projectRotationVisual(55, 0, 0).fillFamily === "graphite"
      && projectRotationVisual(43, -0.8, 4).fillFamily === "amber"
      && projectRotationVisual(24, -1.8, -12).fillFamily === "magenta-red",
    neutralIsNotYellow:
      !projectRotationVisual(55, 0, 0).fill.toLowerCase().includes("yellow")
      && !projectRotationVisual(55, 0, 0).fill.toLowerCase().includes("olive"),
    momentumChangesAccent:
      projectRotationVisual(55, 1, 0).momentumAccent
      !== projectRotationVisual(55, -1, 0).momentumAccent,
    neutralAccentRemainsMuted:
      projectRotationVisual(55, 1, 0).border
      !== projectRotationVisual(94, 2.4, 18).border,
    withinBandIntensity:
      normalizeRotationBandIntensity("neutral", 40) === 0
      && normalizeRotationBandIntensity("neutral", 50) === 0.5
      && normalizeRotationBandIntensity("neutral", 60) === 1
      && normalizeRotationBandIntensity("strong-leader", 90)
        > normalizeRotationBandIntensity("strong-leader", 82),
    strictLabelDensity:
      marketTreemapLabelPolicy("tiny").showScore === false
      && marketTreemapLabelPolicy("small").showFlow === false
      && marketTreemapLabelPolicy("medium").showFlow
      && marketTreemapLabelPolicy("large").showRegime,
    hierarchyProjection:
      projectRotationLayout().treemapBasisPercent >= 60
      && projectRotationLayout().treemapBasisPercent <= 65
      && projectRotationLayout().secondaryPanel === "diagnostic-intelligence"
      && !projectRotationLayout().duplicatedPrimarySurfaces.includes("ranking"),
    rightRailContainsOnlyAllowedSurfaces:
      projectRotationLayout().rightRail.join(">")
      === "market-diagnostics>capital-flow-story>selected-sector-intelligence",
  };
}
