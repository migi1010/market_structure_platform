import type { StockResearchResponse, StockResearchRole, StockResearchThemeExposure } from "@/types/stock";

const FORBIDDEN_RECOMMENDATION_TERMS = [
  "buy",
  "sell",
  "hold",
  "target price",
  "allocation",
  "portfolio weight",
  "position size",
  "price prediction",
  "fair value",
  "intrinsic value",
  "llm conviction",
  "generated recommendation",
];

const ROLE_PRIORITY: Record<string, number> = {
  "Constraint Resolver": 5,
  Controller: 4,
  Supplier: 3,
  Enabler: 2,
  Beneficiary: 1,
};

export function buildStockResearchSurfaceContract() {
  return {
    question: "Which company benefits?",
    allowed: [
      "company-header",
      "supply-chain-role",
      "theme-exposure",
      "investment-thesis",
      "evidence-chain",
      "research-completeness",
      "decision-support",
      "related-companies",
    ],
    forbidden: [
      "treemap",
      "capital-flow-story",
      "scout-queue",
      "theme-ranking-panel",
      "dependency-graph",
      "pipeline-board",
      "quote-dashboard",
      "factor-dashboard",
    ],
  };
}

export function orderThemeExposureByRank(rows: StockResearchThemeExposure[]): StockResearchThemeExposure[] {
  return [...rows].sort((left, right) => {
    const leftRank = Number.isFinite(left.rank) && left.rank !== null ? left.rank : 9999;
    const rightRank = Number.isFinite(right.rank) && right.rank !== null ? right.rank : 9999;
    return leftRank - rightRank || right.importance - left.importance || left.theme_id.localeCompare(right.theme_id);
  });
}

export function projectPrimaryRole(rows: StockResearchRole[]): StockResearchRole {
  const [role] = [...rows].sort((left, right) => {
    const priority = (ROLE_PRIORITY[right.role_type] ?? 0) - (ROLE_PRIORITY[left.role_type] ?? 0);
    return priority || right.role_importance - left.role_importance || right.evidence_count - left.evidence_count;
  });
  return role ?? {
    role_type: "Unavailable",
    role_description: "No persisted stock role evidence is available.",
    role_importance: 0,
    evidence_count: 0,
    evidence_ids: [],
  };
}

export function assertNoStockRecommendationLanguage(payload: StockResearchResponse | Record<string, unknown>): boolean {
  const raw = JSON.stringify(payload).toLowerCase();
  return !FORBIDDEN_RECOMMENDATION_TERMS.some((term) => raw.includes(term));
}

export function stockResearchCoverageLabel(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
  return `${Math.round(Math.max(0, Math.min(100, value)))}%`;
}
