import { buildSharedThemeRegistrySelector } from "./themeRegistry";
import { rankingAwareThemeOrder } from "./themeRanking";
import type { ThemeRank, ThemeRegistryEntry } from "@/types/stock";

function entry(theme_id: string, rank: number): ThemeRegistryEntry {
  return {
    theme_id,
    theme_name: theme_id.replace(/_/g, " "),
    status: "ACTIVE",
    source: "GRAPH",
    theme_type: "INDUSTRIAL",
    rank,
    research_case_count: 0,
    graph_snapshot_count: 1,
    controller_count: 0,
    opportunity_count: 0,
    updated_at: "2026-06-21T00:00:00+00:00",
  };
}

function themeRank(theme_id: string, rank_score: number, lifecycle: ThemeRank["lifecycle"]): ThemeRank {
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

export function themeRegistrySelectionRankingContractTest() {
  const registry = [entry("low_registry_rank", 1), entry("high_dynamic_rank", 0)];
  const rankings = [
    themeRank("high_dynamic_rank", 91, "ACTIVE"),
    themeRank("low_registry_rank", 12, "MONITORING"),
  ];
  const ordered = rankingAwareThemeOrder(registry, rankings);
  const selector = buildSharedThemeRegistrySelector(ordered, "high_dynamic_rank", "theme");

  return {
    selectorReceivesRankingOrder:
      selector.items.map((row) => row.value).join(",") === "high_dynamic_rank,low_registry_rank",
    selectorItemsExposeRankAndLifecycle:
      selector.items[0]?.rankBadge === "#1"
      && selector.items[0]?.rankingLifecycle === "ACTIVE"
      && selector.items[1]?.rankingLifecycle === "MONITORING",
  };
}
