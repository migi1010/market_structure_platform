export const designTokens = {
  colors: {
    background: "#20242B",
    backgroundSecondary: "#262B33",
    panel: "#2A2F37",
    panelHover: "#313743",
    border: "#3A404A",
    accent: "#7C8796",
    accentSoft: "#909BA8",
    bullish: "#7E9C8C",
    bearish: "#A07B7B",
    warning: "#B39C72",
    highlight: "#D8D3C9",
    textPrimary: "#E2E6EB",
    textSecondary: "#B5BDC8",
    mutedText: "#8D97A5",
    success: "#7E9C8C",
    danger: "#B08989",
  },
  typography: {
    fontFamily: '"IBM Plex Sans", "Noto Sans TC", Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    monoFamily: '"IBM Plex Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace',
    pageTitle: "34px",
    sectionTitle: "22px",
    panelTitle: "16px",
    body: "14px",
    micro: "11px",
  },
  radii: {
    panel: "12px",
    control: "10px",
    compact: "8px",
  },
  spacing: {
    railWidth: "64px",
    railGap: "24px",
    pagePadding: "20px",
    panelPadding: "16px",
  },
  icons: {
    size: 18,
    default: "#7C8796",
    hover: "#D8D3C9",
    active: "#E2E6EB",
    activeBackground: "#313743",
  },
  panel: {
    className: "terminal-panel rounded-xl border border-[var(--theme-border)] bg-[var(--theme-panel)]",
    hoverClassName: "transition-colors hover:bg-[var(--theme-panel-hover)]",
  },
} as const;

export type DesignTokens = typeof designTokens;

