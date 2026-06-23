import type {
  AlphaQuantResponse,
  EmergingThemeResponse,
  MarketOverviewItem,
  MarketOverviewResponse,
  OmniboxGroup,
  OmniboxIntent,
  OmniboxTargetTab,
  SearchResult,
  RotationSnapshotResponse,
  RotationStatus,
  SectorRotation,
  StockAnalysis,
  StockResearchResponse,
  StockQuote,
  AlphaQuantRow,
  NarrativeIntelligence,
  ThemeScore,
  ThemeCapitalFlowResponse,
  ThemeDetailResponse,
  ThemeAggregateResponse,
  ThemeBeneficiaryRecord,
  ThemeBottleneckRecord,
  ThemeCatalystRecord,
  ThemeDiscoveryRecord,
  ThemeDiscoveryResponse,
  ThemePortfolioRecord,
  ThemePortfolioResponse,
  ThemeScoreRecord,
  ThemeScoresResponse,
  ThemeNarrativeResponse,
  ThemeForecastResponse,
  ThemeForecastValidationResponse,
  ForecastHorizon,
  ThemeRotationResponse,
  ThemeStocksResponse,
  ThemeSupplyChainResponse,
  ThemeTopResponse,
  WorkspaceAction,
  ThemeScoutCandidate,
  ThemeScoutResponse,
  ThemeRegistryEntry,
  ThemeRegistryResponse,
  ThemeRank,
  ThemeRankingResponse,
  ResearchPipelineCaseDetail,
  ResearchPipelineResponse,
  DecisionIntelligenceDetailResponse,
  DecisionIntelligenceResponse,
} from "@/types/stock";
import { enabledTerminalModules } from "@/modules/terminalModules";
import { buildRegistrySearchItems, matchesRegistryTheme, sortThemeRegistryEntries } from "@/lib/themeRegistry";

const RENDER_API_URL = "https://market-structure-platform.onrender.com";
const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL;
const IS_PRODUCTION = process.env.NODE_ENV === "production";
const IS_DEVELOPMENT = process.env.NODE_ENV === "development";

function resolveApiBaseUrl(value: string | undefined): string {
  const trimmed = value?.trim().replace(/\/+$/, "");
  if (!trimmed) return RENDER_API_URL;
  try {
    const parsed = new URL(trimmed);
    if (!/^https?:$/.test(parsed.protocol)) return RENDER_API_URL;
    if (IS_PRODUCTION && (parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1" || parsed.hostname === "::1")) {
      return RENDER_API_URL;
    }
    return parsed.toString().replace(/\/+$/, "");
  } catch {
    return RENDER_API_URL;
  }
}

const API_URL = resolveApiBaseUrl(RAW_API_URL);
const STOCK_PROXY_URL = "/api/stock";
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_ATTEMPTS = 3;
const CLIENT_CACHE_SCHEMA_VERSION = "stock_v7_factor_ui";
const themeIntelligenceRequests = new Map<string, Promise<unknown>>();

interface LocalCacheEnvelope<T> {
  schema_version: string;
  cached_at: string;
  data: T;
}

interface CanonicalQuoteFields {
  canonicalPrice: number | null;
  canonicalChange: number | null;
  canonicalChangePercent: number | null;
  canonicalMarketCap: number | null;
  canonicalQuoteStatus: string;
  canonicalSector: string;
}

const POPULAR_SYMBOLS: SearchResult[] = [
  { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "NVDA", name: "NVIDIA Corporation", exchange: "NASDAQ", type: "Equity" },
  { symbol: "TSLA", name: "Tesla, Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "META", name: "Meta Platforms, Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "PLTR", name: "Palantir Technologies Inc.", exchange: "NYSE", type: "Equity" },
  { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", type: "Equity" },
  { symbol: "SPY", name: "SPDR S&P 500 ETF Trust", exchange: "NYSEARCA", type: "ETF" },
  { symbol: "QQQ", name: "Invesco QQQ Trust", exchange: "NASDAQ", type: "ETF" },
  { symbol: "AMD", name: "Advanced Micro Devices, Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "AVGO", name: "Broadcom Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "AMAT", name: "Applied Materials, Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "TSM", name: "Taiwan Semiconductor Manufacturing Company Limited", exchange: "NYSE", type: "Equity" },
  { symbol: "ASML", name: "ASML Holding N.V.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "KLAC", name: "KLA Corporation", exchange: "NASDAQ", type: "Equity" },
  { symbol: "TER", name: "Teradyne, Inc.", exchange: "NASDAQ", type: "Equity" },
  { symbol: "GLW", name: "Corning Incorporated", exchange: "NYSE", type: "Equity" },
  { symbol: "NOW", name: "ServiceNow, Inc.", exchange: "NYSE", type: "Equity" },
];

const UNIVERSAL_SEARCH: SearchResult[] = [
  { symbol: "SEMICONDUCTOR", name: "Semiconductor", exchange: "Sector", type: "Sector" },
  { symbol: "UTILITIES", name: "Utilities", exchange: "Sector", type: "Sector" },
  { symbol: "ENERGY", name: "Energy", exchange: "Sector", type: "Sector" },
  { symbol: "FINANCIALS", name: "Financials", exchange: "Sector", type: "Sector" },
  { symbol: "SMH", name: "VanEck Semiconductor ETF", exchange: "ETF", type: "ETF" },
  { symbol: "SOXX", name: "iShares Semiconductor ETF", exchange: "ETF", type: "ETF" },
  { symbol: "QQQ", name: "Invesco QQQ Trust", exchange: "ETF", type: "ETF" },
];

interface OmniboxRegistryItem extends SearchResult {
  aliases: string[];
}

const OMNIBOX_COMMANDS: OmniboxRegistryItem[] = enabledTerminalModules.filter((module) => module.workspaceType !== "stock").map((module) => ({
  symbol: module.shortTitle.toUpperCase().replace(/[^A-Z0-9]+/g, "-"),
  name: module.title,
  exchange: "Command",
  type: "Command",
  command: `open-${module.id}`,
  label: module.title,
  description: module.description,
  intent: "command",
  group: "Commands",
  target_tab: module.target_tab,
  aliases: [module.title, module.shortTitle, ...module.searchKeywords],
}));

const THEME_RESEARCH_COMMANDS: OmniboxRegistryItem[] = [
  {
    symbol: "THEME-FORECAST",
    name: "Open Theme Forecast",
    exchange: "Command",
    type: "Command",
    command: "open-theme-forecast",
    label: "Open Theme Forecast",
    description: "Open the Forecast tab inside Theme Research",
    intent: "command",
    group: "Commands",
    target_tab: "theme-forecast",
    aliases: ["forecast", "theme forecast", "future themes", "theme ai", "regime forecast"],
  },
  {
    symbol: "CAPITAL-ROTATION",
    name: "Open Capital Rotation",
    exchange: "Command",
    type: "Command",
    command: "open-capital-rotation",
    label: "Open Capital Rotation",
    description: "Open the Rotation tab inside Theme Research",
    intent: "command",
    group: "Commands",
    target_tab: "market-intel",
    aliases: ["sector", "sector rotation", "capital rotation", "capital flow", "relative strength"],
  },
  {
    symbol: "SUPPLY-CHAIN",
    name: "Open Supply Chain",
    exchange: "Command",
    type: "Command",
    command: "open-supply-chain",
    label: "Open Supply Chain",
    description: "Open supply-chain intelligence inside Theme Research",
    intent: "command",
    group: "Commands",
    target_tab: "theme-supply-chain",
    aliases: ["supply chain", "beneficiary stocks", "theme stocks", "stocks"],
  },
];

const OMNIBOX_SECTORS: OmniboxRegistryItem[] = [
  ["Semiconductors", "Sector Rotation", "Chipmakers, foundries, equipment, and memory", ["SEMICONDUCTOR", "SEMICONDUCTORS", "SOX", "CHIPS"]],
  ["Technology", "Sector Rotation", "Software, hardware, cloud, and platform leadership", ["TECH", "TECHNOLOGY", "XLK"]],
  ["Financials", "Sector Rotation", "Banks, brokers, payment rails, and insurance", ["FINANCIALS", "BANKS", "XLF"]],
  ["Energy", "Sector Rotation", "Oil, gas, services, and energy infrastructure", ["ENERGY", "OIL", "GAS", "XLE"]],
  ["Healthcare", "Sector Rotation", "Pharma, biotech, providers, and medtech", ["HEALTHCARE", "HEALTH CARE", "XLV", "BIOTECH"]],
  ["Utilities", "Sector Rotation", "Regulated power, grid demand, and defensive yield", ["UTILITIES", "UTILITY", "XLU"]],
  ["Industrials", "Sector Rotation", "Manufacturing, aerospace, logistics, and automation", ["INDUSTRIALS", "XLI"]],
].map(([sector, label, description, aliases]) => ({
  symbol: `SECTOR:${String(sector).toUpperCase().replace(/[^A-Z0-9]+/g, "-")}`,
  name: String(sector),
  exchange: String(label),
  type: "Sector",
  sector: String(sector),
  label: String(sector),
  description: String(description),
  intent: "sector" as OmniboxIntent,
  group: "Sectors" as OmniboxGroup,
  target_tab: "market-intel" as OmniboxTargetTab,
  aliases: aliases as string[],
}));

function compactSearchText(value: string): string {
  return value.trim().toUpperCase().replace(/[^A-Z0-9. ]+/g, " ").replace(/\s+/g, " ");
}

function stripIntentPrefix(value: string): string {
  return compactSearchText(value).replace(/^(THEME|SECTOR|COMMAND|OPEN|GO TO|SHOW)\s+/, "");
}

function resultHaystack(item: SearchResult): string {
  return compactSearchText([
    item.symbol,
    item.name,
    item.label,
    item.description,
    item.company,
    item.theme,
    item.sector,
    item.etf,
    item.command,
    item.type,
    item.exchange,
  ].filter(Boolean).join(" "));
}

function matchesOmniboxItem(item: OmniboxRegistryItem, query: string): boolean {
  const normalized = compactSearchText(query);
  const intentQuery = stripIntentPrefix(query);
  const haystack = resultHaystack(item);
  return haystack.includes(normalized)
    || haystack.includes(intentQuery)
    || item.aliases.some((alias) => compactSearchText(alias).includes(intentQuery) || intentQuery.includes(compactSearchText(alias)));
}

function actionForResult(item: SearchResult, query = ""): WorkspaceAction {
  const type = item.type.toLowerCase();
  const normalizedQuery = compactSearchText(query);
  const targetTab = item.target_tab ?? "stock-analysis";
  if (targetTab === "stock-analysis") {
    const ticker = (item.ticker ?? item.symbol).trim().toUpperCase();
    return {
      actionType: "open_stock",
      target_tab: "stock-analysis",
      focusTarget: "stock-workspace",
      openMode: "replace",
      contextPayload: { ticker, label: `Open ${ticker} Analysis` },
    };
  }
  if (type === "sector" || targetTab === "market-intel") {
    const sector = item.sector ?? item.label ?? item.name;
    return {
      actionType: type === "sector" ? "open_sector" : "open_module",
      target_tab: "market-intel",
      focusTarget: "theme-rotation",
      openMode: "replace",
      contextPayload: type === "sector" ? { sector, themeView: "rotation", label: `Open ${sector} Rotation` } : { themeView: "rotation", label: item.label ?? item.name },
    };
  }
  if (item.command === "open-theme-forecast") {
    return {
      actionType: "open_module",
      target_tab: "theme-forecast",
      focusTarget: "theme-forecast",
      openMode: "replace",
      contextPayload: { themeView: "forecast", label: item.label ?? item.name },
    };
  }
  if (item.command === "open-capital-rotation") {
    return {
      actionType: "open_module",
      target_tab: "market-intel",
      focusTarget: "theme-rotation",
      openMode: "replace",
      contextPayload: { themeView: "rotation", label: item.label ?? item.name },
    };
  }
  if (item.command === "open-supply-chain") {
    return {
      actionType: "open_module",
      target_tab: "theme-supply-chain",
      focusTarget: "theme-supply-chain",
      openMode: "replace",
      contextPayload: { themeView: "supply-chain", label: item.label ?? item.name },
    };
  }
  if (type === "theme" || targetTab === "theme-intelligence") {
    const theme = item.theme ?? item.label ?? item.name;
    return {
      actionType: type === "theme" ? "open_theme" : "open_module",
      target_tab: "theme-intelligence",
      focusTarget: type === "theme" ? "theme-detail" : "theme-workspace",
      openMode: "replace",
      contextPayload: type === "theme" ? { theme, themeView: "command", label: `Open ${theme}` } : { themeView: "command", label: item.label ?? item.name },
    };
  }
  if (targetTab === "theme-forecast") {
    return {
      actionType: "open_module",
      target_tab: "theme-forecast",
      focusTarget: "theme-forecast",
      openMode: "replace",
      contextPayload: { themeView: "forecast", label: item.label ?? item.name },
    };
  }
  if (targetTab === "alpha-quant") {
    const alphaView = normalizedQuery.includes("MOMENTUM") ? "momentum" : normalizedQuery.includes("FACTOR") ? "factors" : "top-alpha";
    return {
      actionType: "open_alpha",
      target_tab: "alpha-quant",
      focusTarget: alphaView === "momentum" ? "alpha-momentum" : "alpha-workspace",
      openMode: "replace",
      contextPayload: { alphaView, label: alphaView === "momentum" ? "Alpha Momentum" : item.label ?? item.name },
    };
  }
  if (targetTab === "portfolio") {
    const portfolioView = normalizedQuery.includes("WATCHLIST") ? "watchlist" : "overview";
    return {
      actionType: "open_portfolio",
      target_tab: "portfolio",
      focusTarget: "portfolio-watchlist",
      openMode: "replace",
      contextPayload: { portfolioView, label: portfolioView === "watchlist" ? "Portfolio Watchlist" : item.label ?? item.name },
    };
  }
  return {
    actionType: "open_module",
    target_tab: targetTab,
    focusTarget: targetTab,
    openMode: "replace",
    contextPayload: { label: item.label ?? item.name },
  };
}

function withWorkspaceAction(item: SearchResult, query = ""): SearchResult {
  const workspaceAction = actionForResult(item, query);
  return {
    ...item,
    actionType: workspaceAction.actionType,
    focusTarget: workspaceAction.focusTarget,
    contextPayload: workspaceAction.contextPayload,
    openMode: workspaceAction.openMode,
    workspaceAction,
  };
}

function enrichStockResult(item: SearchResult): SearchResult {
  const symbol = item.symbol.trim().toUpperCase();
  const isEtf = item.type.toUpperCase() === "ETF" || item.exchange.toUpperCase() === "ETF";
  return withWorkspaceAction({
    ...item,
    symbol,
    ticker: symbol,
    company: item.name,
    etf: isEtf ? symbol : item.etf,
    label: item.label ?? symbol,
    description: item.description ?? item.name,
    intent: "ticker",
    group: "Stocks",
    target_tab: "stock-analysis",
  });
}

function enrichUniversalResult(item: SearchResult): SearchResult {
  const type = item.type.toLowerCase();
  if (type === "theme") {
    return withWorkspaceAction({
      ...item,
      label: item.label ?? item.name.split("/")[0].trim(),
      theme: item.theme ?? item.name.split("/")[0].trim(),
      description: item.description ?? "Open theme intelligence",
      intent: "theme",
      group: "Themes",
      target_tab: "theme-intelligence",
    });
  }
  if (type === "sector") {
    return withWorkspaceAction({
      ...item,
      label: item.label ?? item.name.split("/")[0].trim(),
      sector: item.sector ?? item.name.split("/")[0].trim(),
      description: item.description ?? "Open sector rotation",
      intent: "sector",
      group: "Sectors",
      target_tab: "market-intel",
    });
  }
  return enrichStockResult(item);
}

function exactKnownTicker(query: string): SearchResult | undefined {
  const normalized = stripIntentPrefix(query);
  return POPULAR_SYMBOLS.find((item) => compactSearchText(item.symbol) === normalized);
}

function exactThemeMatch(query: string, registryThemes: ThemeRegistryEntry[] = []): SearchResult | undefined {
  const normalized = stripIntentPrefix(query);
  const entry = sortThemeRegistryEntries(registryThemes).find((item) => (
    compactSearchText(item.theme_name) === normalized
    || compactSearchText(item.theme_id) === normalized
  ));
  return entry ? buildRegistrySearchItems([entry])[0] : undefined;
}

export function resolveExactSearchResult(query: string, registryThemes: ThemeRegistryEntry[] = []): SearchResult | null {
  const knownTicker = exactKnownTicker(query);
  if (knownTicker) return enrichStockResult(knownTicker);
  const knownTheme = exactThemeMatch(query, registryThemes);
  return knownTheme ?? null;
}

export function classifySearchIntent(query: string, registryThemes: ThemeRegistryEntry[] = []): OmniboxIntent {
  const normalized = compactSearchText(query);
  if (!normalized) return "ticker";
  if (/^THEME\s+/.test(normalized)) return "theme";
  if (/^SECTOR\s+/.test(normalized)) return "sector";
  if (exactKnownTicker(query)) return "ticker";
  if (exactThemeMatch(query, registryThemes)) return "theme";
  if ([...OMNIBOX_COMMANDS, ...THEME_RESEARCH_COMMANDS].some((item) => matchesOmniboxItem(item, normalized))) return "command";
  if (registryThemes.some((item) => matchesRegistryTheme(item, normalized))) return "theme";
  if (OMNIBOX_SECTORS.some((item) => matchesOmniboxItem(item, normalized))) return "sector";
  const stripped = stripIntentPrefix(query);
  if (/^[A-Z.]{1,8}$/.test(stripped)) return "ticker";
  return "natural_language";
}

function mergeSearchResults(results: SearchResult[]): SearchResult[] {
  return results.reduce<SearchResult[]>((acc, item) => {
    const key = item.id ?? `${item.group ?? item.type}:${item.symbol}`;
    if (!acc.some((existing) => (existing.id ?? `${existing.group ?? existing.type}:${existing.symbol}`) === key)) acc.push(item);
    return acc;
  }, []);
}

function searchResultRank(item: SearchResult, query: string): number {
  const exactTickerPriority = 0;
  const tickerPrefixPriority = 10;
  const exactCompanyPriority = 20;
  const companyPrefixPriority = 30;
  const themeSectorPriority = 40;
  const commandPriority = 60;
  const fallbackPriority = 80;
  const normalizedQuery = stripIntentPrefix(query);
  const symbol = compactSearchText(item.ticker ?? item.symbol);
  const company = compactSearchText(item.company ?? item.name);
  const group = item.group ?? (item.type.toLowerCase() === "theme" ? "Themes" : item.type.toLowerCase() === "sector" ? "Sectors" : item.type.toLowerCase() === "command" ? "Commands" : "Stocks");

  if (symbol === normalizedQuery) return exactTickerPriority;
  if (symbol.startsWith(normalizedQuery)) return tickerPrefixPriority;
  if (company === normalizedQuery) return exactCompanyPriority;
  if (company.startsWith(normalizedQuery)) return companyPrefixPriority;
  if (group === "Themes" || group === "Sectors") return themeSectorPriority;
  if (group === "Commands") return commandPriority;
  return fallbackPriority;
}

function rankSearchResults(results: SearchResult[], query: string): SearchResult[] {
  return [...results].sort((left, right) => {
    const leftRank = searchResultRank(left, query);
    const rightRank = searchResultRank(right, query);
    if (leftRank !== rightRank) return leftRank - rightRank;
    return (left.ticker ?? left.symbol).localeCompare(right.ticker ?? right.symbol);
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function xhrRequest(input: string, init?: RequestInit): Promise<Response> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(init?.method ?? "GET", input, true);
    xhr.timeout = REQUEST_TIMEOUT_MS;
    if (init?.headers) {
      new Headers(init.headers).forEach((value, key) => xhr.setRequestHeader(key, value));
    }
    xhr.onload = () => {
      resolve(new Response(xhr.responseText, {
        status: xhr.status,
        statusText: xhr.statusText,
        headers: { "content-type": xhr.getResponseHeader("content-type") ?? "application/json" },
      }));
    };
    xhr.onerror = () => reject(new Error("Network request failed"));
    xhr.ontimeout = () => reject(new Error("Network request timed out"));
    xhr.onabort = () => reject(new Error("Network request aborted"));
    xhr.send(typeof init?.body === "string" ? init.body : null);
  });
}

async function browserRequest(input: string, init?: RequestInit): Promise<Response> {
  const fetcher = typeof window !== "undefined" && typeof window.fetch === "function" ? window.fetch.bind(window) : null;
  if (fetcher) return fetcher(input, init);
  return xhrRequest(input, init);
}

async function fetchWithRetry(input: string, init?: RequestInit): Promise<Response> {
  let lastError: unknown;
  const deadline = Date.now() + REQUEST_TIMEOUT_MS;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    if (init?.signal?.aborted) {
      throw new DOMException("Request aborted", "AbortError");
    }
    const controller = new AbortController();
    const abortFromCaller = () => controller.abort();
    init?.signal?.addEventListener("abort", abortFromCaller, { once: true });
    const timeout = window.setTimeout(() => controller.abort(), remaining);
    try {
      return await browserRequest(input, {
        ...init,
        signal: controller.signal,
      });
    } catch (error) {
      lastError = error;
      if (controller.signal.aborted && init?.signal?.aborted) {
        throw error instanceof Error ? error : new DOMException("Request aborted", "AbortError");
      }
      if (attempt < MAX_ATTEMPTS && Date.now() + 750 * attempt < deadline) await sleep(750 * attempt);
    } finally {
      window.clearTimeout(timeout);
      init?.signal?.removeEventListener("abort", abortFromCaller);
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Network request failed");
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasNonFiniteNumber(value: unknown): boolean {
  if (typeof value === "number") return !Number.isFinite(value);
  if (Array.isArray(value)) return value.some(hasNonFiniteNumber);
  if (isRecord(value)) return Object.values(value).some(hasNonFiniteNumber);
  return false;
}

function hasFallbackMarker(value: unknown): boolean {
  if (Array.isArray(value)) return value.some(hasFallbackMarker);
  if (!isRecord(value)) return false;
  if (value.fallback === true) return true;
  if (isRecord(value.qlib_engine) && value.qlib_engine.mode === "fallback") return true;
  return Object.values(value).some(hasFallbackMarker);
}

function isCacheableLocalPayload(key: string, value: unknown): boolean {
  if (hasNonFiniteNumber(value) || hasFallbackMarker(value)) return false;
  if (key.startsWith("miji:stock:")) {
    if (!isRecord(value)) return false;
    return validPrice(value.price) !== null || (isRecord(value.quote) && validPrice(value.quote.price) !== null);
  }
  return true;
}

function getLocalStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage ?? null;
  } catch {
    return null;
  }
}

function removeLocalCacheItem(storage: Storage | null, key: string): void {
  try {
    storage?.removeItem(key);
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts.
  }
}

function readLocalCache<T>(key: string): T | null {
  const storage = getLocalStorage();
  if (!storage) return null;
  try {
    const raw = storage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!isRecord(parsed) || parsed.schema_version !== CLIENT_CACHE_SCHEMA_VERSION || !("data" in parsed)) {
      removeLocalCacheItem(storage, key);
      return null;
    }
    const data = (parsed as unknown as LocalCacheEnvelope<T>).data;
    if (!isCacheableLocalPayload(key, data)) {
      removeLocalCacheItem(storage, key);
      return null;
    }
    if (key.startsWith("miji:stock:") && isRecord(data)) {
      const cachedAt = Date.parse(String((parsed as unknown as LocalCacheEnvelope<T>).cached_at || ""));
      const cacheAgeSeconds = Number.isFinite(cachedAt) ? Math.max(0, Math.floor((Date.now() - cachedAt) / 1000)) : null;
      if (cacheAgeSeconds === null || cacheAgeSeconds > 60) {
        const quote = isRecord(data.quote) ? data.quote : {};
        return {
          ...data,
          quote_status: "stale",
          canonicalQuoteStatus: "stale",
          source: "local_cache",
          cache_age_seconds: cacheAgeSeconds,
          is_stale: true,
          quote: {
            ...quote,
            status: "stale",
            source: "local_cache",
            cache_age_seconds: cacheAgeSeconds,
            is_stale: true,
          },
        } as T;
      }
    }
    return data;
  } catch {
    removeLocalCacheItem(storage, key);
    return null;
  }
}

function writeLocalCache<T>(key: string, value: T): void {
  const storage = getLocalStorage();
  if (!storage) return;
  try {
    if (!isCacheableLocalPayload(key, value)) return;
    const envelope: LocalCacheEnvelope<T> = {
      schema_version: CLIENT_CACHE_SCHEMA_VERSION,
      cached_at: new Date().toISOString(),
      data: value,
    };
    storage.setItem(key, JSON.stringify(envelope));
  } catch {
    // Local cache is best effort and should never block the terminal.
  }
}

function clearLocalCache(key: string): void {
  removeLocalCacheItem(getLocalStorage(), key);
}

function unwrapStockPayload(payload: unknown): StockAnalysis {
  if (!isRecord(payload)) return payload as StockAnalysis;
  for (const key of ["stock", "data", "result", "analysis"]) {
    const value = payload[key];
    if (isRecord(value) && (value.ticker || value.quote || value.price || value.currentPrice || value.regularMarketPrice)) {
      return value as unknown as StockAnalysis;
    }
  }
  return payload as unknown as StockAnalysis;
}

function hasCanonicalPrice(value: unknown, symbol: string): boolean {
  return normalizeCanonicalQuote(isRecord(value) ? value : null, symbol).canonicalPrice !== null;
}

async function fetchCachedJson<T>(cacheKey: string, url: string, fallback: T): Promise<T> {
  const cached = readLocalCache<T>(cacheKey);
  if (cached) {
    fetchWithRetry(url, { cache: "no-store" })
      .then((response) => readJson<T>(response))
      .then((data) => writeLocalCache(cacheKey, data))
      .catch(() => {});
    return cached;
  }
  try {
    const response = await fetchWithRetry(url, { cache: "no-store" });
    const data = await readJson<T>(response);
    writeLocalCache(cacheKey, data);
    return data;
  } catch {
    if (cached) return cached;
    return fallback;
  }
}

async function fetchFreshJson<T>(cacheKey: string, url: string, fallback: T): Promise<T> {
  try {
    const response = await fetchWithRetry(url, { cache: "no-store" });
    const data = await readJson<T>(response);
    writeLocalCache(cacheKey, data);
    return data;
  } catch {
    return readLocalCache<T>(cacheKey) ?? fallback;
  }
}

function coerceNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value.replace(/[$,%\s,]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function validNumber(value: unknown): number | null {
  return coerceNumber(value);
}

function validPrice(value: unknown): number | null {
  const number = validNumber(value);
  return number !== null && number > 0 ? number : null;
}

function firstValidNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const number = validNumber(value);
    if (number !== null) return number;
  }
  return null;
}

function firstValidPrice(...values: unknown[]): number | null {
  for (const value of values) {
    const price = validPrice(value);
    if (price !== null) return price;
  }
  return null;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function quoteRecord(data: Partial<StockAnalysis> | Record<string, unknown> | null | undefined): Record<string, unknown> {
  return isRecord(data?.quote) ? data.quote : {};
}

function normalizeCanonicalQuote(data: Partial<StockAnalysis> | Record<string, unknown> | null | undefined, symbol: string): CanonicalQuoteFields {
  const source = (isRecord(data) ? data : {}) as Record<string, unknown>;
  const quote = quoteRecord(source);
  const canonicalPrice = firstValidPrice(
    source.price,
    quote.price,
    source.currentPrice,
    source.regularMarketPrice,
    quote.currentPrice,
    quote.regularMarketPrice,
  );
  const canonicalChange = firstValidNumber(
    source.change,
    quote.change,
    source.regularMarketChange,
    quote.regularMarketChange,
  );
  const canonicalChangePercent = firstValidNumber(
    source.change_percent,
    source.changePercent,
    quote.change_percent,
    quote.changePercent,
    source.regularMarketChangePercent,
    quote.regularMarketChangePercent,
  );
  const canonicalMarketCap = firstValidPrice(
    source.market_cap,
    source.marketCap,
    quote.market_cap,
    quote.marketCap,
  );
  const status = firstString(source.quote_status, quote.status, quote.quoteStatus);
  const canonicalSector = firstString(source.sector, quote.sector) ?? "US Equity";
  return {
    canonicalPrice,
    canonicalChange,
    canonicalChangePercent,
    canonicalMarketCap,
    canonicalQuoteStatus: status ?? "unavailable",
    canonicalSector,
  };
}

function normalizeQuote(data: Partial<StockAnalysis> | Record<string, unknown> | null | undefined, symbol: string): StockQuote {
  const raw = quoteRecord(data);
  const source = (isRecord(data) ? data : {}) as Record<string, unknown>;
  const canonical = normalizeCanonicalQuote(data, symbol);
  return {
    ticker: (firstString(raw.ticker, isRecord(data) ? data.ticker : null) ?? symbol).toUpperCase(),
    price: canonical.canonicalPrice,
    change: canonical.canonicalChange,
    change_percent: canonical.canonicalChangePercent,
    previous_close: firstValidPrice(raw.previous_close, raw.previousClose),
    market_cap: canonical.canonicalMarketCap,
    pe_ratio: validNumber(raw.pe_ratio),
    ps_ratio: validNumber(raw.ps_ratio),
    currency: firstString(raw.currency) ?? "USD",
    status: canonical.canonicalQuoteStatus,
    source: firstString(raw.source, source.source) ?? undefined,
    fetched_at: firstString(raw.fetched_at, source.fetched_at),
    updated_at: firstString(raw.updated_at, source.updated_at),
    expires_at: firstString(raw.expires_at, source.expires_at),
    cache_age_seconds: firstValidNumber(raw.cache_age_seconds, source.cache_age_seconds),
    is_stale: raw.is_stale === true || source.is_stale === true || ["stale", "fallback", "unavailable"].includes(canonical.canonicalQuoteStatus),
  };
}

function fallbackStock(symbol: string): StockAnalysis {
  const quote = normalizeQuote(null, symbol);
  return {
    ticker: symbol,
    company_name: symbol,
    price: null,
    change: null,
    change_percent: null,
    market_cap: null,
    canonicalPrice: null,
    canonicalChange: null,
    canonicalChangePercent: null,
    canonicalMarketCap: null,
    canonicalQuoteStatus: "unavailable",
    canonicalSector: "US Equity",
    sector: "US Equity",
    quote_status: "unavailable",
    quote,
    bubble_analysis_data: {
      revenue: null,
      net_income: null,
      gross_margin: null,
      operating_cash_flow: null,
      free_cash_flow: null,
      total_assets: null,
      total_liabilities: null,
      debt_ratio: null,
      pe_ratio: null,
      ps_ratio: null,
      bubble_index: null,
      classification: "Calibrating",
      valuation_heat: undefined,
      revenue_divergence: undefined,
      fcf_quality: undefined,
      dilution_risk: undefined,
      distribution_signal: undefined,
      retail_speculation: undefined,
      accrual_ratio: undefined,
      net_income_quality: undefined,
      confidence_score: undefined,
      confidence_label: "Warming",
      ai_summary: "Bubble intelligence is unavailable until central enrichment returns live fundamentals.",
    },
    analyst_targets: {
      available: false,
      high: null,
      average: null,
      low: null,
      average_target: null,
      implied_upside: null,
      buy: null,
      hold: null,
      sell: null,
    },
    analyst_consensus: {
      available: false,
      average_target: null,
      implied_upside: null,
      buy: null,
      hold: null,
      sell: null,
    },
    hmm_prediction: {
      available: false,
      predicted_trend: "Calibrating model...",
      bull_probability: null,
      bear_probability: null,
      regime_state: "Awaiting regime confirmation...",
      confidence: null,
      message: "Using fallback market regime...",
    },
    news: [],
  };
}

function normalizeStockAnalysis(data: StockAnalysis, symbol: string): StockAnalysis {
  const fallback = fallbackStock(symbol);
  const canonical = normalizeCanonicalQuote(data, symbol);
  const quote = normalizeQuote(data, symbol);
  const company = data?.company_name && data.company_name !== "Unknown" ? data.company_name : fallback.company_name;
  const sector = canonical.canonicalSector && canonical.canonicalSector !== "Unknown" ? canonical.canonicalSector : fallback.sector;
  const hmm = data?.hmm_prediction ?? fallback.hmm_prediction;
  const trend = typeof hmm?.predicted_trend === "string" ? hmm.predicted_trend : "";
  const hmmAvailable = hmm?.available !== false && trend !== "Neutral" && !trend.toLowerCase().includes("calibrating") && validNumber(hmm?.confidence) !== null && validNumber(hmm?.bull_probability) !== null;
  return {
    ...fallback,
    ...data,
    ticker: (data?.ticker ?? symbol).trim().toUpperCase(),
    company_name: company,
    sector,
    price: canonical.canonicalPrice,
    change: canonical.canonicalChange,
    change_percent: canonical.canonicalChangePercent,
    market_cap: canonical.canonicalMarketCap,
    canonicalPrice: canonical.canonicalPrice,
    canonicalChange: canonical.canonicalChange,
    canonicalChangePercent: canonical.canonicalChangePercent,
    canonicalMarketCap: canonical.canonicalMarketCap,
    canonicalQuoteStatus: canonical.canonicalQuoteStatus,
    canonicalSector: sector,
    quote_status: canonical.canonicalQuoteStatus,
    source: quote.source,
    fetched_at: quote.fetched_at,
    updated_at: quote.updated_at,
    expires_at: quote.expires_at,
    cache_age_seconds: quote.cache_age_seconds,
    is_stale: quote.is_stale,
    quote,
    hmm_prediction: {
      ...fallback.hmm_prediction,
      ...hmm,
      available: hmmAvailable,
      predicted_trend: hmmAvailable ? hmm.predicted_trend : "Calibrating model...",
      bull_probability: hmmAvailable ? hmm.bull_probability : null,
      bear_probability: hmmAvailable ? hmm.bear_probability : null,
      confidence: hmmAvailable ? hmm.confidence : null,
      regime_state: hmmAvailable ? hmm.regime_state : "Awaiting regime confirmation...",
      message: hmmAvailable ? hmm.message : "Using fallback market regime...",
    },
  };
}

function fallbackAlpha(universe: string): AlphaQuantResponse {
  return {
    generated_at: new Date().toISOString(),
    universe: universe.toUpperCase(),
    qlib_engine: { available: false, mode: "fallback", provider: "Miji Quant", factor_set: "Cached Alpha Fallback" },
    market_regime: { name: "Calibrating", confidence: null },
    factor_importance: {},
    top_alpha: [],
    recommendations: [],
    summary: "Live engine delayed. Showing cached institutional intelligence.",
  };
}

const FALLBACK_SECTORS: SectorRotation[] = [
  "Technology", "Energy", "Healthcare", "Financials", "Industrials", "Utilities",
  "Consumer Discretionary", "Consumer Staples", "Materials", "Real Estate", "Communication Services",
].map((sector) => ({
  sector,
  score: null,
  relative_strength: null,
  flow: null,
  companies: [],
}));

const EMPTY_ROTATION_SNAPSHOT: RotationSnapshotResponse = {
  status: "unavailable",
  source: "unavailable",
  updated_at: null,
  market_regime: "unavailable",
  risk_appetite: "unavailable",
  volatility_state: "unavailable",
  rotation_bias: "unavailable",
  leaders: [],
  laggards: [],
  sector_ranking: FALLBACK_SECTORS,
  selected_sector: null,
  diagnostics: [],
  theme_links: [],
  data_quality: {
    available_sectors: 0,
    unavailable_sectors: FALLBACK_SECTORS.length,
    total_sectors: FALLBACK_SECTORS.length,
    coverage_ratio: 0,
  },
};

function fallbackThemeStocks(theme: string): ThemeStocksResponse {
  const key = theme.trim().toUpperCase().replace(/-/g, " ");
  return {
    generated_at: new Date().toISOString(),
    theme,
    theme_id: key.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
    related_stocks: [],
    top_alpha_stocks: [],
    summary: "Theme stock universe calibrating.",
    fallback: true,
  };
}

function fallbackThemeTop(): ThemeTopResponse {
  return {
    generated_at: new Date().toISOString(),
    cross_asset_regime: {
      risk_on_off: "Calibrating",
      risk_on_score: undefined,
      liquidity_regime: "Calibrating",
      liquidity_score: undefined,
      volatility_regime: "Calibrating",
      volatility_score: undefined,
      inflation_regime: "Calibrating",
      inflation_score: undefined,
      AI_capex_regime: "Calibrating",
      AI_capex_score: undefined,
    },
    themes: [],
    summary: "Using latest cached institutional intelligence while live theme data warms up.",
  };
}

function normalizeAlphaQuantResponse(data: AlphaQuantResponse): AlphaQuantResponse {
  const normalizeRow = (row: AlphaQuantResponse["top_alpha"][number]) => {
    const normalized = normalizeAlphaQuantRow(row);
    const quote = normalizeQuote(row as unknown as Partial<StockAnalysis>, row.ticker);
    return {
      ...normalized,
      price: quote.price,
      change: quote.change,
      change_percent: quote.change_percent,
      quote_status: quote.status,
    };
  };
  return {
    ...data,
    top_alpha: (data.top_alpha ?? []).map(normalizeRow),
    recommendations: (data.recommendations ?? []).map(normalizeRow),
  };
}

function normalizeThemeLeader<T extends { ticker: string; price?: number | null; change?: number | null; change_percent?: number | null; quote_status?: string; quote?: StockQuote }>(leader: T): T {
  const quote = normalizeQuote(leader as unknown as Partial<StockAnalysis>, leader.ticker);
  return {
    ...leader,
    price: quote.price,
    change: quote.change,
    change_percent: quote.change_percent,
    quote_status: quote.status,
    quote,
  };
}

function normalizeThemeStocksResponse<T extends ThemeStocksResponse | ThemeDetailResponse>(data: T): T {
  const related = (data.related_stocks ?? []).map(normalizeThemeLeader);
  const top = (data.top_alpha_stocks ?? []).map(normalizeThemeLeader);
  const supply = "supply_chain" in data && data.supply_chain
    ? Object.fromEntries(Object.entries(data.supply_chain).map(([role, leaders]) => [role, leaders.map(normalizeThemeLeader)]))
    : undefined;
  return {
    ...data,
    related_stocks: related,
    top_alpha_stocks: top,
    ...(supply ? { supply_chain: supply } : {}),
  };
}

function pathNumber(source: unknown, path: string): number | null {
  let current: unknown = source;
  for (const segment of path.split(".")) {
    if (!isRecord(current)) return null;
    current = current[segment];
  }
  return validNumber(current);
}

function firstPathNumber(source: unknown, ...paths: string[]): number | null {
  for (const path of paths) {
    const value = pathNumber(source, path);
    if (value !== null) return value;
  }
  return null;
}

function normalizeNarrativeIntelligence<T extends Partial<NarrativeIntelligence>>(item: T): T {
  const score = firstPathNumber(
    item,
    "score",
    "narrative_strength",
    "ranking_score",
    "leadership_score",
    "institutional_alignment",
    "acceleration_velocity",
    "participation_breadth",
  );
  const flow = firstPathNumber(item, "flow", "institutional_alignment", "theme_capital_flow_score", "volume_participation");
  const relativeStrength = firstPathNumber(item, "relative_strength", "relative_strength_spy", "relative_strength_qqq", "momentum_60d", "momentum_20d");
  const leadership = firstPathNumber(item, "leadership", "leadership_score", "institutional_alignment", "narrative_strength", "score");
  const momentum = firstPathNumber(item, "momentum", "momentum_strength", "momentum_60d", "momentum_20d", "narrative_strength", "score");
  const participation = firstPathNumber(item, "participation", "participation_breadth", "breadth_participation", "volume_participation");
  const acceleration = firstPathNumber(item, "acceleration", "acceleration_velocity", "narrative_acceleration", "momentum_20d");
  return {
    ...item,
    score,
    flow,
    relative_strength: relativeStrength,
    narrative_strength: firstPathNumber(item, "narrative_strength", "score", "ranking_score", "leadership_score", "institutional_alignment") ?? item.narrative_strength ?? null,
    acceleration_velocity: firstPathNumber(item, "acceleration_velocity", "acceleration", "narrative_acceleration", "momentum_20d") ?? item.acceleration_velocity ?? null,
    participation_breadth: firstPathNumber(item, "participation_breadth", "participation", "breadth_participation", "volume_participation") ?? item.participation_breadth ?? null,
    institutional_alignment: firstPathNumber(item, "institutional_alignment", "leadership", "flow", "theme_capital_flow_score") ?? item.institutional_alignment ?? null,
    leadership,
    momentum,
    participation,
    acceleration,
  };
}

function normalizeThemeScore<T extends Partial<ThemeScore>>(theme: T): T {
  const narrative = isRecord(theme.narrative_intelligence)
    ? normalizeNarrativeIntelligence(theme.narrative_intelligence as Partial<NarrativeIntelligence>)
    : theme.narrative_intelligence;
  const score = firstPathNumber(
    theme,
    "score",
    "theme_strength_score",
    "ranking_score",
    "universe_ranking.ranking_score",
    "leadership_score",
    "leadership_intelligence.leadership_score",
    "narrative_intelligence.score",
    "narrative_intelligence.narrative_strength",
    "narrative_strength",
    "acceleration_velocity",
    "momentum_strength",
    "relative_strength_spy",
    "relative_strength_vs_spy",
  );
  const flow = firstPathNumber(
    theme,
    "flow",
    "theme_capital_flow_score",
    "institutional_alignment",
    "narrative_intelligence.institutional_alignment",
    "volume_participation",
    "smart_money_accumulation",
    "institutional_accumulation",
  );
  const relativeStrength = firstPathNumber(theme, "relative_strength", "relative_strength_spy", "relative_strength_vs_spy", "relative_strength_qqq", "etf_relative_strength", "relative_momentum");
  const leadership = firstPathNumber(theme, "leadership", "leadership_score", "leadership_intelligence.leadership_score", "sector_leadership", "score", "theme_strength_score");
  const momentum = firstPathNumber(theme, "momentum", "momentum_strength", "momentum_60d", "momentum_20d", "relative_momentum", "narrative_strength");
  const participation = firstPathNumber(theme, "participation", "participation_breadth", "participation_score", "breadth_participation", "volume_expansion");
  const acceleration = firstPathNumber(theme, "acceleration", "acceleration_velocity", "acceleration_score", "narrative_acceleration", "emerging_score");
  return {
    ...theme,
    score,
    flow,
    relative_strength: relativeStrength,
    relative_strength_vs_spy: relativeStrength ?? theme.relative_strength_vs_spy ?? null,
    theme_strength_score: firstPathNumber(theme, "theme_strength_score", "score", "ranking_score", "leadership_score", "narrative_strength") ?? theme.theme_strength_score ?? null,
    theme_capital_flow_score: flow ?? theme.theme_capital_flow_score ?? null,
    leadership,
    momentum,
    participation,
    acceleration,
    ...(narrative ? { narrative_intelligence: narrative as ThemeScore["narrative_intelligence"] } : {}),
  };
}

function normalizeSectorRotationRow(sector: SectorRotation): SectorRotation {
  const narrative = isRecord(sector.narrative_intelligence)
    ? normalizeNarrativeIntelligence(sector.narrative_intelligence)
    : sector.narrative_intelligence;
  const score = firstPathNumber(
    sector,
    "score",
    "sector_score",
    "sector_strength",
    "ranking_score",
    "universe_ranking.ranking_score",
    "leadership_score",
    "leadership_intelligence.leadership_score",
    "narrative_intelligence.score",
    "narrative_intelligence.narrative_strength",
    "momentum_20d",
    "momentum_60d",
    "relative_strength_spy",
  );
  const flow = firstPathNumber(sector, "flow", "capital_flow", "institutional_alignment", "volume_participation", "narrative_intelligence.institutional_alignment");
  const relativeStrength = firstPathNumber(sector, "relative_strength", "relative_strength_spy", "relative_strength_qqq", "momentum_60d", "momentum_20d");
  const leadership = firstPathNumber(sector, "leadership", "leadership_score", "leadership_intelligence.leadership_score", "sector_strength", "score", "ranking_score");
  const momentum = firstPathNumber(sector, "momentum", "momentum_strength", "momentum_60d", "momentum_20d", "relative_strength_spy");
  const participation = firstPathNumber(sector, "participation", "participation_breadth", "participation_strength", "leadership_intelligence.participation_strength", "volume_participation");
  const acceleration = firstPathNumber(sector, "acceleration", "acceleration_velocity", "narrative_intelligence.acceleration_velocity", "momentum_20d");
  return {
    ...sector,
    score,
    sector_score: firstPathNumber(sector, "sector_score", "sector_strength", "score", "ranking_score") ?? sector.sector_score ?? null,
    flow,
    relative_strength: relativeStrength,
    leadership,
    momentum,
    participation,
    acceleration,
    ...(narrative ? { narrative_intelligence: narrative } : {}),
  };
}

function unwrapSectorRow(row: Record<string, unknown>): Record<string, unknown> {
  const merged: Record<string, unknown> = { ...row };
  for (const key of ["sector_rotation", "sectorRotation", "rotation", "item", "data", "metrics"]) {
    const value = row[key];
    if (isRecord(value) && (value.sector || value.score || value.relative_strength || value.flow)) {
      for (const [nestedKey, nestedValue] of Object.entries(value)) {
        if (nestedValue !== null && nestedValue !== undefined && nestedValue !== "") {
          merged[nestedKey] = nestedValue;
        }
      }
    }
  }
  return merged;
}

function sectorRowsFromPayload(data: unknown): unknown[] {
  if (Array.isArray(data)) return data;
  if (!isRecord(data)) return [];
  for (const key of ["sector_ranking", "sectors", "items", "data", "results", "rows", "sector_rotation", "sectorRotation", "rotation"]) {
    const value = data[key];
    if (Array.isArray(value)) return value;
    if (isRecord(value)) {
      const nested = sectorRowsFromPayload(value);
      if (nested.length > 0) return nested;
    }
  }
  return [];
}

function firstRecordNumber(source: Record<string, unknown>, paths: string[]): number | undefined {
  for (const path of paths) {
    const value = pathNumber(source, path);
    if (value !== null) return value;
  }
  return undefined;
}

function firstRecordString(source: Record<string, unknown>, paths: string[]): string | undefined {
  for (const path of paths) {
    let current: unknown = source;
    for (const segment of path.split(".")) {
      if (!isRecord(current)) {
        current = undefined;
        break;
      }
      current = current[segment];
    }
    if (typeof current === "string" && current.trim()) return current.trim();
  }
  return undefined;
}

function toFiniteNumber(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined;
  if (typeof v === "string" && v.trim() === "") return undefined;
  if (typeof v !== "number" && typeof v !== "string") return undefined;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : undefined;
}

function normalizeSectorRotationResponse(data: unknown): SectorRotation[] {
  const rows = sectorRowsFromPayload(data);
  return rows
    .filter(isRecord)
    .map((row) => {
      const raw = unwrapSectorRow(row);
      const normalized = normalizeSectorRotationRow(raw as unknown as SectorRotation);
      const normalizedRow = {
        ...normalized,
        sector: firstRecordString(raw, ["sector", "name", "sector_name"]) ?? normalized.sector,
        score: firstRecordNumber(raw, [
          "score",
          "sector_score",
          "sector_strength",
          "ranking_score",
          "universe_ranking.ranking_score",
          "leadership_score",
          "leadership_intelligence.leadership_score",
          "narrative_intelligence.score",
          "narrative_intelligence.narrative_strength",
          "data.score",
          "metrics.score",
        ]),
        relative_strength: firstRecordNumber(raw, [
          "relative_strength",
          "relative_strength_spy",
          "relative_strength_qqq",
          "rs",
          "sector_leadership",
          "universe_ranking.sector_leadership",
          "momentum_60d",
          "momentum_20d",
          "data.relative_strength",
          "metrics.relative_strength",
        ]),
        flow: firstRecordNumber(raw, [
          "flow",
          "volume_participation",
          "capital_flow",
          "institutional_alignment",
          "universe_ranking.institutional_alignment",
          "volume_participation",
          "narrative_intelligence.institutional_alignment",
          "data.flow",
          "metrics.flow",
        ]),
        rotation_state: firstRecordString(raw, [
          "rotation_state",
          "rotationState",
          "leadership_state",
          "market_classification",
          "narrative_state",
          "universe_ranking.market_classification",
          "state",
          "status",
        ]) ?? normalized.rotation_state,
        leadership: firstRecordNumber(raw, ["leadership", "leadership_score", "leadership_intelligence.leadership_score", "sector_strength", "score", "ranking_score"]),
        momentum: firstRecordNumber(raw, ["momentum", "momentum_strength", "momentum_60d", "momentum_20d", "relative_strength_spy"]),
        participation: firstRecordNumber(raw, ["participation", "participation_breadth", "participation_strength", "leadership_intelligence.participation_strength", "volume_participation"]),
        acceleration: firstRecordNumber(raw, ["acceleration", "acceleration_velocity", "narrative_intelligence.acceleration_velocity", "momentum_20d"]),
        confidence_score: firstRecordNumber(raw, ["confidence_score", "confidence", "leadership_intelligence.confidence"]),
        status: firstRecordString(raw, ["status", "lifecycle_state"]) ?? normalized.status,
        trend: firstRecordString(raw, ["trend", "momentum_direction"]) ?? normalized.trend,
        evidence_source: firstRecordString(raw, ["evidence_source", "source"]) ?? normalized.evidence_source,
        updated_at: firstRecordString(raw, ["updated_at"]) ?? normalized.updated_at,
        linked_themes: Array.isArray(raw.linked_themes) ? raw.linked_themes.filter((item): item is string => typeof item === "string") : normalized.linked_themes ?? [],
        companies: Array.isArray(raw.companies) ? raw.companies as SectorRotation["companies"] : normalized.companies ?? [],
        rotation_score: firstRecordNumber(raw, ["rotation_score"]),
        rotation_momentum: firstRecordNumber(raw, ["rotation_momentum"]),
        rotation_relative_strength: firstRecordNumber(raw, ["rotation_relative_strength"]),
        rotation_flow_quality: firstRecordNumber(raw, ["rotation_flow_quality"]),
        rotation_confidence: firstRecordNumber(raw, ["rotation_confidence"]),
      };
      return normalizedRow;
    })
    .filter((row) => row.sector);
}

function rotationStatus(value: unknown): RotationStatus {
  return value === "live" || value === "cached" || value === "stale" || value === "partial"
    ? value
    : "unavailable";
}

export function normalizeRotationSnapshot(data: unknown): RotationSnapshotResponse {
  const source = isRecord(data) ? data : {};
  const sectorRanking = normalizeSectorRotationResponse(data);
  const leaders = normalizeSectorRotationResponse(source.leaders);
  const laggards = normalizeSectorRotationResponse(source.laggards);
  const status = rotationStatus(source.status);
  const quality = isRecord(source.data_quality) ? source.data_quality : {};
  const selected = isRecord(source.selected_sector) ? source.selected_sector : null;
  const normalizedRanking = sectorRanking.length > 0 ? sectorRanking : FALLBACK_SECTORS.map(normalizeSectorRotationRow);
  return {
    status,
    source: typeof source.source === "string" ? source.source : status === "unavailable" ? "unavailable" : "unknown",
    updated_at: typeof source.updated_at === "string" ? source.updated_at : null,
    market_regime: typeof source.market_regime === "string" ? source.market_regime : "unavailable",
    risk_appetite: typeof source.risk_appetite === "string" ? source.risk_appetite : "unavailable",
    volatility_state: typeof source.volatility_state === "string" ? source.volatility_state : "unavailable",
    rotation_bias: typeof source.rotation_bias === "string" ? source.rotation_bias : "unavailable",
    leaders: leaders.length > 0 ? leaders : normalizedRanking.filter((row) => row.score !== null && row.score !== undefined).slice(0, 5),
    laggards,
    sector_ranking: normalizedRanking,
    selected_sector: selected ? {
      sector: String(selected.sector ?? ""),
      sector_id: String(selected.sector_id ?? ""),
      leadership: validNumber(selected.leadership),
      momentum: validNumber(selected.momentum),
      flow: validNumber(selected.flow),
      related_themes: stringArray(selected.related_themes),
      risk_overlay: validNumber(selected.risk_overlay),
      updated_at: typeof selected.updated_at === "string" ? selected.updated_at : null,
      status: rotationStatus(selected.status),
      rotation_score: validNumber(selected.rotation_score),
      rotation_momentum: validNumber(selected.rotation_momentum),
      rotation_relative_strength: validNumber(selected.rotation_relative_strength),
      rotation_flow_quality: validNumber(selected.rotation_flow_quality),
      rotation_confidence: validNumber(selected.rotation_confidence),
    } : null,
    diagnostics: Array.isArray(source.diagnostics)
      ? source.diagnostics.filter(isRecord).map((row) => ({
        id: String(row.id ?? ""),
        label: String(row.label ?? ""),
        value: typeof row.value === "string" || typeof row.value === "number" ? row.value : null,
        status: rotationStatus(row.status),
      })).filter((row) => row.id)
      : [],
    theme_links: Array.isArray(source.theme_links) ? source.theme_links.filter(isRecord) : [],
    data_quality: {
      available_sectors: validNumber(quality.available_sectors) ?? normalizedRanking.filter((row) => row.score !== null && row.score !== undefined).length,
      unavailable_sectors: validNumber(quality.unavailable_sectors) ?? undefined,
      stale_sectors: validNumber(quality.stale_sectors) ?? undefined,
      total_sectors: validNumber(quality.total_sectors) ?? normalizedRanking.length,
      benchmark_available: typeof quality.benchmark_available === "boolean" ? quality.benchmark_available : undefined,
      coverage_ratio: validNumber(quality.coverage_ratio) ?? undefined,
      underlying_status: typeof quality.underlying_status === "string" ? quality.underlying_status : undefined,
    },
  };
}

function normalizeAlphaQuantRow(row: AlphaQuantRow): AlphaQuantRow {
  const score = firstPathNumber(row, "score", "ranking_score", "universe_ranking.ranking_score", "alpha_score", "theme_strength", "momentum_20d", "relative_strength_spy");
  const flow = firstPathNumber(row, "flow", "theme_capital_flow", "volume_participation", "smart_money");
  const relativeStrength = firstPathNumber(row, "relative_strength", "relative_strength_spy", "relative_strength_qqq", "sector_alignment", "theme_alignment");
  const leadership = firstPathNumber(row, "leadership", "ranking_score", "universe_ranking.ranking_score", "alpha_score", "sector_alignment", "theme_alignment", "theme_strength");
  const momentum = firstPathNumber(row, "momentum", "momentum_60d", "momentum_20d", "growth", "theme_strength");
  const participation = firstPathNumber(row, "participation", "volume_participation", "smart_money", "participation_breadth");
  const acceleration = firstPathNumber(row, "acceleration", "acceleration_velocity", "momentum_20d", "trend_consistency");
  return {
    ...row,
    score,
    flow,
    relative_strength: relativeStrength,
    alpha_score: firstPathNumber(row, "alpha_score", "score", "ranking_score", "universe_ranking.ranking_score") ?? row.alpha_score ?? null,
    ranking_score: firstPathNumber(row, "ranking_score", "universe_ranking.ranking_score", "score", "alpha_score") ?? row.ranking_score ?? null,
    leadership,
    momentum,
    participation,
    acceleration,
    momentum_20d: firstPathNumber(row, "momentum_20d", "momentum") ?? row.momentum_20d ?? null,
    momentum_60d: firstPathNumber(row, "momentum_60d", "momentum_strength", "momentum") ?? row.momentum_60d ?? null,
    relative_strength_spy: firstPathNumber(row, "relative_strength_spy", "relative_strength", "sector_alignment") ?? row.relative_strength_spy ?? null,
    relative_strength_qqq: firstPathNumber(row, "relative_strength_qqq", "theme_alignment") ?? row.relative_strength_qqq ?? null,
    volatility_quality: firstPathNumber(row, "volatility_quality", "quality") ?? row.volatility_quality ?? null,
    volume_participation: firstPathNumber(row, "volume_participation", "smart_money", "participation") ?? row.volume_participation ?? null,
    drawdown_pressure: firstPathNumber(row, "drawdown_pressure", "bubble_risk") ?? row.drawdown_pressure ?? null,
    trend_consistency: firstPathNumber(row, "trend_consistency", "market_structure") ?? row.trend_consistency ?? null,
  };
}

export async function fetchStockAnalysis(
  ticker: string,
  options: { forceRefresh?: boolean; signal?: AbortSignal } = {},
): Promise<StockAnalysis> {
  const symbol = ticker.trim().toUpperCase() || "NVDA";
  const cacheKey = `miji:stock:${symbol}`;
  const cached = readLocalCache<StockAnalysis>(cacheKey);
  const normalizedCached = cached ? normalizeStockAnalysis(cached, symbol) : null;
  if (cached && !hasCanonicalPrice(cached, symbol)) clearLocalCache(cacheKey);
  const fallback = normalizedCached?.canonicalPrice !== null && normalizedCached ? normalizedCached : fallbackStock(symbol);
  const url = `${API_URL}/stock/${encodeURIComponent(symbol)}${options.forceRefresh ? "?force_refresh=true" : ""}`;
  const proxyUrl = `${STOCK_PROXY_URL}?ticker=${encodeURIComponent(symbol)}${options.forceRefresh ? "&force_refresh=true" : ""}`;
  try {
    const response = await fetchWithRetry(url, {
      cache: "no-store",
      signal: options.signal,
    });
    const data = normalizeStockAnalysis(unwrapStockPayload(await readJson<unknown>(response)), symbol);
    writeLocalCache(cacheKey, data);
    return data;
  } catch {
    try {
      const response = await fetchWithRetry(proxyUrl, { cache: "no-store", signal: options.signal });
      const data = normalizeStockAnalysis(unwrapStockPayload(await readJson<unknown>(response)), symbol);
      writeLocalCache(cacheKey, data);
      return data;
    } catch {}
    if (!fallback.canonicalPrice) clearLocalCache(cacheKey);
    return fallback;
  }
}

export async function searchStocks(query: string, registryThemes: ThemeRegistryEntry[] = []): Promise<SearchResult[]> {
  const normalized = query.trim().toUpperCase();
  if (!normalized) return POPULAR_SYMBOLS.slice(0, 7).map(enrichStockResult);
  const exactResult = resolveExactSearchResult(query, registryThemes);
  if (exactResult) return [exactResult];
  const intent = classifySearchIntent(query, registryThemes);
  const intentQuery = stripIntentPrefix(query);

  const localMatches = POPULAR_SYMBOLS.filter((item) => {
    const haystack = `${item.symbol} ${item.name}`.toUpperCase();
    return haystack.includes(normalized) || haystack.includes(intentQuery);
  }).map(enrichStockResult);
  const universalMatches = UNIVERSAL_SEARCH.filter((item) => {
    const haystack = `${item.symbol} ${item.name} ${item.type}`.toUpperCase();
    return haystack.includes(normalized) || haystack.includes(intentQuery);
  }).map(enrichUniversalResult);
  const themeMatches = buildRegistrySearchItems(registryThemes.filter((item) => matchesRegistryTheme(item, normalized)));
  const sectorMatches = OMNIBOX_SECTORS.filter((item) => matchesOmniboxItem(item, normalized)).map((item) => withWorkspaceAction(item, normalized));
  const commandMatches = [...OMNIBOX_COMMANDS, ...THEME_RESEARCH_COMMANDS].filter((item) => matchesOmniboxItem(item, normalized)).map((item) => withWorkspaceAction(item, normalized));
  const localBuckets: Record<OmniboxIntent, SearchResult[]> = {
    command: [...commandMatches, ...localMatches, ...themeMatches, ...sectorMatches, ...universalMatches],
    theme: [...themeMatches, ...localMatches, ...sectorMatches, ...commandMatches, ...universalMatches],
    sector: [...sectorMatches, ...localMatches, ...themeMatches, ...commandMatches, ...universalMatches],
    ticker: [...localMatches, ...universalMatches, ...themeMatches, ...sectorMatches, ...commandMatches],
    natural_language: [...localMatches, ...themeMatches, ...sectorMatches, ...commandMatches, ...universalMatches],
  };
  const localResults = rankSearchResults(mergeSearchResults(localBuckets[intent]), query);

  if (
    intent === "command"
    || intent === "theme"
    || intent === "sector"
    || normalized.length <= 1
    || localResults.some((item) => item.group && item.group !== "Stocks")
  ) {
    return localResults.slice(0, 10);
  }

  const shouldQueryRemote = /^[A-Z.]{2,8}$/.test(intentQuery) && localResults.length === 0;

  try {
    if (!shouldQueryRemote) return localResults.slice(0, 10);
    const response = await fetchWithRetry(`${API_URL}/search?q=${encodeURIComponent(normalized)}`, {
      cache: "no-store",
    });
    const remote = await readJson<SearchResult[]>(response);
    const merged = rankSearchResults(mergeSearchResults([...localResults, ...remote.map((item) => enrichStockResult({
      ...item,
      price: validPrice(item.price),
      change_percent: validNumber(item.change_percent),
      quote_status: item.quote_status,
    }))]), query);
    return merged.slice(0, 10);
  } catch {
    const fallback = localResults;
    return fallback.length > 0
      ? fallback.slice(0, 10)
      : [enrichStockResult({ symbol: intentQuery || normalized, name: intentQuery || normalized, exchange: "US", type: "Equity" })];
  }
}

export async function fetchSectorRotation(options: { signal?: AbortSignal } = {}): Promise<RotationSnapshotResponse> {
  const cacheKey = "miji:sector-rotation:v6";
  try {
    const response = await fetchWithRetry(`${API_URL}/sector/rotation`, {
      cache: "no-store",
      signal: options.signal,
    });
    const snapshot = normalizeRotationSnapshot(await readJson<unknown>(response));
    writeLocalCache(cacheKey, snapshot);
    return snapshot;
  } catch (error) {
    if (options.signal?.aborted) throw error;
    return normalizeRotationSnapshot(readLocalCache<unknown>(cacheKey) ?? EMPTY_ROTATION_SNAPSHOT);
  }
}

function fallbackStockResearch(symbol: string): StockResearchResponse {
  const ticker = symbol.trim().toUpperCase() || "NVDA";
  return {
    available: false,
    ticker,
    generated_at: new Date().toISOString(),
    company_header: {
      company_name: ticker,
      ticker,
      theme_rank: null,
      theme_lifecycle: "Unavailable",
      research_coverage: 0,
      primary_theme: "Unavailable",
    },
    supply_chain_roles: [],
    theme_exposure: [],
    investment_thesis: {
      why_it_matters: [],
      current_drivers: [],
      catalysts: [],
      risks: [],
      research_gaps: ["Stock research projection is unavailable."],
    },
    evidence_chain: [],
    research_completeness: {
      coverage: 0,
      evidence_strength: 0,
      validation_status: "Research Incomplete",
      open_questions: ["Which persisted evidence links this company to a theme?"],
      research_gaps: ["Stock research projection is unavailable."],
    },
    decision_support: {
      research_state: "Research Incomplete",
      bull_case: [],
      bear_case: [],
      monitoring_triggers: [],
      research_gaps: ["No decision support projection is available."],
    },
    related_companies: {
      same_theme: [],
      same_bottleneck: [],
      same_controller: [],
      same_opportunity: [],
    },
  };
}

export async function fetchStockResearch(
  ticker: string,
  options: { signal?: AbortSignal } = {},
): Promise<StockResearchResponse> {
  const symbol = ticker.trim().toUpperCase() || "NVDA";
  try {
    const response = await fetchWithRetry(`${API_URL}/api/stock-research/${encodeURIComponent(symbol)}`, {
      cache: "no-store",
      signal: options.signal,
    });
    return readJson<StockResearchResponse>(response);
  } catch (error) {
    if (options.signal?.aborted) throw error;
    return fallbackStockResearch(symbol);
  }
}

export async function fetchMarketOverview(): Promise<MarketOverviewItem[]> {
  try {
    const response = await fetchWithRetry(`${API_URL}/market/overview`, { cache: "no-store" });
    const data = await readJson<MarketOverviewItem[] | MarketOverviewResponse>(response);
    if (Array.isArray(data)) return data;
    return Array.isArray(data.items) ? data.items : [];
  } catch {
    throw new Error("Connecting to quant engine...");
  }
}

export async function warmupQuantEngine(): Promise<void> {
  if (IS_PRODUCTION) return;
  try {
    const response = await fetchWithRetry(`${API_URL}/warmup`, {
      cache: "no-store",
      method: "POST",
    });
    await readJson<Record<string, unknown>>(response);
  } catch {
    // Render warmup is opportunistic; user-facing requests still use retry states.
  }
}

export async function fetchAlphaQuant(universe = "sp500"): Promise<AlphaQuantResponse> {
  const data = await fetchFreshJson<AlphaQuantResponse>(`miji:alpha:v5:${universe}`, `${API_URL}/alpha/top?universe=${encodeURIComponent(universe)}`, fallbackAlpha(universe));
  return normalizeAlphaQuantResponse(data);
}

const CANONICAL_THEME_ALIASES: Record<string, string> = {
  "cpo": "cpo_photonics",
  "cpo_photonics": "cpo_photonics",
  "co_packaged_optics": "cpo_photonics",
  "cowos": "cowos",
  "co_wo_s": "cowos",
  "glass_substrate": "glass_substrate",
  "glass_core": "glass_substrate",
  "hbm": "hbm",
  "ai_infrastructure": "ai_infrastructure",
  "data_center_cooling": "data_center_cooling",
  "advanced_packaging": "advanced_packaging",
  "power_grid": "power_grid",
  "electric_grid": "power_grid",
  "robotics": "robotics",
  "edge_ai": "edge_ai",
};

const CANONICAL_THEME_DISPLAY_NAMES: Record<string, string> = {
  "hbm": "HBM",
  "cowos": "CoWoS",
  "glass_substrate": "Glass Substrate",
  "cpo_photonics": "CPO",
  "ai_infrastructure": "AI Infrastructure",
  "data_center_cooling": "Data Center Cooling",
  "advanced_packaging": "Advanced Packaging",
  "power_grid": "Power Grid",
  "robotics": "Robotics",
  "edge_ai": "Edge AI",
};

export function normalizeThemeIntelligenceId(value: string): string {
  const normalized = String(value || "")
    .trim()
    .replace(/^theme:/i, "")
    .replace(/[_-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return CANONICAL_THEME_ALIASES[normalized] ?? normalized;
}

export function resolveCanonicalThemeIdentity(value: string): { rawName: string; themeId: string; displayName: string; canonical: boolean } {
  const rawName = String(value || "").trim().replace(/\s+/g, " ");
  const themeId = normalizeThemeIntelligenceId(rawName);
  const displayName = CANONICAL_THEME_DISPLAY_NAMES[themeId] ?? rawName;
  return {
    rawName,
    themeId,
    displayName,
    canonical: Boolean(CANONICAL_THEME_DISPLAY_NAMES[themeId]),
  };
}

export function resolveCanonicalThemeSelection(...values: Array<string | null | undefined>): ReturnType<typeof resolveCanonicalThemeIdentity> {
  const identities = values.map((value) => resolveCanonicalThemeIdentity(value ?? "")).filter((identity) => identity.rawName);
  return identities.find((identity) => identity.canonical)
    ?? identities[0]
    ?? resolveCanonicalThemeIdentity("");
}

export function traceThemeIdentity(
  stage: string,
  rawThemeName: string,
  normalizedThemeId = normalizeThemeIntelligenceId(rawThemeName),
  aggregateRequestId: string | null = null,
): void {
  if (!IS_DEVELOPMENT) return;
  console.info(`[theme-identity] ${JSON.stringify({
    stage,
    raw_theme_name: rawThemeName,
    normalized_theme_id: normalizedThemeId,
    aggregate_request_id: aggregateRequestId,
  })}`);
}

export function themeIntelligenceCacheKey(themeId: string): string {
  return `miji:theme-intelligence:v1:${normalizeThemeIntelligenceId(themeId)}`;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item ?? "").trim()).filter(Boolean) : [];
}

function normalizeThemeScoreRecord(value: unknown): ThemeScoreRecord {
  const row = isRecord(value) ? value : {};
  const theme = String(row.theme ?? row.theme_name ?? row.name ?? "");
  return {
    theme,
    theme_id: normalizeThemeIntelligenceId(String(row.theme_id ?? theme)),
    ai_potential_score: validNumber(row.ai_potential_score),
    research_importance: validNumber(row.research_importance),
    allocation_readiness: validNumber(row.allocation_readiness),
    risk_adjusted_score: validNumber(row.risk_adjusted_score),
    conviction_level: String(row.conviction_level ?? "Unrated"),
    score_components: isRecord(row.score_components) ? row.score_components : {},
    why_high_score: typeof row.why_high_score === "string" ? row.why_high_score : undefined,
    why_low_score: typeof row.why_low_score === "string" ? row.why_low_score : undefined,
    major_strengths: stringArray(row.major_strengths),
    major_risks: stringArray(row.major_risks),
    allocation_notes: stringArray(row.allocation_notes),
    conviction_reason: typeof row.conviction_reason === "string" ? row.conviction_reason : undefined,
    updated_at: typeof row.updated_at === "string" ? row.updated_at : undefined,
  };
}

function normalizeThemeDiscoveryRecord(value: unknown): ThemeDiscoveryRecord {
  const row = isRecord(value) ? value : {};
  const name = String(row.name ?? row.theme ?? "");
  return {
    theme_id: normalizeThemeIntelligenceId(String(row.theme_id ?? name)),
    name,
    name_zh: typeof row.name_zh === "string" ? row.name_zh : undefined,
    ai_score: validNumber(row.ai_score ?? row.final_ai_score),
    final_ai_score: validNumber(row.final_ai_score ?? row.ai_score),
    discovery_score: validNumber(row.discovery_score),
    emerging_score: validNumber(row.emerging_score),
    catalyst_score: validNumber(row.catalyst_score),
    entity_strength_score: validNumber(row.entity_strength_score),
    confidence_score: validNumber(row.confidence_score),
    crowding_proxy: validNumber(row.crowding_proxy),
    lifecycle_stage: typeof row.lifecycle_stage === "string" ? row.lifecycle_stage : undefined,
    lifecycle_confidence: validNumber(row.lifecycle_confidence),
    expected_next_stage: typeof row.expected_next_stage === "string" ? row.expected_next_stage : undefined,
    time_window: typeof row.time_window === "string" ? row.time_window : undefined,
    key_catalysts: Array.isArray(row.key_catalysts) ? row.key_catalysts.map(normalizeThemeCatalystRecord) : [],
    beneficiaries: Array.isArray(row.beneficiaries) ? row.beneficiaries.map(normalizeThemeBeneficiaryRecord) : [],
    brief: isRecord(row.brief) ? {
      why_now: typeof row.brief.why_now === "string" ? row.brief.why_now : undefined,
      signals: stringArray(row.brief.signals),
      risks: stringArray(row.brief.risks),
      watch_triggers: stringArray(row.brief.watch_triggers),
    } : undefined,
  };
}

function normalizeThemeCatalystRecord(value: unknown): ThemeCatalystRecord {
  const row = isRecord(value) ? value : {};
  return {
    name: typeof row.name === "string" ? row.name : typeof row.catalyst_name === "string" ? row.catalyst_name : undefined,
    catalyst_name: typeof row.catalyst_name === "string" ? row.catalyst_name : typeof row.name === "string" ? row.name : undefined,
    type: typeof row.type === "string" ? row.type : typeof row.catalyst_type === "string" ? row.catalyst_type : undefined,
    catalyst_type: typeof row.catalyst_type === "string" ? row.catalyst_type : typeof row.type === "string" ? row.type : undefined,
    source: typeof row.source === "string" ? row.source : undefined,
    description: typeof row.description === "string" ? row.description : undefined,
    impact_score: validNumber(row.impact_score),
    confidence_score: validNumber(row.confidence_score),
    novelty_score: validNumber(row.novelty_score),
    duration_score: validNumber(row.duration_score),
    stage_relevance: validNumber(row.stage_relevance),
    catalyst_strength: validNumber(row.catalyst_strength),
    timeline_status: typeof row.timeline_status === "string" ? row.timeline_status : undefined,
    polarity: typeof row.polarity === "string" ? row.polarity : undefined,
    cluster_key: typeof row.cluster_key === "string" ? row.cluster_key : undefined,
    updated_at: typeof row.updated_at === "string" ? row.updated_at : undefined,
  };
}

function normalizeThemeBottleneckRecord(value: unknown): ThemeBottleneckRecord {
  const row = isRecord(value) ? value : {};
  return {
    name: typeof row.name === "string" ? row.name : typeof row.bottleneck_name === "string" ? row.bottleneck_name : undefined,
    bottleneck_name: typeof row.bottleneck_name === "string" ? row.bottleneck_name : typeof row.name === "string" ? row.name : undefined,
    type: typeof row.type === "string" ? row.type : typeof row.bottleneck_type === "string" ? row.bottleneck_type : undefined,
    bottleneck_type: typeof row.bottleneck_type === "string" ? row.bottleneck_type : typeof row.type === "string" ? row.type : undefined,
    severity_score: validNumber(row.severity_score),
    duration_score: validNumber(row.duration_score),
    resolution_probability: validNumber(row.resolution_probability),
    impact_score: validNumber(row.impact_score),
    bottleneck_strength: validNumber(row.bottleneck_strength),
    timeline_status: typeof row.timeline_status === "string" ? row.timeline_status : undefined,
    description: typeof row.description === "string" ? row.description : undefined,
    controllers: Array.isArray(row.controllers) ? row.controllers.filter(isRecord) : [],
    beneficiaries: Array.isArray(row.beneficiaries) ? row.beneficiaries.filter(isRecord) : [],
    what_fixes_it: stringArray(row.what_fixes_it),
    what_to_monitor: stringArray(row.what_to_monitor),
    evidence: Array.isArray(row.evidence) ? row.evidence.filter(isRecord) : [],
    updated_at: typeof row.updated_at === "string" ? row.updated_at : undefined,
  };
}

function normalizeThemeBeneficiaryRecord(value: unknown): ThemeBeneficiaryRecord {
  const row = isRecord(value) ? value : {};
  return {
    ticker: String(row.ticker ?? row.symbol ?? ""),
    company: typeof row.company === "string" ? row.company : typeof row.company_name === "string" ? row.company_name : undefined,
    company_name: typeof row.company_name === "string" ? row.company_name : typeof row.company === "string" ? row.company : undefined,
    beneficiary_type: typeof row.beneficiary_type === "string" ? row.beneficiary_type : typeof row.role === "string" ? row.role : undefined,
    beneficiary_score: validNumber(row.beneficiary_score),
    allocation_score: validNumber(row.allocation_score),
    allocation_bucket: typeof row.allocation_bucket === "string" ? row.allocation_bucket : undefined,
    relationship_strength: validNumber(row.relationship_strength),
    role: typeof row.role === "string" ? row.role : typeof row.beneficiary_type === "string" ? row.beneficiary_type : undefined,
    updated_at: typeof row.updated_at === "string" ? row.updated_at : undefined,
  };
}

function normalizeThemePortfolioRecord(value: unknown): ThemePortfolioRecord {
  const row = isRecord(value) ? value : {};
  return {
    portfolio_type: String(row.portfolio_type ?? ""),
    portfolio_name: String(row.portfolio_name ?? row.name ?? ""),
    portfolio_score: validNumber(row.portfolio_score),
    risk_profile: typeof row.risk_profile === "string" ? row.risk_profile : undefined,
    lifecycle_mix: isRecord(row.lifecycle_mix) ? Object.fromEntries(Object.entries(row.lifecycle_mix).map(([key, item]) => [key, validNumber(item) ?? 0])) : {},
    bubble_exposure: validNumber(row.bubble_exposure),
    allocation_quality: validNumber(row.allocation_quality),
    themes: Array.isArray(row.themes)
      ? row.themes.map((item) => {
        const allocation = isRecord(item) ? item : {};
        const theme = typeof allocation.theme === "string" ? allocation.theme : undefined;
        return {
          theme,
          theme_id: normalizeThemeIntelligenceId(String(allocation.theme_id ?? theme ?? "")),
          weight: validNumber(allocation.weight),
          allocation_rationale: typeof allocation.allocation_rationale === "string" ? allocation.allocation_rationale : undefined,
        };
      })
      : [],
    explanation: typeof row.explanation === "string" ? row.explanation : undefined,
    risk_notes: stringArray(row.risk_notes),
    updated_at: typeof row.updated_at === "string" ? row.updated_at : undefined,
  };
}

function normalizeThemeRankings(value: unknown): ThemeScoresResponse["rankings"] {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).map(([key, rows]) => [key, Array.isArray(rows) ? rows.map(normalizeThemeScoreRecord) : []]),
  ) as ThemeScoresResponse["rankings"];
}

export function emptyThemeScoresResponse(): ThemeScoresResponse {
  return { themes: [], rankings: {}, source_status: {} };
}

export function emptyThemeDiscoveryResponse(): ThemeDiscoveryResponse {
  return { themes: [], source_status: {} };
}

export function emptyThemePortfolioResponse(): ThemePortfolioResponse {
  return { portfolios: [], rankings: {}, source_status: {} };
}

function emptyThemeIndustrialIntelligence(themeId: string): ThemeAggregateResponse["industrial_intelligence"] {
  const normalized = normalizeThemeIntelligenceId(themeId);
  return {
    identity: {
      requested_theme_id: normalized,
      canonical_theme_key: normalized,
      display_name: String(themeId || normalized),
      aliases: [],
      resolution_state: "unresolved",
    },
    lineage: {
      graph_snapshot_id: null,
      graph_build_version: null,
      controller_snapshot_id: null,
      controller_version: null,
      opportunity_snapshot_id: null,
      opportunity_version: null,
      packet_family_version: null,
      packet_family_revision: null,
      lineage_state: "unavailable",
    },
    graph: {
      snapshot_id: null,
      build_version: null,
      nodes: [],
      edges: [],
      evidence_count: 0,
      dependency_paths: [],
      counts_by_type: {},
    },
    constraints: [],
    controllers: [],
    opportunities: [],
    decision_packets: {
      family: null,
      theme_packet: null,
      matching_packets: [],
    },
    coverage: {
      overall_coverage: 0,
      components: {},
    },
    research_gaps: [],
  };
}

export function emptyThemeAggregate(themeId: string): ThemeAggregateResponse {
  const normalized = normalizeThemeIntelligenceId(themeId);
  return {
    theme_id: normalized,
    name: String(themeId || normalized),
    score: {},
    discovery: {},
    lifecycle: {
      theme_id: normalized,
      name: String(themeId || normalized),
      lifecycle_stage: null,
      lifecycle_confidence: null,
      expected_next_stage: null,
      time_window: null,
      stage_reason: null,
      history: [],
    },
    catalysts: { top_catalysts: [], future_catalysts: [], key_blockers: [] },
    bottlenecks: {
      primary_bottleneck: null,
      secondary_bottlenecks: [],
      controllers: [],
      beneficiaries: [],
      what_fixes_it: [],
      what_to_monitor: [],
    },
    beneficiaries: {
      top_beneficiaries: [],
      controllers: [],
      resolution_enablers: [],
      direct_beneficiaries: [],
      indirect_beneficiaries: [],
    },
    portfolio_context: { portfolios: [] },
    supply_chain: {
      layers: [],
      bottleneck_controllers: [],
      dependency_paths: [],
      risks: [],
      resolutions: [],
    },
    relationship_intelligence: {
      related_themes: [],
      shared_controllers: [],
      shared_beneficiaries: [],
      portfolio_exposure: [],
      shared_supply_chain_roles: [],
    },
    industrial_intelligence: emptyThemeIndustrialIntelligence(themeId),
  };
}

function normalizeThemeScoresResponse(value: unknown): ThemeScoresResponse {
  const row = isRecord(value) ? value : {};
  return {
    themes: Array.isArray(row.themes) ? row.themes.map(normalizeThemeScoreRecord) : [],
    rankings: normalizeThemeRankings(row.rankings),
    source_status: isRecord(row.source_status) ? row.source_status : {},
  };
}

function normalizeThemeDiscoveryResponse(value: unknown): ThemeDiscoveryResponse {
  const row = isRecord(value) ? value : {};
  return {
    themes: Array.isArray(row.themes) ? row.themes.map(normalizeThemeDiscoveryRecord) : [],
    source_status: isRecord(row.source_status) ? row.source_status : {},
  };
}

function normalizeThemePortfolioResponse(value: unknown): ThemePortfolioResponse {
  const row = isRecord(value) ? value : {};
  const rankings = isRecord(row.rankings)
    ? Object.fromEntries(Object.entries(row.rankings).map(([key, rows]) => [key, Array.isArray(rows) ? rows.map(normalizeThemePortfolioRecord) : []]))
    : {};
  return {
    portfolios: Array.isArray(row.portfolios) ? row.portfolios.map(normalizeThemePortfolioRecord) : [],
    rankings,
    source_status: isRecord(row.source_status) ? row.source_status : {},
  };
}

function normalizeIndustrialNode(value: unknown): ThemeAggregateResponse["industrial_intelligence"]["graph"]["nodes"][number] | null {
  if (!isRecord(value)) return null;
  const nodeType = String(value.node_type ?? "");
  const canonicalKey = String(value.canonical_key ?? "");
  if (!nodeType || !canonicalKey) return null;
  return {
    node_type: nodeType,
    canonical_key: canonicalKey,
    display_name: String(value.display_name ?? canonicalKey),
    aliases: stringArray(value.aliases),
    external_ids: isRecord(value.external_ids) ? value.external_ids : {},
  };
}

function normalizeIndustrialPath(value: unknown): ThemeAggregateResponse["industrial_intelligence"]["graph"]["dependency_paths"][number] | null {
  if (!isRecord(value)) return null;
  const nodes = Array.isArray(value.nodes)
    ? value.nodes.map(normalizeIndustrialNode).filter((node): node is NonNullable<typeof node> => node !== null)
    : [];
  if (nodes.length < 2) return null;
  return {
    path_id: typeof value.path_id === "string" ? value.path_id : undefined,
    depth: validNumber(value.depth) ?? Math.max(0, nodes.length - 1),
    nodes,
    edges: Array.isArray(value.edges)
      ? value.edges.map((item) => {
        const edge = isRecord(item) ? item : {};
        return {
          source_type: String(edge.source_type ?? ""),
          source_key: String(edge.source_key ?? ""),
          relationship_type: String(edge.relationship_type ?? ""),
          target_type: String(edge.target_type ?? ""),
          target_key: String(edge.target_key ?? ""),
          evidence_ids: Array.isArray(edge.evidence_ids)
            ? edge.evidence_ids.map(validNumber).filter((id): id is number => id !== null)
            : [],
        };
      }).filter((edge) => edge.source_type && edge.source_key && edge.relationship_type && edge.target_type && edge.target_key)
      : [],
    evidence_ids: Array.isArray(value.evidence_ids)
      ? value.evidence_ids.map(validNumber).filter((id): id is number => id !== null)
      : [],
  };
}

function normalizeThemeIndustrialIntelligence(
  value: unknown,
  themeId: string,
): ThemeAggregateResponse["industrial_intelligence"] {
  const fallback = emptyThemeIndustrialIntelligence(themeId);
  if (!isRecord(value)) return fallback;
  const identity = isRecord(value.identity) ? value.identity : {};
  const lineage = isRecord(value.lineage) ? value.lineage : {};
  const graph = isRecord(value.graph) ? value.graph : {};
  const packets = isRecord(value.decision_packets) ? value.decision_packets : {};
  const coverage = isRecord(value.coverage) ? value.coverage : {};
  const components = isRecord(coverage.components) ? coverage.components : {};
  const metric = (item: unknown) => {
    const row = isRecord(item) ? item : {};
    return {
      numerator: validNumber(row.numerator) ?? 0,
      denominator: validNumber(row.denominator) ?? 0,
      coverage: validNumber(row.coverage) ?? 0,
      availability_state: String(row.availability_state ?? "unavailable"),
    };
  };
  const paths = (item: unknown) => Array.isArray(item)
    ? item.map(normalizeIndustrialPath).filter((path): path is NonNullable<typeof path> => path !== null)
    : [];
  return {
    identity: {
      requested_theme_id: String(identity.requested_theme_id ?? fallback.identity.requested_theme_id),
      canonical_theme_key: String(identity.canonical_theme_key ?? fallback.identity.canonical_theme_key),
      display_name: String(identity.display_name ?? fallback.identity.display_name),
      aliases: stringArray(identity.aliases),
      resolution_state: String(identity.resolution_state ?? fallback.identity.resolution_state),
    },
    lineage: {
      graph_snapshot_id: validNumber(lineage.graph_snapshot_id),
      graph_build_version: typeof lineage.graph_build_version === "string" ? lineage.graph_build_version : null,
      controller_snapshot_id: validNumber(lineage.controller_snapshot_id),
      controller_version: typeof lineage.controller_version === "string" ? lineage.controller_version : null,
      opportunity_snapshot_id: validNumber(lineage.opportunity_snapshot_id),
      opportunity_version: typeof lineage.opportunity_version === "string" ? lineage.opportunity_version : null,
      packet_family_version: typeof lineage.packet_family_version === "string" ? lineage.packet_family_version : null,
      packet_family_revision: validNumber(lineage.packet_family_revision),
      lineage_state: String(lineage.lineage_state ?? fallback.lineage.lineage_state),
    },
    graph: {
      snapshot_id: validNumber(graph.snapshot_id),
      build_version: typeof graph.build_version === "string" ? graph.build_version : null,
      nodes: Array.isArray(graph.nodes)
        ? graph.nodes.map(normalizeIndustrialNode).filter((node): node is NonNullable<typeof node> => node !== null)
        : [],
      edges: Array.isArray(graph.edges)
        ? graph.edges.map((item) => {
          const edge = isRecord(item) ? item : {};
          return {
            source_type: String(edge.source_type ?? ""),
            source_key: String(edge.source_key ?? ""),
            relationship_type: String(edge.relationship_type ?? ""),
            target_type: String(edge.target_type ?? ""),
            target_key: String(edge.target_key ?? ""),
            evidence_ids: Array.isArray(edge.evidence_ids)
              ? edge.evidence_ids.map(validNumber).filter((id): id is number => id !== null)
              : [],
          };
        }).filter((edge) => edge.source_type && edge.source_key && edge.relationship_type && edge.target_type && edge.target_key)
        : [],
      evidence_count: validNumber(graph.evidence_count) ?? 0,
      dependency_paths: paths(graph.dependency_paths),
      counts_by_type: Object.fromEntries(Object.entries(isRecord(graph.counts_by_type) ? graph.counts_by_type : {})
        .map(([key, count]) => [key, validNumber(count) ?? 0])),
    },
    constraints: Array.isArray(value.constraints)
      ? value.constraints.map((item) => {
        const row = isRecord(item) ? item : {};
        return {
          canonical_key: String(row.canonical_key ?? ""),
          display_name: String(row.display_name ?? row.canonical_key ?? ""),
          constraint_type: typeof row.constraint_type === "string" ? row.constraint_type : null,
          severity: validNumber(row.severity),
          evidence_count: validNumber(row.evidence_count) ?? 0,
          resolution_state: String(row.resolution_state ?? "unresolved"),
          resolver_company_keys: stringArray(row.resolver_company_keys),
          exposed_company_keys: stringArray(row.exposed_company_keys),
          severity_source: typeof row.severity_source === "string" ? row.severity_source : null,
          coverage: validNumber(row.coverage),
        };
      }).filter((row) => row.canonical_key)
      : [],
    controllers: Array.isArray(value.controllers)
      ? value.controllers.map((item) => {
        const row = isRecord(item) ? item : {};
        return {
          company_key: String(row.company_key ?? ""),
          company_name: String(row.company_name ?? row.ticker ?? ""),
          rank: validNumber(row.rank),
          controller_score: validNumber(row.controller_score),
          coverage: validNumber(row.coverage),
          coverage_confidence: validNumber(row.coverage_confidence),
          controller_types: stringArray(row.controller_types),
          evidence_count: validNumber(row.evidence_count) ?? 0,
          evidence_ids: Array.isArray(row.evidence_ids)
            ? row.evidence_ids.map(validNumber).filter((id): id is number => id !== null)
            : [],
          reasoning_paths: paths(row.reasoning_paths),
        };
      }).filter((row) => row.company_key)
      : [],
    opportunities: Array.isArray(value.opportunities)
      ? value.opportunities.map((item) => {
        const row = isRecord(item) ? item : {};
        return {
          company_key: String(row.company_key ?? ""),
          company_name: String(row.company_name ?? row.ticker ?? ""),
          rank: validNumber(row.rank),
          opportunity_score: validNumber(row.opportunity_score),
          coverage_confidence: validNumber(row.coverage_confidence),
          coverage_component: validNumber(row.coverage_component),
          controller_contribution: validNumber(row.controller_contribution),
          constraint_contribution: validNumber(row.constraint_contribution),
          opportunity_types: stringArray(row.opportunity_types),
          evidence_count: validNumber(row.evidence_count) ?? 0,
          evidence_ids: Array.isArray(row.evidence_ids)
            ? row.evidence_ids.map(validNumber).filter((id): id is number => id !== null)
            : [],
          availability_states: Object.fromEntries(
            Object.entries(isRecord(row.availability_states) ? row.availability_states : {})
              .map(([key, state]) => [key, String(state)]),
          ),
          reasoning_paths: paths(row.reasoning_paths),
        };
      }).filter((row) => row.company_key)
      : [],
    decision_packets: {
      family: isRecord(packets.family) ? packets.family : null,
      theme_packet: isRecord(packets.theme_packet) ? packets.theme_packet : null,
      matching_packets: Array.isArray(packets.matching_packets) ? packets.matching_packets.filter(isRecord) : [],
    },
    coverage: {
      overall_coverage: validNumber(coverage.overall_coverage) ?? 0,
      components: Object.fromEntries(Object.entries(components).map(([key, value]) => [key, metric(value)])),
    },
    research_gaps: Array.isArray(value.research_gaps)
      ? value.research_gaps.map((item) => {
        const row = isRecord(item) ? item : {};
        return {
          code: String(row.code ?? ""),
          label: String(row.label ?? row.code ?? ""),
          layer: String(row.layer ?? ""),
          state: String(row.state ?? "missing"),
          observed_count: validNumber(row.observed_count) ?? 0,
        };
      }).filter((row) => row.code)
      : [],
  };
}

export function normalizeThemeAggregateResponse(value: unknown, themeId: string): ThemeAggregateResponse {
  const fallback = emptyThemeAggregate(themeId);
  if (!isRecord(value)) return fallback;
  const name = String(value.name ?? fallback.name);
  const normalized = normalizeThemeIntelligenceId(String(value.theme_id ?? name));
  const catalysts = isRecord(value.catalysts) ? value.catalysts : {};
  const bottlenecks = isRecord(value.bottlenecks) ? value.bottlenecks : {};
  const beneficiaries = isRecord(value.beneficiaries) ? value.beneficiaries : {};
  const portfolioContext = isRecord(value.portfolio_context) ? value.portfolio_context : {};
  const lifecycle = isRecord(value.lifecycle) ? value.lifecycle : {};
  const supplyChain = isRecord(value.supply_chain) ? value.supply_chain : {};
  const relationshipIntelligence = isRecord(value.relationship_intelligence) ? value.relationship_intelligence : {};
  return {
    theme_id: normalized,
    name,
    score: isRecord(value.score) ? normalizeThemeScoreRecord({ ...value.score, theme: value.score.theme ?? name, theme_id: value.score.theme_id ?? normalized }) : {},
    discovery: isRecord(value.discovery) ? normalizeThemeDiscoveryRecord({ ...value.discovery, name: value.discovery.name ?? name, theme_id: value.discovery.theme_id ?? normalized }) : {},
    lifecycle: {
      theme_id: normalized,
      name,
      lifecycle_stage: typeof lifecycle.lifecycle_stage === "string" && lifecycle.lifecycle_stage.trim() ? lifecycle.lifecycle_stage : null,
      lifecycle_confidence: validNumber(lifecycle.lifecycle_confidence),
      expected_next_stage: typeof lifecycle.expected_next_stage === "string" && lifecycle.expected_next_stage.trim() ? lifecycle.expected_next_stage : null,
      time_window: typeof lifecycle.time_window === "string" && lifecycle.time_window.trim() ? lifecycle.time_window : null,
      stage_reason: typeof lifecycle.stage_reason === "string" && lifecycle.stage_reason.trim() ? lifecycle.stage_reason : null,
      source: typeof lifecycle.source === "string" ? lifecycle.source : null,
      history: Array.isArray(lifecycle.history) ? lifecycle.history.filter(isRecord) : [],
    },
    catalysts: {
      top_catalysts: Array.isArray(catalysts.top_catalysts) ? catalysts.top_catalysts.map(normalizeThemeCatalystRecord) : [],
      future_catalysts: Array.isArray(catalysts.future_catalysts) ? catalysts.future_catalysts.map(normalizeThemeCatalystRecord) : [],
      key_blockers: Array.isArray(catalysts.key_blockers) ? catalysts.key_blockers.map(normalizeThemeCatalystRecord) : [],
    },
    bottlenecks: {
      primary_bottleneck: bottlenecks.primary_bottleneck ? normalizeThemeBottleneckRecord(bottlenecks.primary_bottleneck) : null,
      secondary_bottlenecks: Array.isArray(bottlenecks.secondary_bottlenecks) ? bottlenecks.secondary_bottlenecks.map(normalizeThemeBottleneckRecord) : [],
      controllers: Array.isArray(bottlenecks.controllers) ? bottlenecks.controllers.filter(isRecord) : [],
      beneficiaries: Array.isArray(bottlenecks.beneficiaries) ? bottlenecks.beneficiaries.filter(isRecord) : [],
      what_fixes_it: stringArray(bottlenecks.what_fixes_it),
      what_to_monitor: stringArray(bottlenecks.what_to_monitor),
    },
    beneficiaries: {
      top_beneficiaries: Array.isArray(beneficiaries.top_beneficiaries) ? beneficiaries.top_beneficiaries.map(normalizeThemeBeneficiaryRecord) : [],
      controllers: Array.isArray(beneficiaries.controllers) ? beneficiaries.controllers.map(normalizeThemeBeneficiaryRecord) : [],
      resolution_enablers: Array.isArray(beneficiaries.resolution_enablers) ? beneficiaries.resolution_enablers.map(normalizeThemeBeneficiaryRecord) : [],
      direct_beneficiaries: Array.isArray(beneficiaries.direct_beneficiaries) ? beneficiaries.direct_beneficiaries.map(normalizeThemeBeneficiaryRecord) : [],
      indirect_beneficiaries: Array.isArray(beneficiaries.indirect_beneficiaries) ? beneficiaries.indirect_beneficiaries.map(normalizeThemeBeneficiaryRecord) : [],
    },
    portfolio_context: {
      portfolios: Array.isArray(portfolioContext.portfolios)
        ? portfolioContext.portfolios.map((item) => {
          const row = isRecord(item) ? item : {};
          return {
            portfolio_type: String(row.portfolio_type ?? ""),
            portfolio_name: String(row.portfolio_name ?? ""),
            weight: validNumber(row.weight),
            risk_profile: typeof row.risk_profile === "string" ? row.risk_profile : undefined,
            portfolio_score: validNumber(row.portfolio_score),
            allocation_rationale: typeof row.allocation_rationale === "string" ? row.allocation_rationale : undefined,
          };
        })
        : [],
    },
    supply_chain: {
      layers: Array.isArray(supplyChain.layers)
        ? supplyChain.layers.map((item) => {
          const layer = isRecord(item) ? item : {};
          return {
            layer_id: String(layer.layer_id ?? ""),
            layer_name: String(layer.layer_name ?? ""),
            entities: Array.isArray(layer.entities)
              ? layer.entities.map((entityValue) => {
                const entity = isRecord(entityValue) ? entityValue : {};
                return {
                  ticker: String(entity.ticker ?? "").toUpperCase(),
                  company: String(entity.company ?? entity.ticker ?? ""),
                  role: String(entity.role ?? ""),
                  strength: validNumber(entity.strength) ?? 0,
                  is_bottleneck_controller: Boolean(entity.is_bottleneck_controller),
                };
              }).filter((entity) => entity.ticker)
              : [],
            has_bottleneck: Boolean(layer.has_bottleneck),
          };
        }).filter((layer) => layer.layer_id && layer.entities.length > 0)
        : [],
      bottleneck_controllers: stringArray(supplyChain.bottleneck_controllers).map((ticker) => ticker.toUpperCase()),
      dependency_paths: Array.isArray(supplyChain.dependency_paths)
        ? supplyChain.dependency_paths.map((item) => {
          const path = isRecord(item) ? item : {};
          return {
            path: String(path.path ?? ""),
            strength: validNumber(path.strength),
            explanation: typeof path.explanation === "string" ? path.explanation : undefined,
            risk: typeof path.risk === "string" ? path.risk : undefined,
          };
        }).filter((item) => item.path)
        : [],
      risks: Array.isArray(supplyChain.risks)
        ? supplyChain.risks.map((item) => {
          const risk = isRecord(item) ? item : {};
          return {
            risk_type: String(risk.risk_type ?? ""),
            value: validNumber(risk.value),
            explanation: typeof risk.explanation === "string" ? risk.explanation : undefined,
          };
        }).filter((item) => item.risk_type)
        : [],
      resolutions: Array.isArray(supplyChain.resolutions)
        ? supplyChain.resolutions.map((item) => {
          const resolution = isRecord(item) ? item : {};
          return {
            resolution: String(resolution.resolution ?? ""),
            resolution_probability: validNumber(resolution.resolution_probability),
            impact: validNumber(resolution.impact),
            timeline: typeof resolution.timeline === "string" ? resolution.timeline : undefined,
          };
        }).filter((item) => item.resolution)
        : [],
    },
    relationship_intelligence: {
      related_themes: Array.isArray(relationshipIntelligence.related_themes)
        ? relationshipIntelligence.related_themes.map((item) => {
          const relationship = isRecord(item) ? item : {};
          const components = isRecord(relationship.components) ? relationship.components : {};
          return {
            theme_id: normalizeThemeIntelligenceId(String(relationship.theme_id ?? normalized)),
            related_theme_id: normalizeThemeIntelligenceId(String(relationship.related_theme_id ?? "")),
            overlap_score: validNumber(relationship.overlap_score),
            components: {
              beneficiary_overlap: validNumber(components.beneficiary_overlap),
              controller_overlap: validNumber(components.controller_overlap),
              bottleneck_overlap: validNumber(components.bottleneck_overlap),
              catalyst_overlap: validNumber(components.catalyst_overlap),
              portfolio_overlap: validNumber(components.portfolio_overlap),
            },
            shared_beneficiaries: stringArray(relationship.shared_beneficiaries),
            shared_controllers: stringArray(relationship.shared_controllers),
            shared_bottlenecks: stringArray(relationship.shared_bottlenecks),
            shared_catalysts: stringArray(relationship.shared_catalysts),
            shared_portfolios: stringArray(relationship.shared_portfolios),
            shared_supply_chain_roles: stringArray(relationship.shared_supply_chain_roles),
          };
        }).filter((item) => item.related_theme_id)
        : [],
      shared_controllers: stringArray(relationshipIntelligence.shared_controllers),
      shared_beneficiaries: stringArray(relationshipIntelligence.shared_beneficiaries),
      portfolio_exposure: stringArray(relationshipIntelligence.portfolio_exposure),
      shared_supply_chain_roles: stringArray(relationshipIntelligence.shared_supply_chain_roles),
    },
    industrial_intelligence: normalizeThemeIndustrialIntelligence(value.industrial_intelligence, themeId),
  };
}

export async function fetchThemeScores(): Promise<ThemeScoresResponse> {
  const data = await fetchFreshJson<unknown>("miji:theme-scores:v1", `${API_URL}/api/theme/scores`, emptyThemeScoresResponse());
  return normalizeThemeScoresResponse(data);
}

export async function fetchThemeDiscovery(): Promise<ThemeDiscoveryResponse> {
  const data = await fetchFreshJson<unknown>("miji:theme-discovery:v1", `${API_URL}/api/theme/discovery`, emptyThemeDiscoveryResponse());
  return normalizeThemeDiscoveryResponse(data);
}

export async function fetchThemePortfolio(): Promise<ThemePortfolioResponse> {
  const data = await fetchFreshJson<unknown>("miji:theme-portfolio:v1", `${API_URL}/api/theme/portfolio`, emptyThemePortfolioResponse());
  return normalizeThemePortfolioResponse(data);
}

export async function fetchThemeIntelligence(themeId: string, options?: { signal?: AbortSignal }): Promise<ThemeAggregateResponse> {
  const normalized = normalizeThemeIntelligenceId(themeId);
  traceThemeIdentity("aggregate_request", themeId, normalized, normalized);
  const fallback = emptyThemeAggregate(themeId);
  const cacheKey = themeIntelligenceCacheKey(normalized);
  try {
    let request = themeIntelligenceRequests.get(normalized);
    if (!request) {
      request = fetchWithRetry(`${API_URL}/api/theme/intelligence/${encodeURIComponent(normalized)}`, {
        cache: "no-store",
      }).then((response) => readJson<unknown>(response));
      themeIntelligenceRequests.set(normalized, request);
      const release = () => {
        if (themeIntelligenceRequests.get(normalized) === request) themeIntelligenceRequests.delete(normalized);
      };
      request.then(release, release);
    }
    const data = options?.signal
      ? await new Promise<unknown>((resolve, reject) => {
          const abort = () => reject(new DOMException("Request aborted", "AbortError"));
          if (options.signal?.aborted) {
            abort();
            return;
          }
          options.signal?.addEventListener("abort", abort, { once: true });
          request.then(
            (value) => {
              options.signal?.removeEventListener("abort", abort);
              resolve(value);
            },
            (error) => {
              options.signal?.removeEventListener("abort", abort);
              reject(error);
            },
          );
        })
      : await request;
    const normalizedData = normalizeThemeAggregateResponse(data, themeId);
    writeLocalCache(cacheKey, normalizedData);
    return normalizedData;
  } catch (error) {
    if (options?.signal?.aborted) throw error;
    return normalizeThemeAggregateResponse(readLocalCache<ThemeAggregateResponse>(cacheKey), themeId) ?? fallback;
  }
}

export async function fetchThemeTop(): Promise<ThemeTopResponse> {
  const data = await fetchFreshJson<ThemeTopResponse>("miji:theme-top:v4", `${API_URL}/theme/top`, fallbackThemeTop());
  return {
    ...data,
    themes: (data.themes ?? []).map(normalizeThemeScore),
  };
}

export async function fetchThemeEmerging(): Promise<EmergingThemeResponse> {
  const fallback = fallbackThemeTop();
  const data = await fetchCachedJson<EmergingThemeResponse>("miji:theme-emerging:v3", `${API_URL}/theme/emerging`, {
    generated_at: fallback.generated_at,
    emerging_themes: fallback.themes.slice(0, 6),
    summary: "Theme engine calibrating. No active emerging signal confirmed yet.",
  });
  return {
    ...data,
    emerging_themes: (data.emerging_themes ?? []).map(normalizeThemeScore),
  };
}

export async function fetchThemeRotation(): Promise<ThemeRotationResponse> {
  const fallback = fallbackThemeTop();
  const data = await fetchCachedJson<ThemeRotationResponse>("miji:theme-rotation:v3", `${API_URL}/theme/rotation`, {
    generated_at: fallback.generated_at,
    rotation_map: fallback.themes,
    strengthening: [],
    weakening: [],
    overheated_themes: [],
    undervalued_themes: [],
    summary: "Theme rotation matrix is calibrating.",
  });
  return {
    ...data,
    rotation_map: (data.rotation_map ?? []).map(normalizeThemeScore),
    strengthening: (data.strengthening ?? []).map(normalizeThemeScore),
    weakening: (data.weakening ?? []).map(normalizeThemeScore),
    overheated_themes: (data.overheated_themes ?? []).map(normalizeThemeScore),
    undervalued_themes: (data.undervalued_themes ?? []).map(normalizeThemeScore),
  };
}

export async function fetchThemeCapitalFlow(): Promise<ThemeCapitalFlowResponse> {
  const fallback = fallbackThemeTop();
  const data = await fetchCachedJson<ThemeCapitalFlowResponse>("miji:theme-flow:v3", `${API_URL}/theme/capital-flow`, {
    generated_at: fallback.generated_at,
    capital_flow: fallback.themes,
    summary: "Capital flow engine warming. Awaiting finite lightweight factor inputs.",
  });
  return {
    ...data,
    capital_flow: (data.capital_flow ?? []).map(normalizeThemeScore),
  };
}

export async function fetchThemeSupplyChain(theme?: string): Promise<ThemeSupplyChainResponse> {
  const query = theme ? `?theme=${encodeURIComponent(theme)}` : "";
  const data = await fetchFreshJson<ThemeSupplyChainResponse>(`miji:theme-supply:v2:${theme ?? "all"}`, `${API_URL}/theme/supply-chain${query}`, {
    generated_at: new Date().toISOString(),
    themes: [],
  });
  return {
    ...data,
    themes: (data.themes ?? []).map((themeRow) => ({
      ...themeRow,
      leaders: (themeRow.leaders ?? []).map(normalizeThemeLeader),
      supply_chain: Object.fromEntries(
        Object.entries(themeRow.supply_chain ?? {}).map(([role, leaders]) => [role, leaders.map(normalizeThemeLeader)]),
      ),
    })),
  };
}

export async function fetchThemeNarrative(): Promise<ThemeNarrativeResponse> {
  const data = await fetchCachedJson<ThemeNarrativeResponse>("miji:theme-narrative:v3", `${API_URL}/theme/narrative`, {
    generated_at: new Date().toISOString(),
    status: "partial_data",
    lifecycle_state: "warming",
    narratives: [],
  });
  return {
    ...data,
    narratives: (data.narratives ?? []).map(normalizeNarrativeIntelligence),
    top_narratives: (data.top_narratives ?? []).map(normalizeNarrativeIntelligence),
    emerging_narratives: (data.emerging_narratives ?? []).map(normalizeNarrativeIntelligence),
    weakening_narratives: (data.weakening_narratives ?? []).map(normalizeNarrativeIntelligence),
    crowded_narratives: (data.crowded_narratives ?? []).map(normalizeNarrativeIntelligence),
    defensive_narratives: (data.defensive_narratives ?? []).map(normalizeNarrativeIntelligence),
  };
}

export async function fetchThemeForecast(horizon: ForecastHorizon = "1m"): Promise<ThemeForecastResponse> {
  return fetchFreshJson<ThemeForecastResponse>(
    `miji:theme-forecast:v1:${horizon}`,
    `${API_URL}/theme/forecast?horizon=${encodeURIComponent(horizon)}`,
    {
      available: false,
      status: "disabled",
      lifecycle_state: "warming",
      horizon,
      top_future_themes: [],
      emerging_themes: [],
      weakening_themes: [],
      crowded_themes: [],
      defensive_rotation: [],
      forecasts: [],
      message: "Theme Forecast AI is unavailable.",
    },
  );
}

export async function fetchThemeForecastValidation(horizon: ForecastHorizon = "1m"): Promise<ThemeForecastValidationResponse> {
  return fetchFreshJson<ThemeForecastValidationResponse>(
    `miji:theme-forecast-validation:v1:${horizon}`,
    `${API_URL}/theme/forecast/validation?horizon=${encodeURIComponent(horizon)}`,
    {
      horizon,
      status: "partial_data",
      lifecycle_state: "partial_live",
      observations: 0,
      hit_rate: null,
      precision_at_5: null,
      information_ratio: null,
      max_drawdown: null,
      calibration_quality: null,
      turnover: null,
      excess_return_stability: null,
      confusion_matrix: {},
      walk_forward: { method: "expanding_window", shuffle: false },
      reason: "Validation unavailable.",
    },
  );
}

export async function fetchThemeStocks(theme: string): Promise<ThemeStocksResponse> {
  const fallback = fallbackThemeStocks(theme);
  const data = await fetchFreshJson<ThemeStocksResponse>(
    `miji:theme-stocks:v2:${theme}`,
    `${API_URL}/theme/${encodeURIComponent(theme)}/stocks`,
    fallback,
  );
  return normalizeThemeStocksResponse(data);
}

export async function fetchThemeDetail(theme: string): Promise<ThemeDetailResponse> {
  const stocks = fallbackThemeStocks(theme);
  const data = await fetchFreshJson<ThemeDetailResponse>(
    `miji:theme-detail:v2:${theme}`,
    `${API_URL}/theme/${encodeURIComponent(theme)}/detail`,
    {
      ...stocks,
      theme_score: null,
      confidence: "Partial Data",
      status: "Calibrating",
      supply_chain: {},
      capital_flow: null,
      bubble_risk: null,
      explainability: [],
      risks: [],
    },
  );
  return normalizeThemeStocksResponse(data);
}

export async function fetchThemeScout(signal?: AbortSignal): Promise<ThemeScoutResponse> {
  const response = await fetchWithRetry(`${API_URL}/api/theme/scout`, {
    cache: "no-store",
    signal,
  });
  return readJson<ThemeScoutResponse>(response);
}

export async function fetchThemeRegistry(signal?: AbortSignal): Promise<ThemeRegistryResponse> {
  const response = await fetchWithRetry(`${API_URL}/api/theme/registry`, {
    cache: "no-store",
    signal,
  });
  const payload = await readJson<ThemeRegistryResponse>(response);
  return {
    available: Boolean(payload.available),
    generated_at: String(payload.generated_at ?? ""),
    source_priority: Array.isArray(payload.source_priority) ? payload.source_priority : ["GRAPH", "SCOUT", "MANUAL"],
    themes: Array.isArray(payload.themes) ? payload.themes.map((row) => ({
      theme_id: String(row.theme_id ?? ""),
      theme_name: String(row.theme_name ?? row.theme_id ?? ""),
      status: row.status,
      source: row.source,
      theme_type: row.theme_type ?? "INDUSTRIAL",
      rank: Number.isFinite(Number(row.rank)) ? Number(row.rank) : 0,
      research_case_count: Number.isFinite(Number(row.research_case_count)) ? Number(row.research_case_count) : 0,
      graph_snapshot_count: Number.isFinite(Number(row.graph_snapshot_count)) ? Number(row.graph_snapshot_count) : 0,
      controller_count: Number.isFinite(Number(row.controller_count)) ? Number(row.controller_count) : 0,
      opportunity_count: Number.isFinite(Number(row.opportunity_count)) ? Number(row.opportunity_count) : 0,
      updated_at: String(row.updated_at ?? ""),
    })).filter((row) => row.theme_id && row.theme_name) : [],
  };
}

function normalizeThemeRank(row: Partial<ThemeRank>): ThemeRank | null {
  const themeId = String(row.theme_id ?? "").trim();
  const themeName = String(row.theme_name ?? themeId).trim();
  const lifecycle = row.lifecycle;
  if (!themeId || !themeName) return null;
  if (!["EMERGING", "ACCELERATING", "ACTIVE", "MONITORING", "DECLINING"].includes(String(lifecycle))) return null;
  return {
    theme_id: themeId,
    theme_name: themeName,
    lifecycle: lifecycle as ThemeRank["lifecycle"],
    rank_score: Number.isFinite(Number(row.rank_score)) ? Number(row.rank_score) : 0,
    momentum_score: Number.isFinite(Number(row.momentum_score)) ? Number(row.momentum_score) : 0,
    evidence_score: Number.isFinite(Number(row.evidence_score)) ? Number(row.evidence_score) : 0,
    research_score: Number.isFinite(Number(row.research_score)) ? Number(row.research_score) : 0,
    controller_score: Number.isFinite(Number(row.controller_score)) ? Number(row.controller_score) : 0,
    opportunity_score: Number.isFinite(Number(row.opportunity_score)) ? Number(row.opportunity_score) : 0,
    updated_at: String(row.updated_at ?? ""),
  };
}

export async function fetchThemeRanking(signal?: AbortSignal): Promise<ThemeRankingResponse> {
  const response = await fetchWithRetry(`${API_URL}/api/theme/ranking`, {
    cache: "no-store",
    signal,
  });
  const payload = await readJson<ThemeRankingResponse>(response);
  return {
    available: Boolean(payload.available),
    generated_at: String(payload.generated_at ?? ""),
    algorithm_version: String(payload.algorithm_version ?? ""),
    weights: {
      evidence: Number(payload.weights?.evidence ?? 0),
      research: Number(payload.weights?.research ?? 0),
      controller: Number(payload.weights?.controller ?? 0),
      opportunity: Number(payload.weights?.opportunity ?? 0),
      momentum: Number(payload.weights?.momentum ?? 0),
    },
    themes: Array.isArray(payload.themes)
      ? payload.themes.map((row) => normalizeThemeRank(row)).filter((row): row is ThemeRank => row !== null)
      : [],
  };
}

export async function fetchThemeScoutCandidate(
  candidateKey: string,
  signal?: AbortSignal,
): Promise<ThemeScoutCandidate> {
  const response = await fetchWithRetry(
    `${API_URL}/api/theme/scout/${encodeURIComponent(candidateKey)}`,
    { cache: "no-store", signal },
  );
  return readJson<ThemeScoutCandidate>(response);
}

export async function fetchResearchPipeline(signal?: AbortSignal): Promise<ResearchPipelineResponse> {
  const response = await fetchWithRetry(`${API_URL}/api/research/pipeline`, {
    cache: "no-store",
    signal,
  });
  return readJson<ResearchPipelineResponse>(response);
}

export async function fetchDecisionIntelligence(signal?: AbortSignal): Promise<DecisionIntelligenceResponse> {
  const response = await fetchWithRetry(`${API_URL}/api/decision-intelligence`, {
    cache: "no-store",
    signal,
  });
  return readJson<DecisionIntelligenceResponse>(response);
}

export async function fetchDecisionIntelligencePacket(
  packetId: string,
  signal?: AbortSignal,
): Promise<DecisionIntelligenceDetailResponse> {
  const response = await fetchWithRetry(
    `${API_URL}/api/decision-intelligence/${encodeURIComponent(packetId)}`,
    { cache: "no-store", signal },
  );
  return readJson<DecisionIntelligenceDetailResponse>(response);
}

export async function createResearchPipelineCase(
  payload: {
    source_type: string;
    source_id: string;
    theme_id: string;
    title: string;
  },
  signal?: AbortSignal,
): Promise<ResearchPipelineCaseDetail> {
  const response = await fetchWithRetry(`${API_URL}/api/research/pipeline`, {
    method: "POST",
    cache: "no-store",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson<ResearchPipelineCaseDetail>(response);
}

export async function transitionResearchPipelineCase(
  caseId: string,
  payload: { new_status: string; reason: string },
  signal?: AbortSignal,
): Promise<ResearchPipelineCaseDetail> {
  const response = await fetchWithRetry(`${API_URL}/api/research/pipeline/${encodeURIComponent(caseId)}/transition`, {
    method: "POST",
    cache: "no-store",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson<ResearchPipelineCaseDetail>(response);
}

export async function linkResearchPipelineArtifact(
  caseId: string,
  payload: { linked_type: string; linked_id: string },
  signal?: AbortSignal,
): Promise<ResearchPipelineCaseDetail> {
  const response = await fetchWithRetry(`${API_URL}/api/research/pipeline/${encodeURIComponent(caseId)}/links`, {
    method: "POST",
    cache: "no-store",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return readJson<ResearchPipelineCaseDetail>(response);
}

export const defaultWatchlist = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "SPY", "QQQ"];
