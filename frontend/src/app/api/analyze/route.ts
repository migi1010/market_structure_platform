import { NextResponse } from "next/server";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import YahooFinance from "yahoo-finance2";
import { sanitizeCompanyName } from "@/lib/sanitize";

export const dynamic = "force-dynamic";

const execFileAsync = promisify(execFile);
const yahooFinance = new YahooFinance();

type NewsCategory = "Earnings" | "AI" | "Regulation" | "Insider Trading" | "M&A" | "Macro" | "General";

function numberValue(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (value && typeof value === "object" && "raw" in value && typeof (value as { raw?: unknown }).raw === "number") {
    return (value as { raw: number }).raw;
  }
  return 0;
}

function statementValue(statement: Record<string, unknown>, keys: string[]): number {
  for (const key of keys) {
    const value = numberValue(statement?.[key]);
    if (value !== 0) return value;
  }
  return 0;
}

function classifyBubble(score: number): "Fundamental Safety" | "Neutral Watch" | "High Bubble Alert" {
  if (score >= 70) return "High Bubble Alert";
  if (score <= 40) return "Fundamental Safety";
  return "Neutral Watch";
}

function calculateBubbleIndex(input: {
  peRatio: number;
  psRatio: number;
  revenueGrowth: number;
  grossMargin: number;
  freeCashFlow: number;
  debtRatio: number;
}): number {
  const peRisk = Math.min(30, Math.max(0, ((input.peRatio || 0) - 20) * 0.9));
  const psRisk = Math.min(22, Math.max(0, ((input.psRatio || 0) - 5) * 3.2));
  const growthPenalty = input.revenueGrowth >= 0.12 ? -8 : input.revenueGrowth >= 0 ? 4 : 14;
  const marginCredit = input.grossMargin >= 0.45 ? -8 : input.grossMargin >= 0.25 ? 0 : 8;
  const fcfRisk = input.freeCashFlow >= 0 ? -8 : 14;
  const debtRisk = input.debtRatio > 0.7 ? 18 : input.debtRatio > 0.45 ? 8 : -4;
  return Math.round(Math.min(100, Math.max(0, 42 + peRisk + psRisk + growthPenalty + marginCredit + fcfRisk + debtRisk)));
}

function categoryForTitle(title: string): NewsCategory {
  const lower = title.toLowerCase();
  if (lower.includes("earnings") || lower.includes("revenue") || lower.includes("profit")) return "Earnings";
  if (lower.includes("ai") || lower.includes("artificial intelligence") || lower.includes("chip")) return "AI";
  if (lower.includes("regulation") || lower.includes("sec") || lower.includes("lawsuit")) return "Regulation";
  if (lower.includes("insider")) return "Insider Trading";
  if (lower.includes("acquire") || lower.includes("merger") || lower.includes("m&a")) return "M&A";
  if (lower.includes("fed") || lower.includes("inflation") || lower.includes("rates")) return "Macro";
  return "General";
}

function sentimentForTitle(title: string): "Bullish" | "Neutral" | "Bearish" {
  const lower = title.toLowerCase();
  if (["beat", "surge", "rally", "upgrade", "growth", "record", "bull"].some((word) => lower.includes(word))) return "Bullish";
  if (["miss", "fall", "drop", "lawsuit", "downgrade", "risk", "bear"].some((word) => lower.includes(word))) return "Bearish";
  return "Neutral";
}

function summaryForTitle(title: string, ticker: string): string {
  const category = categoryForTitle(title);
  return `${ticker} related ${category.toLowerCase()} intelligence detected from live market news. Monitor price reaction, volume confirmation, and analyst revision risk.`;
}

async function safeCall<T>(task: () => Promise<T>): Promise<T | null> {
  try {
    return await task();
  } catch {
    return null;
  }
}

async function runPythonAnalyze(ticker: string): Promise<unknown | null> {
  const projectRoot = path.resolve(process.cwd(), "..");
  const script = [
    "import json, sys",
    "from orchestrator import analyze_stock",
    "print(json.dumps(analyze_stock(sys.argv[1]), ensure_ascii=False))",
  ].join("; ");
  try {
    const { stdout } = await execFileAsync("python", ["-c", script, ticker], {
      cwd: projectRoot,
      timeout: 45000,
      maxBuffer: 1024 * 1024 * 6,
    });
    return JSON.parse(stdout.trim());
  } catch {
    return null;
  }
}

function sanitizeAnalyzePayload(payload: unknown): unknown {
  if (!payload || typeof payload !== "object") return payload;
  const typed = payload as { company_name?: string; ticker?: string; news?: Array<{ title?: string; publisher?: string }> };
  return {
    ...typed,
    company_name: sanitizeCompanyName(typed.company_name ?? typed.ticker ?? ""),
    news: (typed.news ?? []).map((item) => ({
      ...item,
      title: sanitizeCompanyName(item?.title ?? "") || "No News",
      publisher: sanitizeCompanyName(item?.publisher ?? "") || "Yahoo Finance",
    })),
  };
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const ticker = searchParams.get("ticker")?.trim().toUpperCase();

  if (!ticker) {
    return NextResponse.json({ error: "ticker is required" }, { status: 400 });
  }

  try {
    const pythonResult = await runPythonAnalyze(ticker);
    if (pythonResult) return NextResponse.json(sanitizeAnalyzePayload(pythonResult));

    const [quote, modules, newsResult, chart] = await Promise.all([
      safeCall(() => yahooFinance.quote(ticker)),
      safeCall(() => yahooFinance.quoteSummary(ticker, {
        modules: [
          "financialData",
          "defaultKeyStatistics",
          "summaryProfile",
          "price",
          "recommendationTrend",
          "incomeStatementHistory",
          "cashflowStatementHistory",
          "balanceSheetHistory",
        ],
      })),
      safeCall(() => yahooFinance.search(ticker, { newsCount: 8, quotesCount: 0 })),
      safeCall(() => yahooFinance.chart(ticker, { period1: new Date(Date.now() - 120 * 24 * 60 * 60 * 1000), interval: "1d" })),
    ]);

    const quoteAny = quote as Record<string, unknown> | null;
    const modulesAny = modules as Record<string, any> | null;
    const financialData = modulesAny?.financialData ?? {};
    const keyStats = modulesAny?.defaultKeyStatistics ?? {};
    const profile = modulesAny?.summaryProfile ?? {};
    const priceNode = modulesAny?.price ?? {};
    const income = modulesAny?.incomeStatementHistory?.incomeStatementHistory?.[0] ?? {};
    const previousIncome = modulesAny?.incomeStatementHistory?.incomeStatementHistory?.[1] ?? {};
    const cashflow = modulesAny?.cashflowStatementHistory?.cashflowStatements?.[0] ?? modulesAny?.cashflowStatementHistory?.cashflowStatementHistory?.[0] ?? {};
    const balance = modulesAny?.balanceSheetHistory?.balanceSheetStatements?.[0] ?? {};

    const price = numberValue(quoteAny?.regularMarketPrice) || numberValue(priceNode?.regularMarketPrice);
    const revenue = statementValue(income, ["totalRevenue", "Total Revenue"]);
    const previousRevenue = statementValue(previousIncome, ["totalRevenue", "Total Revenue"]);
    const grossProfit = statementValue(income, ["grossProfit", "Gross Profit"]);
    const netIncome = statementValue(income, ["netIncome", "Net Income"]);
    const operatingCashFlow = statementValue(cashflow, ["totalCashFromOperatingActivities", "operatingCashflow", "Operating Cash Flow"]);
    const capitalExpenditures = statementValue(cashflow, ["capitalExpenditures", "Capital Expenditure"]);
    const freeCashFlow = numberValue(financialData?.freeCashflow) || operatingCashFlow + capitalExpenditures;
    const totalAssets = statementValue(balance, ["totalAssets", "Total Assets"]);
    const totalLiabilities = statementValue(balance, ["totalLiab", "totalLiabilitiesNetMinorityInterest", "Total Liabilities Net Minority Interest"]);
    const debtRatio = totalAssets > 0 ? totalLiabilities / totalAssets : 0;
    const grossMargin = revenue > 0 ? grossProfit / revenue : numberValue(financialData?.grossMargins);
    const revenueGrowth = previousRevenue > 0 ? (revenue - previousRevenue) / previousRevenue : numberValue(financialData?.revenueGrowth);
    const peRatio = numberValue(quoteAny?.trailingPE) || numberValue(quoteAny?.forwardPE) || numberValue(keyStats?.trailingPE);
    const psRatio = numberValue(keyStats?.priceToSalesTrailing12Months) || numberValue(quoteAny?.priceToSalesTrailing12Months);
    const bubbleIndex = calculateBubbleIndex({ peRatio, psRatio, revenueGrowth, grossMargin, freeCashFlow, debtRatio });
    const classification = classifyBubble(bubbleIndex);

    const recommendationTrend = modulesAny?.recommendationTrend?.trend?.[0] ?? {};
    const analystTargets = {
      high: numberValue(financialData?.targetHighPrice),
      average: numberValue(financialData?.targetMeanPrice),
      low: numberValue(financialData?.targetLowPrice),
      buy: numberValue(recommendationTrend?.strongBuy) + numberValue(recommendationTrend?.buy),
      hold: numberValue(recommendationTrend?.hold),
      sell: numberValue(recommendationTrend?.sell) + numberValue(recommendationTrend?.strongSell),
    };

    const chartAny = chart as { quotes?: Array<{ close?: number }> } | null;
    const quotes = chartAny?.quotes ?? [];
    const closes = quotes.map((item: { close?: number }) => item?.close ?? 0).filter((value: number) => value > 0);
    const firstClose = closes?.[0] ?? price;
    const lastClose = closes?.[closes.length - 1] ?? price;
    const return120 = firstClose > 0 ? (lastClose - firstClose) / firstClose : 0;
    const dailyReturns = closes.slice(1).map((close: number, index: number) => (closes[index] > 0 ? (close - closes[index]) / closes[index] : 0));
    const volatility = dailyReturns.length > 2 ? Math.sqrt(dailyReturns.reduce((sum: number, value: number) => sum + value * value, 0) / dailyReturns.length) * Math.sqrt(252) : 0.2;
    const bullProbability = Math.min(0.92, Math.max(0.08, 0.5 + return120 * 1.2 - volatility * 0.25));
    const bearProbability = 1 - bullProbability;
    const predictedTrend = bullProbability >= 0.55 ? "Bullish" : bearProbability >= 0.55 ? "Bearish" : "Neutral";
    const hmmPrediction = {
      predicted_trend: predictedTrend,
      bull_probability: Number(bullProbability.toFixed(4)),
      bear_probability: Number(bearProbability.toFixed(4)),
      regime_state: predictedTrend === "Bullish" ? "Momentum Expansion" : predictedTrend === "Bearish" ? "Risk-Off Contraction" : "Range-Bound Equilibrium",
      confidence: Number(Math.min(0.95, Math.max(0.45, Math.abs(bullProbability - 0.5) * 1.6 + 0.45)).toFixed(2)),
    };

    const newsAny = newsResult as { news?: any[] } | null;
    const news = (newsAny?.news ?? []).slice(0, 8).map((item: any) => {
      const title = String(item?.title ?? "No News");
      return {
        title,
        publisher: String(item?.publisher ?? item?.provider ?? "Yahoo Finance"),
        link: String(item?.link ?? "#"),
        provider_publish_time: item?.providerPublishTime ? new Date(item.providerPublishTime * 1000).toISOString() : new Date().toISOString(),
        sentiment: sentimentForTitle(title),
        category: categoryForTitle(title),
        summary: summaryForTitle(title, ticker),
      };
    });

    return NextResponse.json({
      ticker,
      company_name: sanitizeCompanyName(String(quoteAny?.longName ?? quoteAny?.shortName ?? priceNode?.longName ?? ticker)),
      price,
      change_percent: numberValue(quoteAny?.regularMarketChangePercent),
      market_cap: numberValue(quoteAny?.marketCap) || numberValue(priceNode?.marketCap),
      sector: String(profile?.sector ?? "Unknown"),
      bubble_analysis_data: {
        revenue,
        net_income: netIncome,
        gross_margin: grossMargin,
        operating_cash_flow: operatingCashFlow,
        free_cash_flow: freeCashFlow,
        total_assets: totalAssets,
        total_liabilities: totalLiabilities,
        debt_ratio: debtRatio,
        pe_ratio: peRatio,
        ps_ratio: psRatio,
        bubble_index: bubbleIndex,
        classification,
        ai_summary: `${ticker} is classified as ${classification}. Bubble index reflects valuation multiples, revenue growth, margin quality, free cash flow, and leverage risk from live Yahoo Finance statements.`,
      },
      analyst_targets: analystTargets,
      hmm_prediction: hmmPrediction,
      news,
    });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : "analysis failed" }, { status: 500 });
  }
}
