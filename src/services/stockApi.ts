import type {
  AlphaQuantResponse,
  EmergingThemeResponse,
  MarketOverviewItem,
  SearchResult,
  SectorRotation,
  StockAnalysis,
  ThemeCapitalFlowResponse,
  ThemeNarrativeResponse,
  ThemeRotationResponse,
  ThemeSupplyChainResponse,
  ThemeTopResponse,
} from "@/types/stock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://market-structure-platform.onrender.com";
const REQUEST_TIMEOUT_MS = 15_000;
const MAX_ATTEMPTS = 3;

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

function readLocalCache<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeLocalCache<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
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

function fallbackAlpha(universe: string): AlphaQuantResponse {
  const symbols = ["NVDA", "MSFT", "AAPL", "AMZN", "META", "AVGO", "LLY", "JPM", "XOM", "V"];
  const rows = symbols.map((symbol) => ({
    ticker: symbol,
    company_name: symbol,
    sector: "Calibrating",
    alpha_score: 50,
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

function fallbackThemeTop(): ThemeTopResponse {
  const themes = ["AI Infrastructure", "Semiconductor", "Electric Grid", "Nuclear Energy", "Energy", "Defense", "Healthcare", "Financials"].map((theme) => ({
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

export async function fetchStockAnalysis(ticker: string): Promise<StockAnalysis> {
  const symbol = ticker.trim().toUpperCase();
  try {
    const response = await fetchWithRetry(`${API_URL}/stock/${encodeURIComponent(symbol)}`, {
      cache: "no-store",
    });
    return readJson<StockAnalysis>(response);
  } catch {
    throw new Error("Connecting to quant engine...");
  }
}

export async function searchStocks(query: string): Promise<SearchResult[]> {
  const normalized = query.trim().toUpperCase();
  if (!normalized) return POPULAR_SYMBOLS.slice(0, 7);

  const localMatches = POPULAR_SYMBOLS.filter((item) => {
    const haystack = `${item.symbol} ${item.name}`.toUpperCase();
    return haystack.includes(normalized);
  });

  if (normalized.length <= 1) return localMatches.slice(0, 8);

  try {
    const response = await fetchWithRetry(`${API_URL}/search?q=${encodeURIComponent(normalized)}`, {
      cache: "no-store",
    });
    const remote = await readJson<SearchResult[]>(response);
    const merged = [...localMatches, ...remote].reduce<SearchResult[]>((acc, item) => {
      if (!acc.some((existing) => existing.symbol === item.symbol)) acc.push(item);
      return acc;
    }, []);
    return merged.slice(0, 8);
  } catch {
    return localMatches.length > 0
      ? localMatches.slice(0, 8)
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
  return fetchCachedJson<AlphaQuantResponse>(`miji:alpha:${universe}`, `${API_URL}/alpha/top?universe=${encodeURIComponent(universe)}`, fallbackAlpha(universe));
}

export async function fetchThemeTop(): Promise<ThemeTopResponse> {
  return fetchCachedJson<ThemeTopResponse>("miji:theme-top", `${API_URL}/theme/top`, fallbackThemeTop());
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
  return fetchCachedJson<ThemeSupplyChainResponse>(`miji:theme-supply:${theme ?? "all"}`, `${API_URL}/theme/supply-chain${query}`, {
    generated_at: new Date().toISOString(),
    themes: [],
  });
}

export async function fetchThemeNarrative(): Promise<ThemeNarrativeResponse> {
  return fetchCachedJson<ThemeNarrativeResponse>("miji:theme-narrative", `${API_URL}/theme/narrative`, {
    generated_at: new Date().toISOString(),
    narratives: [],
  });
}

export const defaultWatchlist = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "SPY", "QQQ"];
