import {
  assertNoStockRecommendationLanguage,
  buildStockResearchSurfaceContract,
  orderThemeExposureByRank,
  projectPrimaryRole,
} from "./stockResearch";
import type { StockResearchResponse, StockResearchThemeExposure } from "@/types/stock";

function exposure(theme_id: string, rank: number): StockResearchThemeExposure {
  return {
    theme_id,
    theme_name: theme_id,
    rank,
    lifecycle: "ACTIVE",
    importance: 70,
    coverage: 80,
    evidence_count: 2,
  };
}

export function stockResearchContractTest() {
  const contract = buildStockResearchSurfaceContract();
  const ordered = orderThemeExposureByRank([exposure("cpo", 3), exposure("hbm", 1), exposure("cowos", 2)]);
  const primaryRole = projectPrimaryRole([
    { role_type: "Beneficiary", role_description: "exposed beneficiary", role_importance: 60, evidence_count: 1, evidence_ids: [1] },
    { role_type: "Constraint Resolver", role_description: "resolver evidence", role_importance: 91, evidence_count: 2, evidence_ids: [2, 3] },
  ]);
  const payload: StockResearchResponse = {
    available: true,
    ticker: "AMAT",
    generated_at: "2026-06-22T00:00:00+00:00",
    company_header: {
      company_name: "Applied Materials",
      ticker: "AMAT",
      theme_rank: 1,
      theme_lifecycle: "ACTIVE",
      research_coverage: 80,
      primary_theme: "CoWoS",
    },
    supply_chain_roles: [primaryRole],
    theme_exposure: ordered,
    investment_thesis: {
      why_it_matters: ["Evidence-backed role in a bottleneck path."],
      current_drivers: [],
      catalysts: [],
      risks: [],
      research_gaps: [],
    },
    evidence_chain: [
      { step_type: "Theme", label: "CoWoS", source: "graph_nodes", evidence_ids: [1] },
      { step_type: "Company", label: "Applied Materials", source: "graph_nodes", evidence_ids: [2] },
    ],
    research_completeness: {
      coverage: 80,
      evidence_strength: 75,
      validation_status: "Evidence Available",
      open_questions: [],
      research_gaps: [],
    },
    decision_support: {
      research_state: "Evidence Available",
      bull_case: [],
      bear_case: [],
      monitoring_triggers: [],
      research_gaps: [],
    },
    related_companies: {
      same_theme: [],
      same_bottleneck: [],
      same_controller: [],
      same_opportunity: [],
    },
  };

  return {
    allowedSurfaces:
      contract.allowed.join(">")
      === "company-header>supply-chain-role>theme-exposure>investment-thesis>evidence-chain>research-completeness>decision-support>related-companies",
    forbiddenSurfaces:
      contract.forbidden.includes("treemap")
      && contract.forbidden.includes("capital-flow-story")
      && contract.forbidden.includes("dependency-graph")
      && contract.forbidden.includes("quote-dashboard"),
    themeExposureOrdering: ordered.map((row) => row.theme_id).join(">") === "hbm>cowos>cpo",
    primaryRoleSelection: primaryRole.role_type === "Constraint Resolver",
    recommendationLanguageRejected:
      assertNoStockRecommendationLanguage(payload)
      && !assertNoStockRecommendationLanguage({ ...payload, decision_support: { ...payload.decision_support, research_state: "Buy" } }),
  };
}
