# Phase 10.13 Quote Freshness and Backend Performance Design

## Scope

Phase 10.13 makes quote freshness explicit, prevents stale prices from being labeled live, and changes Theme Intelligence read endpoints to serve persisted outputs by default. Phase 11 is out of scope.

## Quote Freshness Contract

Every `/stock/{ticker}` response and nested `quote` object will expose:

- `fetched_at`
- `updated_at`
- `expires_at` when known
- `cache_age_seconds`
- `quote_status`
- `is_stale`
- `source`
- `is_market_open_context` when determinable

The backend is the authority for status:

- `live`: a provider returned the quote during the current request or the quote cache is unexpired.
- `stale`: an expired quote or endpoint cache supplied the price.
- `fallback`: last-known-good data supplied the price after providers failed.
- `unavailable`: no valid price exists.

Endpoint recovery may change lifecycle state but must also downgrade embedded quote status. Frontend normalization must preserve backend status and must never infer live status from price presence.

## Cache Policy

Quote TTL is selected per fetch:

- 60 seconds during regular US market context.
- 600 seconds outside regular US market context.
- 60 seconds when market context cannot be determined, as the conservative default.

SQLite cache reads will optionally return cache metadata without breaking existing callers. Quote payloads will carry their fetch timestamp so metadata survives through endpoint composition and frontend fallback.

## Force Refresh

`GET /stock/{ticker}?force_refresh=true` will:

1. Bypass endpoint and quote caches.
2. Fetch a provider quote and update quote/LKG caches.
3. Reuse existing endpoint research sections when available.
4. Replace only price, change, previous close, source, status, and freshness metadata.
5. Return stale or fallback quote metadata if providers fail.

It will not intentionally recompute bubble, earnings, smart money, news, or other research engines.

## Theme Read Performance

- Discovery GET reads `theme_discovery_scores`; `refresh=true` invokes collectors explicitly.
- Portfolio GET reads `theme_portfolios`; recomputation remains in seed/score/admin workflows.
- Aggregate uses theme-filtered repository reads and a short process-local TTL cache.
- Graph GET reads persisted edges.
- Overlap GET reads persisted `theme_overlap` edges and associated evidence rather than recomputing all pairs.

Aggregate caches are generation-based and invalidated after seed load, score/portfolio recomputation, and graph rebuild.

## Frontend Behavior

Stock Research displays a compact freshness line containing status, source, timestamp, and age. Hard-coded update timestamps are removed.

The stock local cache remains fallback-only. Cached stock payloads are acceptable only when their embedded freshness metadata is present; expired or fallback values retain stale/fallback labels.

Theme aggregate requests remain click/selection driven, abort on theme changes, do not run on hover, and are deduplicated by normalized theme ID while in flight.

## Verification

Tests cover status downgrades, LKG behavior, force refresh, metadata, market-aware TTL, persisted Theme reads, aggregate/graph behavior, frontend normalization, freshness rendering, request deduplication, and abort behavior.

Browser validation covers NVDA quote consistency, force refresh, visible freshness, Theme Discovery latency, selected-theme request counts, console/hydration health, and preservation of graph and supply-chain rendering.
