import type { SearchResult, SectorRotation, StockAnalysis } from "@/types/stock";

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
];

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchStockAnalysis(ticker: string): Promise<StockAnalysis> {
  const symbol = ticker.trim().toUpperCase();
  const response = await fetch(`/api/analyze?ticker=${encodeURIComponent(symbol)}`, {
    cache: "no-store",
  });
  return readJson<StockAnalysis>(response);
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
    const response = await fetch(`/api/search?q=${encodeURIComponent(normalized)}`, {
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
  const response = await fetch("/api/sector-rotation", { cache: "no-store" });
  return readJson<SectorRotation[]>(response);
}

export const defaultWatchlist = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "PLTR", "SPY", "QQQ"];
