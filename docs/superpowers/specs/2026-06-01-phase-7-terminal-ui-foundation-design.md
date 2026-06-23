# Phase 7.0A Institutional Terminal UI Foundation Design

## Goal

Transform the MIJI frontend from an AI dashboard into an institutional AI research terminal while preserving all existing backend contracts, local_full forecast workflows, quote rendering, factor rendering, bubble analysis, smart money analysis, theme intelligence, sector rotation, and omnibox behavior.

## Scope

This phase is frontend-only. It introduces a centralized visual token system, shared terminal layout primitives, a left icon rail, a cleaner command-center homepage structure, and a calmer Morandi financial palette. It does not modify backend code, API contracts, data normalization behavior, or quant logic.

## Design Principles

The interface should feel like a research workstation: dense, calm, scannable, and durable for long sessions. It should not feel like an AI SaaS dashboard, crypto dashboard, marketing site, or neon/glow interface.

Visual direction:

- Flat institutional panels
- Subtle borders
- Minimal shadows
- No glow or cyberpunk effects
- No gradient-driven cards
- Muted Morandi palette
- Monochrome Lucide icons
- Chinese-first labels with English secondary terminology

## Design Token System

Create `frontend/src/styles/designTokens.ts` as the single source of truth for the Phase 7 UI foundation.

Token groups:

- `colors`: background, panels, borders, text, semantic market tones
- `typography`: font stacks and type sizes
- `radii`: panel and control radius values
- `spacing`: rail and panel spacing primitives
- `icons`: rail icon size and colors
- `panel`: common panel classes

`frontend/src/theme/theme.ts` and `frontend/src/app/globals.css` will bridge to these tokens so existing components can migrate incrementally.

## Terminal Primitives

Create reusable frontend primitives under `frontend/src/components/terminal/`:

- `TerminalPanel`: consistent panel shell with optional eyebrow/title/action slots
- `TerminalRail`: fixed-width left rail layout with top/middle/bottom groups
- `TerminalRailButton`: icon-only rail button with tooltip and active state

These primitives should use Lucide icons only and avoid colored or decorative icon treatments.

## Navigation Refactor

`Dashboard.tsx` will move from top-tab navigation to a left terminal rail on desktop. The existing mobile drawer remains, but its visual styling should follow the new token system.

The rail becomes the primary navigation source of truth using `terminalModules.ts`.

Desktop layout:

- Left rail: 64px fixed width
- Main shell: header/search/context strip and workspace content
- Rail top: brand/home or primary terminal entry
- Rail middle: workspace modules
- Rail bottom: search/settings/notifications/watchlist controls where applicable

## Workspace Preservation

The following existing systems must remain functional:

- Global omnibox and workspace action dispatch
- `WorkspaceContext` persistence
- Theme Forecast AI page
- Theme Intelligence page
- Sector Rotation page
- Alpha Quant page
- Portfolio/watchlist page
- Stock Analysis page
- TradingView chart
- Bubble engine
- Smart money engine
- Analyst forecast panel
- News intelligence panel

Phase 7.0A is layout and visual-system work, not data-system work.

## Homepage / Command Center

The default research surface should become an AI Theme Command Center and emphasize only:

1. Today's Leading Themes
2. Emerging Themes
3. Capital Rotation Flow
4. Forecast Heatmap
5. Theme -> Stock Drilldown

This cleanup should happen inside the existing theme/forecast workspace surfaces without removing data features. Sections not included in the command center can remain reachable in deeper panels or existing workspaces.

## Language System

Visible navigation and key workspace labels should move toward Chinese-first + English-secondary labels. English institutional vocabulary remains present for professional scanning.

Examples:

- 主題預測 Forecast
- 板塊輪動 Rotation
- 相對強度 RS
- 資金流向 Flow
- 領導強度 Leadership
- 弱化 Weakening
- 新興主題 Emerging
- 泡沫風險 Bubble
- 聰明錢 Smart Money
- 敘事動能 Narrative

## Error Handling

No UI refactor should make backend data mandatory. Existing partial_live, warming, degraded, unavailable, and fallback rendering semantics must remain intact. Missing data should continue to render as explicit unavailable/warming states rather than fabricated values.

## Verification

Required checks before completion:

- `npx tsc --noEmit`
- `npm run build`
- Static scan for backend changes
- Static scan for emoji UI
- Static scan for remaining debug sector overlays/logs if touched
- Static scan for obvious neon/glow/gradient regressions in touched files

Manual checks:

- Left rail appears on desktop
- Mobile navigation still works
- Omnibox still opens and routes
- Theme Forecast AI remains available
- Theme Intelligence remains available
- Sector Rotation remains available
- Stock Analysis still renders TradingView, bubble, smart money, forecast panels
- Chinese-first labels appear in primary navigation/workspace chrome

