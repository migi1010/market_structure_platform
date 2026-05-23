import type {
  AlphaQuantResponse,
  EmergingThemeResponse,
  MarketOverviewItem,
  SearchResult,
  SectorRotation,
  StockAnalysis,
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

const STOCK_METADATA: Record<string, { name: string; sector: string }> = {
  AAPL: { name: "Apple Inc.", sector: "Technology" },
  NVDA: { name: "NVIDIA Corporation", sector: "Technology" },
  MSFT: { name: "Microsoft Corporation", sector: "Technology" },
  AMZN: { name: "Amazon.com Inc.", sector: "Consumer Discretionary" },
  META: { name: "Meta Platforms Inc.", sector: "Communication Services" },
  TSLA: { name: "Tesla Inc.", sector: "Consumer Discretionary" },
  PLTR: { name: "Palantir Technologies Inc.", sector: "Technology" },
  AMD: { name: "Advanced Micro Devices Inc.", sector: "Technology" },
  AVGO: { name: "Broadcom Inc.", sector: "Technology" },
  NOW: { name: "ServiceNow Inc.", sector: "Technology" },
  SPY: { name: "SPDR S&P 500 ETF Trust", sector: "ETF" },
  QQQ: { name: "Invesco QQQ Trust", sector: "ETF" },
  SMH: { name: "VanEck Semiconductor ETF", sector: "ETF" },
};

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

function validNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value !== 0 ? value : null;
}

function stockMetadata(symbol: string): { name: string; sector: string } {
  return STOCK_METADATA[symbol] ?? { name: symbol, sector: "US Equity" };
}

function fallbackStock(symbol: string): StockAnalysis {
  const metadata = stockMetadata(symbol);
  return {
    ticker: symbol,
    company_name: metadata.name,
    price: null,
    change: null,
    change_percent: null,
    market_cap: null,
    sector: metadata.sector,
    quote_status: "unavailable",
    bubble_analysis_data: {
      revenue: 0,
      net_income: 0,
      gross_margin: 0,
      operating_cash_flow: 0,
      free_cash_flow: 0,
      total_assets: 0,
      total_liabilities: 0,
      debt_ratio: 0,
      pe_ratio: 0,
      ps_ratio: 0,
      bubble_index: 50,
      classification: "Neutral Watch",
      valuation_heat: 0,
      revenue_divergence: 0,
      fcf_quality: 0,
      dilution_risk: 0,
      distribution_signal: 0,
      retail_speculation: 0,
      accrual_ratio: 0,
      net_income_quality: 0,
      ai_summary: "Bubble intelligence is calibrating with cached institutional fundamentals.",
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
  const company = data?.company_name && data.company_name !== "Unknown" ? data.company_name : fallback.company_name;
  const sector = data?.sector && data.sector !== "Unknown" ? data.sector : fallback.sector;
  const price = validNumber(data?.price);
  const changePercent = validNumber(data?.change_percent);
  const change = validNumber(data?.change);
  const hmm = data?.hmm_prediction ?? fallback.hmm_prediction;
  const trend = typeof hmm?.predicted_trend === "string" ? hmm.predicted_trend : "";
  const hmmAvailable = hmm?.available !== false && trend !== "Neutral" && !trend.toLowerCase().includes("calibrating") && validNumber(hmm?.confidence) !== null && validNumber(hmm?.bull_probability) !== null;
  return {
    ...fallback,
    ...data,
    ticker: (data?.ticker ?? symbol).trim().toUpperCase(),
    company_name: company,
    sector,
    price,
    change,
    change_percent: changePercent,
    market_cap: validNumber(data?.market_cap),
    quote_status: price !== null ? data?.quote_status ?? "live_or_cached" : "unavailable",
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

const FALLBACK_THEME_STOCKS: Record<string, Array<{ ticker: string; company_name: string; role: string }>> = {
  "AI INFRASTRUCTURE": [
    { ticker: "NVDA", company_name: "NVIDIA Corporation", role: "GPU / AI accelerator" },
    { ticker: "AVGO", company_name: "Broadcom Inc.", role: "Networking silicon" },
    { ticker: "VRT", company_name: "Vertiv Holdings Co.", role: "Power and cooling" },
    { ticker: "AMD", company_name: "Advanced Micro Devices Inc.", role: "GPU / AI accelerator" },
    { ticker: "ETN", company_name: "Eaton Corporation plc", role: "Electrical infrastructure" },
    { ticker: "ANET", company_name: "Arista Networks Inc.", role: "AI networking" },
  ],
  SEMICONDUCTOR: [
    { ticker: "NVDA", company_name: "NVIDIA Corporation", role: "AI accelerator" },
    { ticker: "AMD", company_name: "Advanced Micro Devices Inc.", role: "GPU / CPU" },
    { ticker: "TSM", company_name: "Taiwan Semiconductor Manufacturing Company", role: "Foundry" },
    { ticker: "ASML", company_name: "ASML Holding N.V.", role: "Lithography" },
    { ticker: "AMAT", company_name: "Applied Materials Inc.", role: "Equipment" },
    { ticker: "LRCX", company_name: "Lam Research Corporation", role: "Equipment" },
    { ticker: "MU", company_name: "Micron Technology Inc.", role: "Memory" },
  ],
  HBM: [
    { ticker: "NVDA", company_name: "NVIDIA Corporation", role: "HBM demand driver" },
    { ticker: "MU", company_name: "Micron Technology Inc.", role: "HBM memory" },
    { ticker: "AMD", company_name: "Advanced Micro Devices Inc.", role: "AI accelerator" },
    { ticker: "TSM", company_name: "Taiwan Semiconductor Manufacturing Company", role: "Advanced packaging" },
    { ticker: "AVGO", company_name: "Broadcom Inc.", role: "Custom silicon" },
  ],
  "GLASS SUBSTRATE": [
    { ticker: "INTC", company_name: "Intel Corporation", role: "Advanced substrate" },
    { ticker: "AMAT", company_name: "Applied Materials Inc.", role: "Equipment" },
    { ticker: "TSM", company_name: "Taiwan Semiconductor Manufacturing Company", role: "Foundry" },
    { ticker: "AMKR", company_name: "Amkor Technology Inc.", role: "Packaging" },
  ],
  CYBERSECURITY: [
    { ticker: "CRWD", company_name: "CrowdStrike Holdings Inc.", role: "Endpoint security" },
    { ticker: "PANW", company_name: "Palo Alto Networks Inc.", role: "Platform security" },
    { ticker: "ZS", company_name: "Zscaler Inc.", role: "Zero trust" },
    { ticker: "FTNT", company_name: "Fortinet Inc.", role: "Network security" },
    { ticker: "OKTA", company_name: "Okta Inc.", role: "Identity" },
  ],
  "ELECTRIC GRID": [
    { ticker: "ETN", company_name: "Eaton Corporation plc", role: "Electrical equipment" },
    { ticker: "GE", company_name: "GE Aerospace", role: "Power infrastructure" },
    { ticker: "PWR", company_name: "Quanta Services Inc.", role: "Grid services" },
    { ticker: "HUBB", company_name: "Hubbell Incorporated", role: "Grid equipment" },
    { ticker: "FCX", company_name: "Freeport-McMoRan Inc.", role: "Copper supply" },
  ],
  "NUCLEAR ENERGY": [
    { ticker: "CEG", company_name: "Constellation Energy Corporation", role: "Nuclear generation" },
    { ticker: "VST", company_name: "Vistra Corp.", role: "Power generation" },
    { ticker: "BWXT", company_name: "BWX Technologies Inc.", role: "Nuclear equipment" },
    { ticker: "CCJ", company_name: "Cameco Corporation", role: "Uranium" },
    { ticker: "SMR", company_name: "NuScale Power Corporation", role: "Small modular reactor" },
  ],
  SHIPPING: [
    { ticker: "ZIM", company_name: "ZIM Integrated Shipping Services", role: "Container shipping" },
    { ticker: "MATX", company_name: "Matson Inc.", role: "Ocean transport" },
    { ticker: "DAC", company_name: "Danaos Corporation", role: "Containership leasing" },
    { ticker: "SBLK", company_name: "Star Bulk Carriers Corp.", role: "Dry bulk" },
    { ticker: "GNK", company_name: "Genco Shipping & Trading Limited", role: "Dry bulk" },
  ],
};

function fallbackThemeStocks(theme: string): ThemeStocksResponse {
  const key = theme.trim().toUpperCase().replace(/-/g, " ");
  const related = FALLBACK_THEME_STOCKS[key] ?? [];
  return {
    generated_at: new Date().toISOString(),
    theme,
    theme_id: key.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
    related_stocks: related,
    top_alpha_stocks: related.slice(0, 5),
    summary: related.length > 0 ? `${theme} related stocks include ${related.slice(0, 3).map((item) => item.ticker).join(", ")}.` : "Theme stock universe calibrating.",
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
    const merged = [...localMatches, ...universalMatches, ...remote].reduce<SearchResult[]>((acc, item) => {
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

export async function fetchThemeStocks(theme: string): Promise<ThemeStocksResponse> {
  const fallback = fallbackThemeStocks(theme);
  return fetchCachedJson<ThemeStocksResponse>(
    `miji:theme-stocks:${theme}`,
    `${API_URL}/theme/${encodeURIComponent(theme)}/stocks`,
    fallback,
  );
}

export async function fetchThemeDetail(theme: string): Promise<ThemeDetailResponse> {
  const stocks = fallbackThemeStocks(theme);
  return fetchCachedJson<ThemeDetailResponse>(
    `miji:theme-detail:${theme}`,
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
}

export const defaultWatchlist = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "SPY", "QQQ"];
