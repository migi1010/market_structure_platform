import type {
  AlphaQuantResponse,
  EmergingThemeResponse,
  MarketOverviewItem,
  SearchResult,
  SectorRotation,
  StockAnalysis,
  StockQuote,
  ThemeCapitalFlowResponse,
  ThemeDetailResponse,
  ThemeNarrativeResponse,
  ThemeRotationResponse,
  ThemeStocksResponse,
  ThemeSupplyChainResponse,
  ThemeTopResponse,
} from "@/types/stock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://market-structure-platform.onrender.com";
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_ATTEMPTS = 3;
const CLIENT_CACHE_SCHEMA_VERSION = "stock_v6";

interface LocalCacheEnvelope<T> {
  schema_version: string;
  cached_at: string;
  data: T;
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

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
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
      return await fetch(input, {
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

function readLocalCache<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!isRecord(parsed) || parsed.schema_version !== CLIENT_CACHE_SCHEMA_VERSION || !("data" in parsed)) {
      window.localStorage.removeItem(key);
      return null;
    }
    const data = (parsed as unknown as LocalCacheEnvelope<T>).data;
    if (!isCacheableLocalPayload(key, data)) {
      window.localStorage.removeItem(key);
      return null;
    }
    return data;
  } catch {
    window.localStorage.removeItem(key);
    return null;
  }
}

function writeLocalCache<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;
  try {
    if (!isCacheableLocalPayload(key, value)) return;
    const envelope: LocalCacheEnvelope<T> = {
      schema_version: CLIENT_CACHE_SCHEMA_VERSION,
      cached_at: new Date().toISOString(),
      data: value,
    };
    window.localStorage.setItem(key, JSON.stringify(envelope));
  } catch {
    // Local cache is best effort and should never block the terminal.
  }
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

function validNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function validPrice(value: unknown): number | null {
  const number = validNumber(value);
  return number !== null && number > 0 ? number : null;
}

function normalizeQuote(data: Partial<StockAnalysis> | null | undefined, symbol: string): StockQuote {
  const raw = data?.quote;
  // Coerce to number: the backend always emits JSON numbers, but guard against string
  // serialization edge cases (e.g., some proxies or CDN rewrites) where price arrives as "215.33".
  const rawPrice = raw?.price ?? data?.price;
  const price = validPrice(typeof rawPrice === "string" ? parseFloat(rawPrice) : rawPrice);
  const rawChange = raw?.change ?? data?.change;
  const change = validNumber(typeof rawChange === "string" ? parseFloat(rawChange) : rawChange);
  const rawChangePercent = raw?.change_percent ?? data?.change_percent;
  const changePercent = validNumber(typeof rawChangePercent === "string" ? parseFloat(rawChangePercent) : rawChangePercent);
  const marketCap = validPrice(raw?.market_cap ?? data?.market_cap);
  return {
    ticker: (raw?.ticker ?? data?.ticker ?? symbol).trim().toUpperCase(),
    price,
    change,
    change_percent: changePercent,
    previous_close: validPrice(raw?.previous_close),
    market_cap: marketCap,
    pe_ratio: validNumber(raw?.pe_ratio),
    ps_ratio: validNumber(raw?.ps_ratio),
    currency: raw?.currency ?? "USD",
    status: price !== null ? raw?.status ?? data?.quote_status ?? "live_or_cached" : "unavailable",
    source: raw?.source,
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
      confidence_label: "Unavailable",
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
  const quote = normalizeQuote(data, symbol);
  const company = data?.company_name && data.company_name !== "Unknown" ? data.company_name : fallback.company_name;
  const sector = data?.sector && data.sector !== "Unknown" ? data.sector : fallback.sector;
  const hmm = data?.hmm_prediction ?? fallback.hmm_prediction;
  const trend = typeof hmm?.predicted_trend === "string" ? hmm.predicted_trend : "";
  const hmmAvailable = hmm?.available !== false && trend !== "Neutral" && !trend.toLowerCase().includes("calibrating") && validNumber(hmm?.confidence) !== null && validNumber(hmm?.bull_probability) !== null;
  return {
    ...fallback,
    ...data,
    ticker: (data?.ticker ?? symbol).trim().toUpperCase(),
    company_name: company,
    sector,
    price: quote.price ?? (typeof data?.price === "number" && Number.isFinite(data.price) && data.price > 0 ? data.price : null),
    change: quote.change ?? (typeof data?.change === "number" && Number.isFinite(data.change) ? data.change : null),
    change_percent: quote.change_percent ?? (typeof data?.change_percent === "number" && Number.isFinite(data.change_percent) ? data.change_percent : null),
    market_cap: quote.market_cap,
    quote_status: quote.status,
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
  const alphaFallbackUniverses: Record<string, string[]> = {
    sp500: ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "LLY", "JPM", "XOM", "V"],
    nasdaq100: ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "GOOGL", "COST", "TSLA", "AMD"],
    sox: ["NVDA", "AMD", "AVGO", "QCOM", "AMAT", "LRCX", "KLAC", "TSM", "ASML", "MU"],
    smh: ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "AMAT", "TXN", "LRCX", "MU"],
    soxx: ["NVDA", "AVGO", "AMD", "QCOM", "AMAT", "LRCX", "KLAC", "MU", "INTC", "TXN"],
  };
  const normalizedUniverse = universe.trim().toLowerCase().replace(/[ /-]+/g, "_");
  const symbols = alphaFallbackUniverses[normalizedUniverse] ?? alphaFallbackUniverses.sp500;
  const rows = symbols.map((symbol, index) => ({
    ticker: symbol,
    company_name: symbol,
    sector: "Calibrating",
    alpha_score: 50,
    base_alpha_score: 50,
    universe_context_score: 50,
    universe_adjustment: 0,
    universe_percentile: symbols.length > 1 ? ((symbols.length - index - 1) / (symbols.length - 1)) * 100 : 100,
    rank_in_universe: index + 1,
    universe: universe.toUpperCase(),
    quality: 50,
    growth: 50,
    smart_money: 50,
    valuation: 50,
    earnings_quality: 50,
    market_structure: 50,
    bubble_risk: 50,
    sector_alignment: 50,
    theme_alignment: 50,
    theme_strength: 50,
    theme_capital_flow: 50,
    theme_explanation: ["Live engine delayed. Showing cached institutional intelligence."],
    suggested_action: "Hold" as const,
    factor_importance: { quality: 0.2, growth: 0.2, smart_money: 0.2, valuation: 0.15, earnings_quality: 0.15, market_structure: 0.1 },
  }));
  return {
    generated_at: new Date().toISOString(),
    universe: universe.toUpperCase(),
    qlib_engine: { available: false, mode: "fallback", provider: "Miji Quant", factor_set: "Cached Alpha Fallback" },
    market_regime: { name: "Calibrating", confidence: 50 },
    factor_importance: rows[0]?.factor_importance ?? {},
    top_alpha: rows,
    recommendations: rows.slice(0, 5),
    summary: "Live engine delayed. Showing cached institutional intelligence.",
  };
}

const FALLBACK_SECTORS: SectorRotation[] = [
  "Technology", "Energy", "Healthcare", "Financials", "Industrials", "Utilities",
  "Consumer Discretionary", "Consumer Staples", "Materials", "Real Estate", "Communication Services",
].map((sector) => ({
  sector,
  score: 50,
  relative_strength: 50,
  flow: 50,
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
    theme_strength_score: 50,
    theme_capital_flow_score: 50,
    emerging_score: 45,
    overheating_score: 35,
    relative_momentum: 0,
    etf_relative_strength: 0,
    volume_expansion: 1,
    institutional_accumulation: 50,
    earnings_acceleration: 0,
    revenue_acceleration: 0,
    capex_trend: 50,
    smart_money_accumulation: 50,
    narrative_strength: 45,
    narrative_acceleration: 45,
    narrative_saturation: 35,
    narrative_bubble_risk: 30,
    breadth_participation: 50,
    leadership_concentration: 0,
    relative_strength_vs_spy: 0,
    options_activity: 50,
    supply_chain_acceleration: 50,
    macro_alignment: 50,
    leaders: [],
    etfs: [],
    macro_tags: [],
    explainability: ["Using latest cached institutional intelligence while live data warms up."],
  }));
  return {
    generated_at: new Date().toISOString(),
    cross_asset_regime: {
      risk_on_off: "Calibrating",
      risk_on_score: 50,
      liquidity_regime: "Calibrating",
      liquidity_score: 50,
      volatility_regime: "Calibrating",
      volatility_score: 50,
      inflation_regime: "Calibrating",
      inflation_score: 50,
      AI_capex_regime: "Calibrating",
      AI_capex_score: 50,
    },
    themes,
    summary: "Using latest cached institutional intelligence while live theme data warms up.",
  };
}

function normalizeAlphaQuantResponse(data: AlphaQuantResponse): AlphaQuantResponse {
  const normalizeRow = (row: AlphaQuantResponse["top_alpha"][number]) => {
    const quote = normalizeQuote(row as unknown as Partial<StockAnalysis>, row.ticker);
    return {
      ...row,
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

export async function fetchStockAnalysis(ticker: string): Promise<StockAnalysis> {
  const symbol = ticker.trim().toUpperCase();
  const cacheKey = `miji:stock:${symbol}`;
  const cached = readLocalCache<StockAnalysis>(cacheKey);
  const fallback = cached ? normalizeStockAnalysis(cached, symbol) : fallbackStock(symbol);
  try {
    const response = await fetchWithRetry(`${API_URL}/stock/${encodeURIComponent(symbol)}`, {
      cache: "no-store",
    });
    const data = normalizeStockAnalysis(await readJson<StockAnalysis>(response), symbol);
    writeLocalCache(cacheKey, data);
    return data;
  } catch {
    return fallback;
  }
}

export async function searchStocks(query: string): Promise<SearchResult[]> {
  const normalized = query.trim().toUpperCase();
  if (!normalized) return POPULAR_SYMBOLS.slice(0, 7);

  const localMatches = POPULAR_SYMBOLS.filter((item) => {
    const haystack = `${item.symbol} ${item.name}`.toUpperCase();
    return haystack.includes(normalized);
  });
  const universalMatches = UNIVERSAL_SEARCH.filter((item) => {
    const haystack = `${item.symbol} ${item.name} ${item.type}`.toUpperCase();
    return haystack.includes(normalized);
  });

  if (normalized.length <= 1) return [...localMatches, ...universalMatches].slice(0, 8);

  try {
    const response = await fetchWithRetry(`${API_URL}/search?q=${encodeURIComponent(normalized)}`, {
      cache: "no-store",
    });
    const remote = await readJson<SearchResult[]>(response);
    const merged = [...localMatches, ...universalMatches, ...remote.map((item) => ({
      ...item,
      price: validPrice(item.price),
      change_percent: validNumber(item.change_percent),
      quote_status: item.quote_status,
    }))].reduce<SearchResult[]>((acc, item) => {
      if (!acc.some((existing) => existing.symbol === item.symbol)) acc.push(item);
      return acc;
    }, []);
    return merged.slice(0, 8);
  } catch {
    const fallback = [...localMatches, ...universalMatches];
    return fallback.length > 0
      ? fallback.slice(0, 8)
      : [{ symbol: normalized, name: normalized, exchange: "US", type: "Equity" }];
  }
}

export async function fetchSectorRotation(): Promise<SectorRotation[]> {
  return fetchCachedJson<SectorRotation[]>("miji:sector-rotation", `${API_URL}/sector/rotation`, FALLBACK_SECTORS);
}

export async function fetchMarketOverview(): Promise<MarketOverviewItem[]> {
  try {
    const response = await fetchWithRetry(`${API_URL}/market/overview`, { cache: "no-store" });
    return readJson<MarketOverviewItem[]>(response);
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
  const data = await fetchFreshJson<AlphaQuantResponse>(`miji:alpha:v3:${universe}`, `${API_URL}/alpha/top?universe=${encodeURIComponent(universe)}`, fallbackAlpha(universe));
  return normalizeAlphaQuantResponse(data);
}

export async function fetchThemeTop(): Promise<ThemeTopResponse> {
  return fetchFreshJson<ThemeTopResponse>("miji:theme-top:v2", `${API_URL}/theme/top`, fallbackThemeTop());
}

export async function fetchThemeEmerging(): Promise<EmergingThemeResponse> {
  const fallback = fallbackThemeTop();
  return fetchCachedJson<EmergingThemeResponse>("miji:theme-emerging", `${API_URL}/theme/emerging`, {
    generated_at: fallback.generated_at,
    emerging_themes: fallback.themes.slice(0, 6),
    summary: "Theme engine calibrating. No active emerging signal confirmed yet.",
  });
}

export async function fetchThemeRotation(): Promise<ThemeRotationResponse> {
  const fallback = fallbackThemeTop();
  return fetchCachedJson<ThemeRotationResponse>("miji:theme-rotation", `${API_URL}/theme/rotation`, {
    generated_at: fallback.generated_at,
    rotation_map: fallback.themes,
    strengthening: [],
    weakening: [],
    overheated_themes: [],
    undervalued_themes: [],
    summary: "Theme rotation matrix is calibrating.",
  });
}

export async function fetchThemeCapitalFlow(): Promise<ThemeCapitalFlowResponse> {
  const fallback = fallbackThemeTop();
  return fetchCachedJson<ThemeCapitalFlowResponse>("miji:theme-flow", `${API_URL}/theme/capital-flow`, {
    generated_at: fallback.generated_at,
    capital_flow: fallback.themes,
    summary: "Capital flow temporarily unavailable. Using latest cached institutional intelligence.",
  });
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
  return fetchCachedJson<ThemeNarrativeResponse>("miji:theme-narrative", `${API_URL}/theme/narrative`, {
    generated_at: new Date().toISOString(),
    narratives: [],
  });
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
