import {
  buildSharedThemeRegistrySelector,
  buildRegistrySearchItems,
  findThemeRegistryEntry,
  sortThemeRegistryEntries,
  themeRegistrySelectionModel,
} from "./themeRegistry";
import type { ThemeRegistryEntry } from "@/types/stock";

function entry(
  theme_id: string,
  status: ThemeRegistryEntry["status"],
  rank: number,
  updated_at: string,
): ThemeRegistryEntry {
  return {
    theme_id,
    theme_name: theme_id.replace(/_/g, " "),
    status,
    source: status === "DISCOVERED" ? "SCOUT" : "GRAPH",
    theme_type: "INDUSTRIAL",
    rank,
    research_case_count: 0,
    graph_snapshot_count: status === "ACTIVE" ? 1 : 0,
    controller_count: 0,
    opportunity_count: 0,
    updated_at,
  };
}

export function themeRegistryContractTest() {
  const themes = [
    entry("archived_theme", "ARCHIVED", 1000, "2026-06-20T03:00:00+00:00"),
    entry("active_low", "ACTIVE", 1, "2026-06-20T02:00:00+00:00"),
    entry("discovered_theme", "DISCOVERED", 99, "2026-06-20T04:00:00+00:00"),
    entry("active_high", "ACTIVE", 50, "2026-06-20T01:00:00+00:00"),
  ];
  const sorted = sortThemeRegistryEntries(themes);
  const model = themeRegistrySelectionModel(sorted, "active_high");
  const searchItems = buildRegistrySearchItems([
    { ...entry("cpo_photonics", "ACTIVE", 10, "2026-06-20T01:00:00+00:00"), theme_name: "CPO Photonics" },
  ]);

  return {
    statusRankSort:
      sorted.map((theme) => theme.theme_id).join(",") === "active_high,active_low,discovered_theme,archived_theme",
    selectionUsesThemeId:
      model.selected?.theme_id === "active_high" && model.items[0]?.value === "active_high",
    selectedAlwaysVisible:
      buildSharedThemeRegistrySelector(themes, "archived_theme", "theme").selectedVisible,
    sharedSelectorTargets:
      buildSharedThemeRegistrySelector(themes, "active_high", "theme").workspace === "theme"
      && buildSharedThemeRegistrySelector(themes, "active_high", "supply-chain").workspace === "supply-chain"
      && buildSharedThemeRegistrySelector(themes, "active_high", "decision-intelligence").workspace === "decision-intelligence",
    nameLookup:
      findThemeRegistryEntry(themes, "discovered theme")?.theme_id === "discovered_theme",
    registrySearchUsesThemeId:
      searchItems[0]?.contextPayload?.theme === "cpo_photonics"
      && searchItems[0]?.theme === "cpo_photonics",
  };
}
