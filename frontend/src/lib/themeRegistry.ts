import type { SearchResult, ThemeRankingLifecycle, ThemeRegistryEntry, WorkspaceAction } from "@/types/stock";

const STATUS_ORDER: Record<ThemeRegistryEntry["status"], number> = {
  ACTIVE: 0,
  DISCOVERED: 1,
  ARCHIVED: 2,
};

export interface ThemeRegistrySelectorItem {
  value: string;
  label: string;
  status: ThemeRegistryEntry["status"];
  source: ThemeRegistryEntry["source"];
  themeType: ThemeRegistryEntry["theme_type"];
  rankBadge?: string | null;
  rankingLifecycle?: ThemeRankingLifecycle | null;
}

export interface ThemeRegistrySelectionModel {
  items: ThemeRegistrySelectorItem[];
  selected: ThemeRegistryEntry | null;
}

export type SharedThemeRegistryWorkspace = "theme" | "supply-chain" | "decision-intelligence";

export interface SharedThemeRegistrySelectorModel extends ThemeRegistrySelectionModel {
  workspace: SharedThemeRegistryWorkspace;
  selectedVisible: boolean;
}

function compact(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function searchText(value: string): string {
  return value.trim().toUpperCase().replace(/[^A-Z0-9. ]+/g, " ").replace(/\s+/g, " ");
}

export function sortThemeRegistryEntries(entries: ThemeRegistryEntry[]): ThemeRegistryEntry[] {
  return [...entries].sort((left, right) => {
    const status = STATUS_ORDER[left.status] - STATUS_ORDER[right.status];
    if (status !== 0) return status;
    if (right.rank !== left.rank) return right.rank - left.rank;
    const time = right.updated_at.localeCompare(left.updated_at);
    if (time !== 0) return time;
    return left.theme_id.localeCompare(right.theme_id);
  });
}

export function findThemeRegistryEntry(
  entries: ThemeRegistryEntry[],
  value: string,
): ThemeRegistryEntry | null {
  const normalized = compact(value);
  return entries.find((entry) => (
    compact(entry.theme_id) === normalized
    || compact(entry.theme_name) === normalized
  )) ?? null;
}

export function themeRegistrySelectionModel(
  entries: ThemeRegistryEntry[],
  selectedThemeId?: string,
): ThemeRegistrySelectionModel {
  const sorted = sortThemeRegistryEntries(entries);
  return {
    items: sorted.map((entry) => ({
      value: entry.theme_id,
      label: entry.theme_name,
      status: entry.status,
      source: entry.source,
      themeType: entry.theme_type,
      rankBadge: "rankBadge" in entry ? entry.rankBadge as string | null : null,
      rankingLifecycle: "rankingLifecycle" in entry ? entry.rankingLifecycle as ThemeRankingLifecycle | null : null,
    })),
    selected: selectedThemeId ? findThemeRegistryEntry(sorted, selectedThemeId) : sorted[0] ?? null,
  };
}

export function buildSharedThemeRegistrySelector(
  entries: ThemeRegistryEntry[],
  selectedThemeId: string | undefined,
  workspace: SharedThemeRegistryWorkspace,
): SharedThemeRegistrySelectorModel {
  const sorted = sortThemeRegistryEntries(entries);
  const selected = selectedThemeId ? findThemeRegistryEntry(sorted, selectedThemeId) : sorted[0] ?? null;
  const visibleEntries = selected && !sorted.some((entry) => entry.theme_id === selected.theme_id)
    ? [selected, ...sorted]
    : sorted;
  return {
    workspace,
    items: visibleEntries.map((entry) => ({
      value: entry.theme_id,
      label: entry.theme_name,
      status: entry.status,
      source: entry.source,
      themeType: entry.theme_type,
      rankBadge: "rankBadge" in entry ? entry.rankBadge as string | null : null,
      rankingLifecycle: "rankingLifecycle" in entry ? entry.rankingLifecycle as ThemeRankingLifecycle | null : null,
    })),
    selected,
    selectedVisible: selected ? visibleEntries.some((entry) => entry.theme_id === selected.theme_id) : false,
  };
}

function workspaceActionForTheme(entry: ThemeRegistryEntry): WorkspaceAction {
  return {
    actionType: "open_theme",
    target_tab: "theme-intelligence",
    focusTarget: "theme-detail",
    openMode: "replace",
    contextPayload: {
      theme: entry.theme_id,
      themeView: "command",
      label: `Open ${entry.theme_name}`,
    },
  };
}

export function buildRegistrySearchItems(entries: ThemeRegistryEntry[]): SearchResult[] {
  return sortThemeRegistryEntries(entries).map((entry) => {
    const action = workspaceActionForTheme(entry);
    return {
      id: `theme-registry:${entry.theme_id}`,
      symbol: `THEME:${entry.theme_id.toUpperCase().replace(/[^A-Z0-9]+/g, "-")}`,
      name: entry.theme_name,
      exchange: entry.source,
      type: "Theme",
      theme: entry.theme_id,
      label: entry.theme_name,
      description: `${entry.status} ${entry.theme_type} theme`,
      intent: "theme",
      group: "Themes",
      target_tab: "theme-intelligence",
      actionType: action.actionType,
      focusTarget: action.focusTarget,
      contextPayload: action.contextPayload,
      openMode: action.openMode,
      workspaceAction: action,
    };
  });
}

export function matchesRegistryTheme(entry: ThemeRegistryEntry, query: string): boolean {
  const normalized = searchText(query);
  const themeId = searchText(entry.theme_id);
  const name = searchText(entry.theme_name);
  return themeId === normalized
    || name === normalized
    || themeId.includes(normalized)
    || name.includes(normalized);
}
