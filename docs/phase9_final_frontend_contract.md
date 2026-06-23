# Phase 9.2F Final Frontend Contract

Status: Accepted for manual QA  
Scope: Frontend behavior and workspace composition only. Backend, APIs, cache, quote enrichment, and data contracts are out of scope.

## Manual QA Checklist

Run the app at the normal frontend entry route (`/`) and use the terminal rail or universal search to switch workspaces.

- [ ] Rotation (`market-intel`) shows Rotation Snapshot, Sector Ranking, and Sector Intelligence only.
- [ ] Rotation treemap text adapts to tile size with no overlap, clipping, or overflow.
- [ ] Hovering a sector shows a temporary preview; leaving clears it.
- [ ] Clicking a sector creates persistent selection and opens the ContextDock collapsed.
- [ ] Double-clicking a sector drills down without leaving stale preview or beneficiary state.
- [ ] Theme Discovery (`theme-intelligence`) shows the AI prediction hero, ranking, overview, supply chain, beneficiaries, and deep dive.
- [ ] Selecting a theme updates Theme Discovery content and beneficiaries.
- [ ] Selecting a supply-chain role updates persistent selection and beneficiary context.
- [ ] Top Beneficiaries is populated from live data or the defined fallback chain.
- [ ] ContextDock expands on toggle, closes with its close button or `Escape`, and resets on workspace change.
- [ ] Universal search hover, click, and double-click follow the same preview, selection, and drilldown behavior.
- [ ] Stock, Supply Chain, Forecast, Beneficiaries, Screener, Bubble, and Smart Money workflows remain reachable.
- [ ] Browser console has no runtime errors, especially no undefined/null `.map`, `.filter`, or `.find` failures.

## Expected Workspaces And Components

The current frontend uses workspace module IDs as stateful routes. The browser entry route remains `/`.

| Manual destination | Module ID | Primary rendering boundary | Components or surfaces to verify |
| --- | --- | --- | --- |
| Rotation | `market-intel` | `ThemeResearchPage` rotation branch | `MarketTreemap`, Sector Ranking table, Sector Intelligence |
| AI Theme Discovery | `theme-intelligence` | `ThemeResearchPage` command branch | AI prediction hero, AI Theme Ranking, Theme Overview, Supply Chain Map, Top Beneficiaries, Theme Deep Dive |
| Supply Chain | `theme-supply-chain` | `ThemeResearchPage` supply-chain branch | `SupplyDependencyMap`, supply-role table, beneficiary preview |
| Theme Forecast | `theme-forecast` | `ThemeResearchPage` forecast branch | `ForecastTab` |
| Theme Beneficiaries | `theme-stocks` | `ThemeResearchPage` stocks branch | `BeneficiaryList` |
| Risk Overlay compatibility route | `theme-risk` | `ThemeResearchPage` risk branch | Contextual risk surfaces; not primary navigation |
| Stock Workspace | `stock-analysis` | `StockAnalysisWorkspace` | Existing stock analysis, Bubble, and Smart Money handoffs |
| Screener | `alpha-quant` | `AlphaQuantPage` | Existing ranking and drilldown behavior |
| Universal Search | Global header | `GlobalStockSearch` in `Dashboard` | Preview, selection, drilldown, and workspace dispatch |
| ContextDock | Global shell | `ContextDock` in `Dashboard` | Collapsed state, expansion, close/reset, selected entity content |

## Rotation Workspace Structure

Rotation is the focused sector-leadership workspace.

1. **Rotation Snapshot** is the dominant first-view visualization.
   - Uses calculated treemap geometry.
   - Area communicates relative importance.
   - Color communicates momentum.
   - Tile content adapts from full metrics on large tiles to title-only on tiny tiles.
2. **Sector Ranking** follows the snapshot.
   - Primary scan fields are RS, Momentum, Trend, and Status.
3. **Sector Intelligence** provides the selected sector's Leadership, Momentum, Forecast, Risk, and Last Update.

Capital Flow, Flow Graph, and Theme-to-Dependency-to-Beneficiary flow are intentionally absent from Rotation.

## AI Theme Discovery Workspace Structure

AI Theme Discovery is the flagship theme workspace and uses Chinese-first, English-secondary labels.

1. **Top AI Predicted Theme**
   - Dominant theme, AI potential score, trend strength, capital inflow, sentiment, attention, maturity, and crowding risk.
   - Includes Key Insight and Key Drivers.
2. **AI Theme Ranking**
   - Ranked theme discovery surface with score, trend, stage, and positioning recommendation.
   - Theme selection updates the active theme context.
3. **Theme Overview and Market Rotation Trend**
   - Compact stage distribution and market-regime context.
4. **Supply Chain Map**
   - Horizontal directional stages from upstream inputs to downstream applications.
   - Role clicks create the same persistent entity selection used by the rest of the workspace.
5. **Top Beneficiaries**
   - Shows ticker, company, relevance, beta, and estimated growth.
   - Must not retain rows from a previous selection.
6. **Theme Deep Dive**
   - Market Size Forecast, AI Trend Timeline, Risk and Challenges, Confidence Score, and Strategy Suggestions.

## ContextDock Behavior

`Dashboard` owns the ContextDock state. `Dashboard.contextDock.target` is the single persistent active entity selection.

- Default after click: dock is open but collapsed.
- Toggle: expands or collapses the selected context.
- Close button: clears selection and collapses the dock.
- `Escape`: clears selection, preview, and expanded state.
- Workspace/module change: clears the previous dock, preview, and expanded state.
- Hover preview is separate from ContextDock selection and appears only while no persistent dock is open.
- ContextDock is supplementary; workspace content must remain usable without expanding it.

## Selection Behavior

All interactive workspace surfaces should use the same interaction contract:

| Interaction | Expected behavior |
| --- | --- |
| Hover or focus | Show temporary preview only |
| Mouse leave or blur | Clear temporary preview only |
| Single click | Set `Dashboard.contextDock.target` and open the dock collapsed |
| Double click | Execute the shared drilldown action |
| Workspace change | Clear stale dock and preview state |

Persistent workspace consumers must derive from `Dashboard.contextDock.target`; temporary preview state must never drive beneficiaries or other persistent workspace content.

## Beneficiary Fallback Behavior

The pure resolver is `resolveActiveBeneficiaries` in `frontend/src/lib/beneficiaries.ts`. It must resolve fresh rows for the active entity and never reuse previous rows.

Fallback priority:

1. Explicit beneficiaries on the selected target.
2. Matching theme detail leaders or related stocks.
3. Matching theme leaders, top-alpha stocks, or related stocks.
4. Sector companies.
5. Supply-role leaders.
6. Supply-role constituents.
7. Capital-flow endpoint tickers.
8. Related-theme entities.
9. Compact empty state.

AI Theme Discovery currently adds a presentation-only final fallback (`NVDA`, `AVGO`, `AMAT`, `GLW`, `TSM`) when all live beneficiary sources are empty. Other surfaces should show an entity-specific compact empty state rather than stale rows.

## Remaining UI Debt

- Several Chinese navigation labels in `frontend/src/modules/terminalModules.ts` still contain mojibake and require a dedicated frontend label repair.
- AI Theme Discovery's presentation-only beneficiary fallback should eventually be replaced by consistently populated live payloads.
- Partial/live data can still produce `--` values; manual QA should confirm these remain legible and do not shift layouts.
- Mobile and narrow viewport layouts need dedicated visual QA beyond responsive stacking.
- Exact screenshot similarity still needs manual review on the target display using representative live data.
- Existing lint debt includes raw image usage and a `SectorRotationPanel` hook-dependency warning.
- Dependency audit findings remain outside this frontend visual contract.

## Implementation References

- Workspace shell and ContextDock ownership: `frontend/src/components/Dashboard.tsx`
- Workspace module registry: `frontend/src/modules/terminalModules.ts`
- Rotation and AI Theme Discovery composition: `frontend/src/components/ThemeResearchPage.tsx`
- Shared ContextDock primitives: `frontend/src/components/terminal/InteractionPrimitives.tsx`
- Adaptive treemap: `frontend/src/components/terminal/MarketTreemap.tsx`
- Beneficiary table surface: `frontend/src/components/terminal/BeneficiaryMatrix.tsx`
- Beneficiary resolver: `frontend/src/lib/beneficiaries.ts`
- Shared drilldown contract: `frontend/src/lib/drilldown.ts`
