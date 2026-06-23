import {
  buildRankingLookup,
  lifecycleBadgeModel,
  rankingAwareThemeOrder,
  topEmergingThemeRanks,
} from "./themeRanking";
import type { ThemeRank, ThemeRegistryEntry } from "@/types/stock";

function rank(theme_id: string, rank_score: number, lifecycle: ThemeRank["lifecycle"]): ThemeRank {
  return {
    theme_id,
    theme_name: theme_id.replace(/_/g, " "),
    lifecycle,
    rank_score,
    momentum_score: 0,
    evidence_score: 0,
    research_score: 0,
    controller_score: 0,
    opportunity_score: 0,
    updated_at: "2026-06-21T00:00:00+00:00",
  };
}

function entry(theme_id: string, registryRank: number): ThemeRegistryEntry {
  return {
    theme_id,
    theme_name: theme_id.replace(/_/g, " "),
    status: "ACTIVE",
    source: "GRAPH",
    theme_type: "INDUSTRIAL",
    rank: registryRank,
    research_case_count: 0,
    graph_snapshot_count: 1,
    controller_count: 0,
    opportunity_count: 0,
    updated_at: "2026-06-21T00:00:00+00:00",
  };
}

export function themeRankingContractTest() {
  const rankings = [
    rank("hbm", 88, "ACTIVE"),
    rank("ai_power_grid", 81, "ACCELERATING"),
    rank("optical_ai_fabric", 72, "EMERGING"),
    rank("legacy_theme", 21, "DECLINING"),
  ];
  const registry = [
    entry("legacy_theme", 1000),
    entry("hbm", 1),
    entry("ai_power_grid", 2),
    entry("unranked", 999),
  ];
  const lookup = buildRankingLookup(rankings);
  const ordered = rankingAwareThemeOrder(registry, rankings);
  const badge = lifecycleBadgeModel("ACCELERATING");
  const emerging = topEmergingThemeRanks(rankings, 2);

  return {
    lookupUsesThemeId: lookup.get("hbm")?.rank === 1,
    rankingOrderOverridesRegistryRank:
      ordered.map((row) => row.theme_id).join(",") === "hbm,ai_power_grid,legacy_theme,unranked",
    rankBadges: ordered[0]?.rankBadge === "#1" && ordered[3]?.rankBadge === null,
    lifecycleBadgeColors:
      badge.label === "ACCELERATING" && badge.color === "green",
    topEmergingFilter:
      emerging.map((row) => row.theme_id).join(",") === "ai_power_grid,optical_ai_fabric",
  };
}
