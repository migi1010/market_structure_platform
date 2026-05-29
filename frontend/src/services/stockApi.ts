import type {
  AlphaQuantResponse,
  EmergingThemeResponse,
  MarketOverviewItem,
  MarketOverviewResponse,
  OmniboxGroup,
  OmniboxIntent,
  OmniboxTargetTab,
  SearchResult,
  SectorRotation,
  StockAnalysis,
  StockQuote,
  AlphaQuantRow,
  NarrativeIntelligence,
  ThemeScore,
  ThemeCapitalFlowResponse,
  ThemeDetailResponse,
  ThemeNarrativeResponse,
  ThemeRotationResponse,
  ThemeStocksResponse,
  ThemeSupplyChainResponse,
  ThemeTopResponse,
  WorkspaceAction,
} from "@/types/stock";
import { enabledTerminalModules } from "@/modules/terminalModules";

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
  { symbol: "NOW", name: "ServiceNow, Inc.", exchange: "NYSE", type: "Equity" },
];

const UNIVERSAL_SEARCH: SearchResult[] = [
  { symbol: "HBM", name: "High Bandwidth Memory / 高頻寬記憶體", exchange: "Theme", type: "Theme" },
  { symbol: "NUCLEAR", name: "Nuclear Energy / 核能", exchange: "Theme", type: "Theme" },
  { symbol: "COPPER", name: "Cable / Copper / 電纜銅材", exchange: "Theme", type: "Theme" },
  { symbol: "GRID", name: "Electric Grid / 電網基建", exchange: "Theme", type: "Theme" },
  { symbol: "DEFENSE AI", name: "Defense AI / 國防 AI", exchange: "Theme", type: "Theme" },
  { symbol: "ROBOTICS", name: "Robotics / 機器人", exchange: "Theme", type: "Theme" },
  { symbol: "CYBERSECURITY", name: "Cybersecurity / 資安", exchange: "Theme", type: "Theme" },
  { symbol: "SEMICONDUCTOR", name: "Semiconductor / 半導體", exchange: "Sector", type: "Sector" },
  { symbol: "UTILITIES", name: "Utilities / 公用事業", exchange: "Sector", type: "Sector" },
  { symbol: "ENERGY", name: "Energy / 能源", exchange: "Sector", type: "Sector" },
  { symbol: "FINANCIALS", name: "Financials / 金融", exchange: "Sector", type: "Sector" },
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

const OMNIBOX_THEMES: OmniboxRegistryItem[] = [
  ["AI Infrastructure", "AI capex, accelerators, cloud data centers, and power demand", ["AI", "ARTIFICIAL INTELLIGENCE", "AI INFRA", "AI INFRASTRUCTURE", "DATA CENTER"]],
  ["Semiconductor", "Chip design, foundry capacity, equipment, and memory leaders", ["SEMICONDUCTOR", "SEMICONDUCTORS", "CHIPS", "SMH", "SOXX"]],
  ["HBM", "High bandwidth memory supply chain and accelerator attach rates", ["HBM", "HIGH BANDWIDTH MEMORY", "MEMORY"]],
  ["Electric Grid", "Grid equipment, power infrastructure, and electrification bottlenecks", ["GRID", "ELECTRIC GRID", "POWER GRID", "UTILITIES"]],
  ["Nuclear Energy", "Uranium, reactor buildout, and baseload power infrastructure", ["NUCLEAR", "NUCLEAR ENERGY", "URANIUM"]],
  ["Defense AI", "Defense software, autonomy, sensors, and compute programs", ["DEFENSE", "DEFENSE AI", "AEROSPACE"]],
  ["Cybersecurity", "Security software, identity, endpoint, and cloud protection", ["CYBER", "CYBERSECURITY", "SECURITY"]],
  ["Robotics", "Industrial automation, robotics platforms, and autonomy supply chain", ["ROBOTICS", "ROBOTS", "AUTOMATION"]],
].map(([theme, description, aliases]) => ({
  symbol: `THEME:${String(theme).toUpperCase().replace(/[^A-Z0-9]+/g, "-")}`,
  name: String(theme),
  exchange: "Theme",
  type: "Theme",
  theme: String(theme),
  label: String(theme),
  description: String(description),
  intent: "theme" as OmniboxIntent,
  group: "Themes" as OmniboxGroup,
  target_tab: "theme-intelligence" as OmniboxTargetTab,
  aliases: aliases as string[],
}));

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
  if (type === "theme" || targetTab === "theme-intelligence") {
    const theme = item.theme ?? item.label ?? item.name;
    return {
      actionType: type === "theme" ? "open_theme" : "open_module",
      target_tab: "theme-intelligence",
      focusTarget: type === "theme" ? "theme-detail" : "theme-workspace",
      openMode: "replace",
      contextPayload: type === "theme" ? { theme, label: `Open ${theme}` } : { label: item.label ?? item.name },
    };
  }
  if (type === "sector" || targetTab === "market-intel") {
    const sector = item.sector ?? item.label ?? item.name;
    return {
      actionType: type === "sector" ? "open_sector" : "open_module",
      target_tab: "market-intel",
      focusTarget: "sector-drilldown",
      openMode: "replace",
      contextPayload: type === "sector" ? { sector, label: `Open ${sector} Rotation` } : { label: item.label ?? item.name },
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

export function classifySearchIntent(query: string): OmniboxIntent {
  const normalized = compactSearchText(query);
  const stripped = stripIntentPrefix(query);
  if (!normalized) return "ticker";
  if (/^THEME\s+/.test(normalized)) return "theme";
  if (/^SECTOR\s+/.test(normalized)) return "sector";
  if (OMNIBOX_COMMANDS.some((item) => matchesOmniboxItem(item, normalized))) return "command";
  if (OMNIBOX_THEMES.some((item) => matchesOmniboxItem(item, normalized))) return "theme";
  if (OMNIBOX_SECTORS.some((item) => matchesOmniboxItem(item, normalized))) return "sector";
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
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), remaining);
    try {
      return await browserRequest(input, {
        ...init,
        signal: controller.signal,
      });
    } catch (error) {
      lastError = error;
      if (attempt < MAX_ATTEMPTS && Date.now() + 750 * attempt < deadline) await sleep(750 * attempt);
    } finally {
      window.clearTimeout(timeout);
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
    canonicalQuoteStatus: canonicalPrice !== null && (!status || status === "unavailable") ? "live_or_cached" : status ?? "unavailable",
    canonicalSector,
  };
}

function normalizeQuote(data: Partial<StockAnalysis> | Record<string, unknown> | null | undefined, symbol: string): StockQuote {
  const raw = quoteRecord(data);
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
    source: firstString(raw.source) ?? undefined,
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
  const themes = ["AI Infrastructure", "Semiconductor", "Electric Grid", "Nuclear Energy", "Energy", "Defense", "Healthcare", "Financials"].map((theme) => ({
    related_stocks: fallbackThemeStocks(theme).related_stocks,
    top_alpha_stocks: fallbackThemeStocks(theme).top_alpha_stocks,
    theme,
    category: "Calibrating",
    description: "Live theme signal is calibrating.",
    theme_strength_score: null,
    theme_capital_flow_score: null,
    emerging_score: null,
    overheating_score: null,
    relative_momentum: null,
    etf_relative_strength: null,
    volume_expansion: null,
    institutional_accumulation: null,
    earnings_acceleration: null,
    revenue_acceleration: null,
    capex_trend: null,
    smart_money_accumulation: null,
    narrative_strength: null,
    narrative_acceleration: null,
    narrative_saturation: null,
    narrative_bubble_risk: null,
    breadth_participation: null,
    leadership_concentration: null,
    relative_strength_vs_spy: null,
    options_activity: null,
    supply_chain_acceleration: null,
    macro_alignment: null,
    leaders: [],
    etfs: [],
    macro_tags: [],
    explainability: ["Using latest cached institutional intelligence while live data warms up."],
  }));
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
    themes,
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

function toFiniteNumber(v: unknown): number | undefined {
  if (v === null || v === undefined) return undefined;
  if (typeof v === "string" && v.trim() === "") return undefined;
  if (typeof v !== "number" && typeof v !== "string") return undefined;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : undefined;
}

function normalizeSectorRotationResponse(data: unknown): SectorRotation[] {
  const rows = Array.isArray(data)
    ? data
    : isRecord(data) && Array.isArray(data.sectors)
      ? data.sectors
      : isRecord(data) && Array.isArray(data.items)
        ? data.items
        : isRecord(data) && Array.isArray(data.data)
          ? data.data
          : [];
  return rows
    .filter(isRecord)
    .map((row) => {
      const normalized = normalizeSectorRotationRow(row as unknown as SectorRotation);
      return {
        ...normalized,
        score: toFiniteNumber(normalized.score),
        relative_strength: toFiniteNumber(normalized.relative_strength),
        flow: toFiniteNumber(normalized.flow),
        leadership: toFiniteNumber(normalized.leadership),
        momentum: toFiniteNumber(normalized.momentum),
        participation: toFiniteNumber(normalized.participation),
        acceleration: toFiniteNumber(normalized.acceleration),
        confidence_score: toFiniteNumber(normalized.confidence_score),
      };
    });
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

export async function fetchStockAnalysis(ticker: string): Promise<StockAnalysis> {
  const symbol = ticker.trim().toUpperCase() || "NVDA";
  const cacheKey = `miji:stock:${symbol}`;
  const cached = readLocalCache<StockAnalysis>(cacheKey);
  const normalizedCached = cached ? normalizeStockAnalysis(cached, symbol) : null;
  if (cached && !hasCanonicalPrice(cached, symbol)) clearLocalCache(cacheKey);
  const fallback = normalizedCached?.canonicalPrice !== null && normalizedCached ? normalizedCached : fallbackStock(symbol);
  const url = `${API_URL}/stock/${encodeURIComponent(symbol)}`;
  const proxyUrl = `${STOCK_PROXY_URL}?ticker=${encodeURIComponent(symbol)}`;
  try {
    if (IS_DEVELOPMENT) console.debug("[stockApi] fetchStockAnalysis", { symbol, url });
    const response = await fetchWithRetry(url, {
      cache: "no-store",
    });
    const data = normalizeStockAnalysis(unwrapStockPayload(await readJson<unknown>(response)), symbol);
    writeLocalCache(cacheKey, data);
    if (IS_DEVELOPMENT) console.debug("[stockApi] stock response", { symbol, price: data.canonicalPrice, status: data.canonicalQuoteStatus });
    return data;
  } catch (error) {
    if (IS_DEVELOPMENT) console.debug("[stockApi] stock fetch failed", { symbol, url, error });
    try {
      const response = await fetchWithRetry(proxyUrl, { cache: "no-store" });
      const data = normalizeStockAnalysis(unwrapStockPayload(await readJson<unknown>(response)), symbol);
      writeLocalCache(cacheKey, data);
      if (IS_DEVELOPMENT) console.debug("[stockApi] stock proxy response", { symbol, price: data.canonicalPrice, status: data.canonicalQuoteStatus });
      return data;
    } catch (proxyError) {
      if (IS_DEVELOPMENT) console.debug("[stockApi] stock proxy failed", { symbol, proxyUrl, proxyError });
    }
    if (!fallback.canonicalPrice) clearLocalCache(cacheKey);
    return fallback;
  }
}

export async function searchStocks(query: string): Promise<SearchResult[]> {
  const normalized = query.trim().toUpperCase();
  if (!normalized) return POPULAR_SYMBOLS.slice(0, 7).map(enrichStockResult);
  const intent = classifySearchIntent(query);
  const intentQuery = stripIntentPrefix(query);

  const localMatches = POPULAR_SYMBOLS.filter((item) => {
    const haystack = `${item.symbol} ${item.name}`.toUpperCase();
    return haystack.includes(normalized) || haystack.includes(intentQuery);
  }).map(enrichStockResult);
  const universalMatches = UNIVERSAL_SEARCH.filter((item) => {
    const haystack = `${item.symbol} ${item.name} ${item.type}`.toUpperCase();
    return haystack.includes(normalized) || haystack.includes(intentQuery);
  }).map(enrichUniversalResult);
  const themeMatches = OMNIBOX_THEMES.filter((item) => matchesOmniboxItem(item, normalized)).map((item) => withWorkspaceAction(item, normalized));
  const sectorMatches = OMNIBOX_SECTORS.filter((item) => matchesOmniboxItem(item, normalized)).map((item) => withWorkspaceAction(item, normalized));
  const commandMatches = OMNIBOX_COMMANDS.filter((item) => matchesOmniboxItem(item, normalized)).map((item) => withWorkspaceAction(item, normalized));
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

export async function fetchSectorRotation(): Promise<SectorRotation[]> {
  const data = await fetchFreshJson<unknown>("miji:sector-rotation:v5", `${API_URL}/sector/rotation`, FALLBACK_SECTORS);
  if (IS_DEVELOPMENT) {
    console.debug("[sector-rotation] raw API payload", data);
  }
  const sectors = normalizeSectorRotationResponse(data);
  if (IS_DEVELOPMENT) {
    console.debug("[sector-rotation] normalized payload", sectors);
  }
  return sectors.length > 0 ? sectors : FALLBACK_SECTORS.map(normalizeSectorRotationRow);
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

export const defaultWatchlist = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "SPY", "QQQ"];
