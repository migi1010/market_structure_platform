import type { ThemeRank, ThemeRankingLifecycle, ThemeRegistryEntry } from "@/types/stock";

export interface RankedThemeRegistryEntry extends ThemeRegistryEntry {
  ranking: ThemeRank | null;
  rankBadge: string | null;
  rankingLifecycle: ThemeRankingLifecycle | null;
}

export interface ThemeRankingBadge {
  label: ThemeRankingLifecycle;
  color: "cyan" | "green" | "gold" | "gray" | "red";
  className: string;
}

export interface RankedThemeLookupValue extends ThemeRank {
  rank: number;
}

export function normalizeThemeRankingKey(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

export function buildRankingLookup(rankings: ThemeRank[]): Map<string, RankedThemeLookupValue> {
  const sorted = [...rankings].sort((left, right) => (
    right.rank_score - left.rank_score
    || left.theme_id.localeCompare(right.theme_id)
  ));
  const lookup = new Map<string, RankedThemeLookupValue>();
  sorted.forEach((row, index) => {
    const ranked = { ...row, rank: index + 1 };
    [row.theme_id, row.theme_name, normalizeThemeRankingKey(row.theme_id), normalizeThemeRankingKey(row.theme_name)].forEach((key) => {
      const trimmed = key.trim();
      if (!trimmed || lookup.has(trimmed)) return;
      lookup.set(trimmed, ranked);
    });
  });
  return lookup;
}

export function lifecycleBadgeModel(lifecycle: ThemeRankingLifecycle): ThemeRankingBadge {
  const colors: Record<ThemeRankingLifecycle, ThemeRankingBadge["color"]> = {
    EMERGING: "cyan",
    ACCELERATING: "green",
    ACTIVE: "gold",
    MONITORING: "gray",
    DECLINING: "red",
  };
  const color = colors[lifecycle];
  return {
    label: lifecycle,
    color,
    className: `theme-lifecycle-badge theme-lifecycle-${color}`,
  };
}

export function rankingAwareThemeOrder(
  registryEntries: ThemeRegistryEntry[],
  rankings: ThemeRank[],
): RankedThemeRegistryEntry[] {
  const lookup = buildRankingLookup(rankings);
  const seen = new Set<string>();
  return registryEntries
    .filter((entry) => {
      const key = normalizeThemeRankingKey(entry.theme_id || entry.theme_name);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((entry) => {
      const ranking = lookup.get(entry.theme_id) ?? lookup.get(normalizeThemeRankingKey(entry.theme_id)) ?? lookup.get(normalizeThemeRankingKey(entry.theme_name)) ?? null;
      return {
        ...entry,
        ranking,
        rankBadge: ranking ? `#${ranking.rank}` : null,
        rankingLifecycle: ranking?.lifecycle ?? null,
      };
    })
    .sort((left, right) => {
      if (left.ranking && right.ranking) {
        return left.ranking.rank - right.ranking.rank;
      }
      if (left.ranking) return -1;
      if (right.ranking) return 1;
      if (right.rank !== left.rank) return right.rank - left.rank;
      return left.theme_id.localeCompare(right.theme_id);
    });
}

export function topEmergingThemeRanks(rankings: ThemeRank[], limit = 5): ThemeRank[] {
  return [...rankings]
    .filter((row) => row.lifecycle === "EMERGING" || row.lifecycle === "ACCELERATING")
    .sort((left, right) => (
      right.rank_score - left.rank_score
      || left.theme_id.localeCompare(right.theme_id)
    ))
    .slice(0, Math.max(0, limit));
}
