"use client";

import { lifecycleBadgeModel } from "@/lib/themeRanking";
import type { ThemeRegistryEntry } from "@/types/stock";

type RankedThemeEntry = ThemeRegistryEntry & {
  ranking?: {
    momentum_score?: unknown;
    evidence_score?: unknown;
  } | null;
};

interface DynamicThemeRotationPanelProps {
  themes: RankedThemeEntry[];
  selectedTheme?: string | null;
  onThemeSelect?: (theme: string) => void;
  titleZh?: string;
  titleEn?: string;
  limit?: number;
  variant?: "rail" | "ribbon" | "compact";
}

function numeric(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function score(value: unknown): string {
  const parsed = numeric(value);
  return parsed === null ? "Unavailable" : parsed.toFixed(0);
}

function isSelected(theme: ThemeRegistryEntry, selectedTheme?: string | null): boolean {
  if (!selectedTheme) return false;
  const target = selectedTheme.trim().toLowerCase();
  return theme.theme_id.toLowerCase() === target || theme.theme_name.toLowerCase() === target;
}

export default function DynamicThemeRotationPanel({
  themes,
  selectedTheme,
  onThemeSelect,
  titleZh = "主題輪動",
  titleEn = "Theme Rotation",
  limit = 5,
  variant = "rail",
}: DynamicThemeRotationPanelProps) {
  const visibleThemes = themes.slice(0, Math.max(0, limit));

  return (
    <section className={`dynamic-theme-rotation-panel dynamic-theme-rotation-panel--${variant}`} aria-label={`${titleZh} ${titleEn}`}>
      <header>
        <strong>{titleZh}</strong>
        <span>{titleEn}</span>
      </header>
      <div className="dynamic-theme-rotation-list">
        {visibleThemes.length > 0 ? visibleThemes.map((theme) => {
          const lifecycle = "rankingLifecycle" in theme ? theme.rankingLifecycle : null;
          const ranking = theme.ranking ?? null;
          const badge = lifecycle ? lifecycleBadgeModel(lifecycle) : null;
          return (
            <button
              key={theme.theme_id}
              type="button"
              data-selected={isSelected(theme, selectedTheme)}
              onClick={() => onThemeSelect?.(theme.theme_id)}
            >
              <b>{("rankBadge" in theme && theme.rankBadge) ? theme.rankBadge : "--"}</b>
              <span>
                <strong>{theme.theme_name}</strong>
                {badge ? <em className={badge.className}>{badge.label}</em> : <em>Lifecycle unavailable</em>}
              </span>
              <dl>
                <span><dt>Momentum</dt><dd>{score(ranking?.momentum_score)}</dd></span>
                <span><dt>Evidence</dt><dd>{score(ranking?.evidence_score)}</dd></span>
              </dl>
            </button>
          );
        }) : (
          <p>Ranked themes unavailable</p>
        )}
      </div>
    </section>
  );
}
