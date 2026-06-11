# Theme Momentum Dashboard Design

## Scope

Replace only the Theme Discovery sidebar panel currently labeled `Market Rotation Trend`.
Preserve the surrounding hero, ranking, theme overview, supply-chain, beneficiary, and deep-dive layouts.

## Problem

The current panel repeats lifecycle labels already shown elsewhere, uses decorative half-gauges,
and includes an unlabeled heat strip. It does not explain why a theme ranks highly or what could
constrain the thesis.

## Approved Direction

Use the approved Dense Research Stack in the existing sidebar footprint.

### Theme Momentum

Render four compact metrics:

- Current Stage: `aggregate.lifecycle.lifecycle_stage`
- Stage Confidence: `aggregate.lifecycle.lifecycle_confidence`
- Expected Next Stage: `aggregate.lifecycle.expected_next_stage`
- Estimated Time Window: `aggregate.lifecycle.time_window`

Missing values render `Unavailable`. Do not infer lifecycle values.

### Why Now

Render up to four names from `aggregate.catalysts.top_catalysts`, preserving aggregate order.
Use `name`, then `catalyst_name`. If no persisted catalyst names exist, render:

`No catalyst evidence available.`

### Primary Bottleneck

Use `aggregate.bottlenecks.primary_bottleneck`.

Render:

- Name from `name`, then `bottleneck_name`
- Severity from `severity_score`
- Resolution Probability from `resolution_probability`
- Controllers from `aggregate.bottlenecks.controllers`

Controller labels use persisted company name when present, otherwise ticker. If no primary
bottleneck exists, render:

`No bottleneck evidence available.`

Do not synthesize controllers from beneficiaries or supply-chain layers.

### Conviction Summary

Render compact metric cells from `aggregate.score`:

- Research Importance
- Allocation Readiness
- Risk Adjusted Score
- Conviction Level

Missing numeric values render `Unavailable`; missing conviction renders `Unrated`.

### Theme Overlap

Render the exact placeholder:

`Theme Overlap Intelligence will be available after Phase 10.12 Knowledge Graph Engine.`

No overlap metrics, links, or inferred relationships are introduced.

## Component Boundary

Create a focused `ThemeMomentumDashboard` component inside `ThemeResearchPage.tsx` because the
page already owns the selected aggregate and the change is limited to one presentation boundary.
The component receives the selected aggregate and contains no fetching, caching, or derived
intelligence.

## Styling

Replace `.ai-market-trend` gauge styles with compact terminal sections:

- Small section headers
- Two-column lifecycle and conviction grids
- Evidence list for catalysts
- Three-column bottleneck metrics
- Dashed placeholder card for Theme Overlap

No charts, gauges, progress bars, or decorative indicators are added.

## Testing

Add source-level contract assertions that require:

- `ThemeMomentumDashboard`
- all five section labels
- the exact catalyst and bottleneck empty states
- the exact Phase 10.12 placeholder
- absence of `marketTrendItems` and `.ai-market-trend`

Then verify:

- `npx tsc --noEmit`
- `npm run lint`
- `npm run build`
- Browser checks for HBM, Glass Substrate, and AI Infrastructure
- No console errors, hydration errors, overflow, duplicate keys, or mojibake

## Non-Goals

- No backend changes
- No new API requests
- No Knowledge Graph or Phase 10.12 work
- No changes to Theme Overview
- No unrelated Theme Discovery layout changes
