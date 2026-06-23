import type { DrilldownTarget } from "./drilldown";
import type { ThemeLeader, ThemeScore } from "@/types/stock";

export type FlowRankingSort = "flow" | "momentum" | "score";

export interface FlowRankingRow {
  id: string;
  rank: number;
  theme: string;
  score: number | null;
  flow: number | null;
  momentum: number | null;
  beneficiaries: ThemeLeader[];
  active: boolean;
  state?: string;
}

function finite(...values: Array<number | null | undefined>): number | null {
  return values.find((value) => typeof value === "number" && Number.isFinite(value)) ?? null;
}

function unique(rows: ThemeLeader[]): ThemeLeader[] {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const ticker = row.ticker?.toUpperCase();
    if (!ticker || seen.has(ticker)) return false;
    seen.add(ticker);
    return true;
  });
}

export function deriveFlowRanking(
  themes: Array<Partial<ThemeScore> & { theme: string }>,
  target: DrilldownTarget | null,
  sort: FlowRankingSort = "flow",
): FlowRankingRow[] {
  const active = (target?.subject ?? target?.name ?? target?.label ?? "").toLowerCase();
  return themes
    .map((theme) => ({
      id: theme.theme,
      rank: 0,
      theme: theme.theme,
      score: finite(theme.score, theme.theme_strength_score, theme.ranking_score, theme.leadership),
      flow: finite(theme.flow, theme.theme_capital_flow_score, theme.institutional_alignment),
      momentum: finite(theme.momentum, theme.momentum_strength, theme.relative_momentum, theme.acceleration),
      beneficiaries: unique([...(theme.leaders ?? []), ...(theme.top_alpha_stocks ?? []), ...(theme.related_stocks ?? [])]).slice(0, 4),
      active: theme.theme.toLowerCase() === active,
      state: theme.lifecycle_state ?? theme.status,
    }))
    .sort((left, right) => (right[sort] ?? -Infinity) - (left[sort] ?? -Infinity) || left.theme.localeCompare(right.theme))
    .map((row, index) => ({ ...row, rank: index + 1 }));
}
