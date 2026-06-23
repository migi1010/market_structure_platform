import { resolveExactSearchResult } from "@/services/stockApi";
import type { ThemeRegistryEntry } from "@/types/stock";

function registryTheme(theme_id: string, theme_name: string): ThemeRegistryEntry {
  return {
    theme_id,
    theme_name,
    status: "ACTIVE",
    source: "GRAPH",
    theme_type: "INDUSTRIAL",
    rank: 1,
    research_case_count: 0,
    graph_snapshot_count: 1,
    controller_count: 0,
    opportunity_count: 0,
    updated_at: "2026-06-20T00:00:00+00:00",
  };
}

export function searchRoutingContractTest() {
  const registry = [
    registryTheme("cpo", "CPO"),
    registryTheme("cowos", "CoWoS"),
    registryTheme("glass_substrate", "Glass Substrate"),
  ];
  const cpo = resolveExactSearchResult("CPO", registry);
  const cowos = resolveExactSearchResult("CoWoS", registry);
  const glass = resolveExactSearchResult("Glass Substrate", registry);
  const ter = resolveExactSearchResult("TER");

  return {
    cpoRoutesToTheme: cpo?.workspaceAction?.actionType === "open_theme",
    cowosRoutesToTheme: cowos?.workspaceAction?.actionType === "open_theme",
    glassRoutesToTheme: glass?.workspaceAction?.actionType === "open_theme",
    terRoutesToStock: ter?.workspaceAction?.actionType === "open_stock",
  };
}
