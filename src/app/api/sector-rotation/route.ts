import { NextResponse } from "next/server";
import YahooFinance from "yahoo-finance2";
import { sanitizeCompanyName } from "@/lib/sanitize";

export const dynamic = "force-dynamic";

const yahooFinance = new YahooFinance();

const sectors = [
  { sector: "Technology", etf: "XLK", companies: ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "PLTR"] },
  { sector: "Healthcare", etf: "XLV", companies: ["LLY", "UNH", "JNJ", "MRK", "ABBV", "PFE"] },
  { sector: "Financials", etf: "XLF", companies: ["JPM", "BAC", "GS", "MS", "V", "MA"] },
  { sector: "Energy", etf: "XLE", companies: ["XOM", "CVX", "COP", "SLB", "EOG", "MPC"] },
  { sector: "Industrials", etf: "XLI", companies: ["GE", "CAT", "BA", "HON", "UPS", "RTX"] },
  { sector: "Consumer", etf: "XLY", companies: ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX"] },
  { sector: "Utilities", etf: "XLU", companies: ["NEE", "SO", "DUK", "AEP", "SRE", "D"] },
  { sector: "Real Estate", etf: "XLRE", companies: ["PLD", "AMT", "EQIX", "WELL", "SPG", "O"] },
  { sector: "Semiconductors", etf: "SMH", companies: ["NVDA", "AMD", "AVGO", "TSM", "ASML", "MU"] },
  { sector: "Software", etf: "IGV", companies: ["MSFT", "CRM", "NOW", "ADBE", "ORCL", "SNOW"] },
  { sector: "AI", etf: "BOTZ", companies: ["NVDA", "PLTR", "META", "GOOGL", "TSLA", "AMD"] },
  { sector: "Cybersecurity", etf: "CIBR", companies: ["CRWD", "PANW", "FTNT", "ZS", "OKTA", "S"] },
];

function n(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function clamp(value: number): number {
  return Math.round(Math.min(100, Math.max(0, value)) * 100) / 100;
}

function pct(now: number, then: number): number {
  return then > 0 ? now / then - 1 : 0;
}

async function quote(symbol: string): Promise<any> {
  try {
    return await yahooFinance.quote(symbol);
  } catch {
    return { symbol };
  }
}

async function chart(symbol: string): Promise<Array<{ close: number; volume: number }>> {
  try {
    const result = await yahooFinance.chart(symbol, {
      period1: new Date(Date.now() - 190 * 24 * 60 * 60 * 1000),
      interval: "1d",
    });
    const resultAny = result as unknown as { quotes?: any[] };
    return (resultAny?.quotes ?? [])
      .map((item: any) => ({ close: n(item?.close), volume: n(item?.volume) }))
      .filter((item) => item.close > 0);
  } catch {
    return [];
  }
}

function volatility(closes: number[]): number {
  const returns = closes.slice(1).map((close, index) => pct(close, closes[index]));
  if (returns.length === 0) return 0.35;
  const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / returns.length;
  return Math.sqrt(variance) * Math.sqrt(252);
}

async function metrics(symbol: string, marketMomentum: number) {
  const [q, series] = await Promise.all([quote(symbol), chart(symbol)]);
  const closes = series.map((item) => item.close);
  const volumes = series.map((item) => item.volume).filter((value) => value > 0);
  const latest = closes.at(-1) ?? n(q?.regularMarketPrice);
  const oneMonth = closes.length > 22 ? closes[closes.length - 22] : closes[0] ?? latest;
  const threeMonth = closes.length > 64 ? closes[closes.length - 64] : closes[0] ?? latest;
  const sixMonth = closes[0] ?? latest;
  const momentum1m = pct(latest, oneMonth);
  const momentum3m = pct(latest, threeMonth);
  const momentum6m = pct(latest, sixMonth);
  const acceleration = momentum1m - momentum3m / 3;
  const avgVolume = volumes.length > 0 ? volumes.slice(-60).reduce((sum, value) => sum + value, 0) / Math.min(60, volumes.length) : n(q?.averageDailyVolume3Month) || 1;
  const currentVolume = (volumes.at(-1) ?? n(q?.regularMarketVolume)) || avgVolume;
  const relativeVolume = avgVolume > 0 ? currentVolume / avgVolume : 1;
  const pe = n(q?.trailingPE) || n(q?.forwardPE);
  const ps = n(q?.priceToSalesTrailing12Months);
  const bubbleScore = clamp(38 + Math.max(0, pe - 22) * 0.85 + Math.max(0, ps - 5) * 3 + Math.max(0, momentum1m) * 55 - Math.max(0, momentum3m) * 12);
  return {
    symbol,
    quote: q,
    momentum1m,
    momentum3m,
    momentum6m,
    acceleration,
    relativeStrengthRaw: momentum3m - marketMomentum,
    relativeVolume,
    volatility: volatility(closes),
    marketCap: n(q?.marketCap),
    changePercent: n(q?.regularMarketChangePercent) || momentum1m * 100,
    bubbleScore,
  };
}

function stockAlpha(item: Awaited<ReturnType<typeof metrics>>): number {
  const trend = 50 + item.momentum3m * 170;
  const volume = 50 + (item.relativeVolume - 1) * 22;
  const acceleration = 50 + item.acceleration * 260;
  const momentum = 50 + item.momentum6m * 130;
  const flow = 50 + (item.relativeVolume - 1) * 28 + item.momentum1m * 120;
  const regime = 50 + item.relativeStrengthRaw * 150;
  const bubblePenalty = Math.max(0, item.bubbleScore - 55) * 0.45;
  return clamp(trend * 0.21 + volume * 0.13 + acceleration * 0.14 + momentum * 0.20 + flow * 0.13 + regime * 0.11 + (100 - item.bubbleScore) * 0.08 - bubblePenalty);
}

function sectorStrength(input: {
  momentum3m: number;
  relativeStrengthRaw: number;
  relativeVolume: number;
  capFlow: number;
  volatility: number;
  avgAlpha: number;
  avgBubble: number;
}) {
  const momentum = 50 + input.momentum3m * 190;
  const relative = 50 + input.relativeStrengthRaw * 210;
  const volume = 50 + (input.relativeVolume - 1) * 24;
  const flow = 50 + input.capFlow * 160;
  const stability = 100 - Math.min(100, Math.max(0, input.volatility * 160));
  return clamp(momentum * 0.23 + relative * 0.21 + volume * 0.13 + flow * 0.13 + stability * 0.10 + input.avgAlpha * 0.14 + (100 - input.avgBubble) * 0.06);
}

export async function GET() {
  const spy = await metrics("SPY", 0);
  const marketMomentum = spy.momentum3m;
  const response = await Promise.all(sectors.map(async (sector) => {
    const [etf, companyMetrics] = await Promise.all([
      metrics(sector.etf, marketMomentum),
      Promise.all(sector.companies.map((symbol) => metrics(symbol, marketMomentum))),
    ]);

    const companies = companyMetrics.map((item) => ({
      ticker: item.symbol,
      company_name: sanitizeCompanyName(String(item.quote?.longName ?? item.quote?.shortName ?? item.symbol)),
      market_cap: item.marketCap,
      alpha_score: stockAlpha(item),
      bubble_score: item.bubbleScore,
      relative_strength: clamp(50 + item.relativeStrengthRaw * 180),
      change_percent: Math.round(item.changePercent * 100) / 100,
      sector_rank: 0,
    })).sort((a, b) => b.alpha_score - a.alpha_score).map((company, index) => ({ ...company, sector_rank: index + 1 }));

    const capTotal = companyMetrics.reduce((sum, item) => sum + item.marketCap, 0);
    const capFlow = capTotal > 0
      ? companyMetrics.reduce((sum, item) => sum + item.marketCap * item.momentum1m, 0) / capTotal
      : etf.momentum1m;
    const avgAlpha = companies.reduce((sum, item) => sum + item.alpha_score, 0) / Math.max(1, companies.length);
    const avgBubble = companies.reduce((sum, item) => sum + item.bubble_score, 0) / Math.max(1, companies.length);

    return {
      sector: sector.sector,
      score: sectorStrength({
        momentum3m: etf.momentum3m,
        relativeStrengthRaw: etf.relativeStrengthRaw,
        relativeVolume: etf.relativeVolume,
        capFlow,
        volatility: etf.volatility,
        avgAlpha,
        avgBubble,
      }),
      relative_strength: clamp(50 + etf.relativeStrengthRaw * 180),
      flow: clamp(50 + capFlow * 220),
      companies,
    };
  }));

  return NextResponse.json(response.sort((a, b) => b.score - a.score));
}
