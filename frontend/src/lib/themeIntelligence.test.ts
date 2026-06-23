import { emptyThemeAggregate, normalizeThemeAggregateResponse, normalizeThemeIntelligenceId, themeIntelligenceCacheKey } from "@/services/stockApi";
import type { ThemeAggregateResponse, ThemeScoresResponse } from "@/types/stock";

export function themeIntelligenceContractTest() {
  const aggregate: ThemeAggregateResponse = emptyThemeAggregate("Glass Substrate");
  const scores: ThemeScoresResponse = {
    themes: [{
      theme: "Glass Substrate",
      theme_id: "glass_substrate",
      ai_potential_score: 91,
      research_importance: 88,
      allocation_readiness: 76,
      risk_adjusted_score: 84,
      conviction_level: "High Conviction",
      score_components: {},
      major_strengths: [],
      major_risks: [],
      allocation_notes: [],
    }],
    rankings: {},
  };

  return {
    normalized: normalizeThemeIntelligenceId("Glass Substrate") === "glass_substrate",
    normalizedCowos: normalizeThemeIntelligenceId("CoWoS") === "cowos",
    cacheKeyStable: themeIntelligenceCacheKey("Glass Substrate") === "miji:theme-intelligence:v1:glass_substrate",
    emptySectionsPresent: Boolean(aggregate.score && aggregate.lifecycle && aggregate.catalysts && aggregate.bottlenecks && aggregate.beneficiaries && aggregate.portfolio_context && aggregate.supply_chain && aggregate.relationship_intelligence && aggregate.industrial_intelligence),
    emptyLifecycleIsNull: aggregate.lifecycle.lifecycle_stage === null && aggregate.lifecycle.lifecycle_confidence === null,
    scoreShapeStable: scores.themes[0].conviction_level === "High Conviction",
  };
}

export function industrialIntelligenceNormalizationContract() {
  const aggregate = normalizeThemeAggregateResponse({
    theme_id: "cpo_photonics",
    name: "CPO Photonics",
    industrial_intelligence: {
      identity: {
        requested_theme_id: "cpo",
        canonical_theme_key: "cpo_photonics",
        display_name: "CPO Photonics",
        aliases: ["CPO"],
        resolution_state: "alias",
      },
      lineage: { graph_snapshot_id: 20, lineage_state: "partial" },
      graph: {
        nodes: [{ node_type: "Theme", canonical_key: "cpo_photonics", display_name: "CPO Photonics" }],
        edges: [],
        dependency_paths: [],
        evidence_count: 3,
        counts_by_type: { Theme: 1 },
      },
      constraints: [],
      controllers: [],
      opportunities: [],
      decision_packets: { family: null, theme_packet: null, matching_packets: [] },
      coverage: {
        overall_coverage: 50,
        components: { Evidence: { numerator: 1, denominator: 2, coverage: 50, availability_state: "available" } },
      },
      research_gaps: [{ code: "NO_CONTROLLER_EVIDENCE", label: "Missing Controller evidence", layer: "Controller", state: "missing", observed_count: 0 }],
    },
  }, "CPO");

  return {
    canonicalIdentityPreserved: aggregate.industrial_intelligence.identity.canonical_theme_key === "cpo_photonics",
    missingScoresRemainEmpty: aggregate.industrial_intelligence.controllers.length === 0 && aggregate.industrial_intelligence.opportunities.length === 0,
    missingLineageRemainsNull: aggregate.industrial_intelligence.lineage.controller_snapshot_id === null,
    explicitGapPreserved: aggregate.industrial_intelligence.research_gaps[0]?.code === "NO_CONTROLLER_EVIDENCE",
  };
}

export function themeResearchSourceContract(source: string) {
  return {
    selectedAggregateFetchDocumented: source.includes("fetchThemeIntelligence(selectedThemeName"),
    noLegacyThemeDiscoveryApis: ![
      "fetchThemeTop(",
      "fetchThemeEmerging(",
      "fetchThemeRotation(",
      "fetchThemeCapitalFlow(",
      "fetchThemeNarrative(",
      "fetchThemeSupplyChain(",
      "fetchThemeDetail(",
      "fetchThemeDiscovery(",
    ].some((pattern) => source.includes(pattern)),
    hasThemeIntelligenceSummary: source.includes("function ThemeIntelligenceSummary"),
    hasSummarySections: [
      "Positioning",
      "Momentum",
      "Why Now",
      "Primary Bottleneck",
      "Conviction Summary",
      "Theme Relationship Intelligence",
    ].every((label) => source.includes(label)),
    hasHonestEvidenceStates:
      source.includes("No catalyst evidence available.")
      && source.includes("No bottleneck evidence available."),
    hasHonestRelationshipState:
      source.includes("No relationship intelligence available."),
    removesGaugePanel:
      !source.includes("marketTrendItems")
      && !source.includes("ai-market-trend")
      && !source.includes("ai-donut")
      && !source.includes("Theme Overview"),
  };
}

export function contextDockContract(source: string) {
  const clickFetchIndex = source.indexOf("fetchThemeIntelligence(themeSubject");
  const previewIndex = source.indexOf("const previewContext");
  return {
    clickCanFetchAggregate: clickFetchIndex >= 0,
    previewDoesNotFetchAggregate: previewIndex >= 0 && source.indexOf("fetchThemeIntelligence", previewIndex) === -1,
    routeChangeClearsDock: source.includes("setContextDock(null)") && source.includes("abortContextThemeFetch()"),
    rendersSupplyChainSummary: source.includes('label="Supply Chain"'),
    rendersControllers: source.includes('label="Controllers"'),
    rendersRiskSummary: source.includes('label="Risk Summary"'),
  };
}
