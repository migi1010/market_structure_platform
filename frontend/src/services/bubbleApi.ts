import type { BubbleApiResponse } from "@/types/bubble";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://market-structure-platform.onrender.com";

export async function fetchBubbleAnalysis(ticker: string): Promise<BubbleApiResponse> {
  const symbol = ticker.trim().toUpperCase();
  const response = await fetch(`${API_URL}/bubble/${encodeURIComponent(symbol)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch bubble analysis for ${symbol}`);
  }
  return response.json();
}
