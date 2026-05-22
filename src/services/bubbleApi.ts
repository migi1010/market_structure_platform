import type { BubbleApiResponse } from "@/types/bubble";
import { fetchStockAnalysis } from "./stockApi";

export async function fetchBubbleAnalysis(ticker: string): Promise<BubbleApiResponse> {
  const stock = await fetchStockAnalysis(ticker);
  return {
    ticker: stock?.ticker ?? ticker.trim().toUpperCase(),
    company_name: stock?.company_name ?? ticker.trim().toUpperCase(),
    price: stock?.price ?? 0,
    sector: stock?.sector ?? "Unknown",
    bubble_analysis_data: stock?.bubble_analysis_data,
  };
}
