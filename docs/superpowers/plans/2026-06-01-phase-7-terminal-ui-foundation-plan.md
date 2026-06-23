# Phase 7.0A Institutional Terminal UI Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a frontend-only institutional terminal UI foundation with centralized tokens, terminal rail navigation, reusable panels, and calmer workspace styling.

**Architecture:** Add a token layer and terminal primitives first, then refactor shell navigation and workspace panels to consume them. Existing `WorkspaceContext`, API clients, route behavior, and backend endpoints remain unchanged.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide React.

---

## File Structure

- Create: `frontend/src/styles/designTokens.ts`
  - Morandi colors, typography, icon, rail, and panel tokens.
- Modify: `frontend/src/theme/theme.ts`
  - Backward-compatible bridge from old `THEME` constants to new tokens.
- Modify: `frontend/src/app/globals.css`
  - CSS custom properties, base font stack, rail layout helpers, terminal panel helpers.
- Create: `frontend/src/components/terminal/TerminalPanel.tsx`
  - Shared institutional panel wrapper.
- Create: `frontend/src/components/terminal/TerminalRail.tsx`
  - Desktop rail layout wrapper.
- Create: `frontend/src/components/terminal/TerminalRailButton.tsx`
  - Icon-only rail button with tooltip.
- Create: `frontend/src/components/terminal/index.ts`
  - Export terminal primitives.
- Modify: `frontend/src/modules/terminalModules.ts`
  - Expand Lucide icon keys and Chinese-first display labels.
- Modify: `frontend/src/components/Dashboard.tsx`
  - Convert desktop top tabs to left terminal rail. Preserve mobile drawer and workspace routing.
- Modify: `frontend/src/components/ThemeForecastAIPage.tsx`
  - Apply terminal panel styling and command-center language.
- Modify: `frontend/src/components/SectorRotationPanel.tsx`
  - Apply terminal panel styling, remove temporary debug overlay/logging, remove gradient heatmap cards.
- Modify: `frontend/src/components/ThemeIntelligenceDashboard.tsx`
  - Apply tokenized panel styling and cleaner AI Theme Command Center hierarchy.
- Modify: `frontend/src/components/StockAnalysisWorkspace.tsx`
  - Apply tokenized page/panel chrome while preserving chart, bubble, smart money, news, analyst, and forecast behavior.

## Task 1: Design Tokens

- [ ] Create `frontend/src/styles/designTokens.ts` with the requested token values.
- [ ] Include helper exports for panel classes, rail dimensions, font stacks, and semantic text tones.
- [ ] Keep the file dependency-free.

## Task 2: CSS and Theme Bridge

- [ ] Update `frontend/src/theme/theme.ts` to export old keys from new tokens.
- [ ] Update `frontend/src/app/globals.css` root variables to Morandi tokens.
- [ ] Add base font family: `"IBM Plex Sans", "Noto Sans TC", Inter, system-ui, sans-serif`.
- [ ] Add `.terminal-shell`, `.terminal-main`, `.terminal-panel`, `.terminal-rail`, and `.terminal-rail-button` helper styles.

## Task 3: Terminal Primitives

- [ ] Create `TerminalPanel.tsx` with props: `eyebrow`, `title`, `description`, `actions`, `className`, `children`, `as`.
- [ ] Create `TerminalRailButton.tsx` with props: `label`, `secondaryLabel`, `icon`, `active`, `onClick`.
- [ ] Create `TerminalRail.tsx` with props: `brand`, `top`, `middle`, `bottom`, `className`.
- [ ] Export all primitives from `frontend/src/components/terminal/index.ts`.

## Task 4: Module Metadata

- [ ] Expand `TerminalIconKey` to include the Phase 7 Lucide icon map.
- [ ] Add `labelZh`, `labelEn`, and `railGroup` metadata.
- [ ] Preserve existing `id`, `title`, `shortTitle`, `target_tab`, `workspaceType`, and search keywords.

## Task 5: Dashboard Rail

- [ ] Import terminal primitives and expanded Lucide icons.
- [ ] Replace desktop top tab buttons with left rail buttons.
- [ ] Keep mobile drawer visible on small screens.
- [ ] Preserve `GlobalStockSearch`, `MarketTickerMarquee`, `activeContextLabel`, and all active workspace branches.
- [ ] Keep `WorkspaceProvider` and `dispatchWorkspaceAction` unchanged.

## Task 6: Workspace Panel Styling

- [ ] Apply `TerminalPanel` to key page chrome in Theme Forecast AI.
- [ ] Apply `TerminalPanel` to Sector Rotation and remove temporary debug overlay/logging.
- [ ] Apply `TerminalPanel` to Theme Intelligence command-center sections.
- [ ] Apply `TerminalPanel` to Stock Analysis side panels/page header without removing analytics.

## Task 7: Verification

- [ ] Run `git diff -- backend` and confirm no backend source changes from Phase 7.
- [ ] Run `rg -n "🔥|🚀|✨|💎|🧠|📈|📉|DEBUG|RAW_SECTOR|NORMALIZED_SECTOR|SECTOR_RENDER_ROW" frontend/src`.
- [ ] Run `rg -n "gradient|shadow-\\[0_|glow|cyan|purple|backdrop-blur" frontend/src/components frontend/src/app frontend/src/theme`.
- [ ] Run `npx tsc --noEmit` from `frontend`.
- [ ] Run `npm run build` from `frontend`.

