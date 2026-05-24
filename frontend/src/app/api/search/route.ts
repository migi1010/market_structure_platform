import { NextResponse } from "next/server";
import YahooFinance from "yahoo-finance2";
import { sanitizeCompanyName } from "@/lib/sanitize";

export const dynamic = "force-dynamic";

const yahooFinance = new YahooFinance();

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q")?.trim().toUpperCase();
  if (!query) return NextResponse.json([]);

  try {
    const result = await yahooFinance.search(query, { quotesCount: 8, newsCount: 0 });
    const resultAny = result as unknown as { quotes?: any[] };
    const quotes = (resultAny?.quotes ?? [])
      .map((quote: any) => ({
        symbol: String(quote?.symbol ?? "").toUpperCase(),
        name: sanitizeCompanyName(String(quote?.shortname ?? quote?.longname ?? quote?.name ?? quote?.symbol ?? "")),
        exchange: String(quote?.exchange ?? quote?.exchDisp ?? "US"),
        type: String(quote?.quoteType ?? "Equity"),
      }))
      .filter((quote) => quote.symbol.length > 0);
    return NextResponse.json(quotes);
  } catch {
    return NextResponse.json([{ symbol: query, name: query, exchange: "US", type: "Equity" }]);
  }
}
