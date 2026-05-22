import type { BubbleAnalysisData } from "./bubble";

export interface AnalystTargets {
  high: number;
  average: number;
  low: number;
  buy: number;
  hold: number;
  sell: number;
}

export interface HmmPrediction {
  predicted_trend: string;
  bull_probability: number;
  bear_probability: number;
  regime_state: string;
  confidence: number;
}

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  provider_publish_time: string;
  sentiment: "Bullish" | "Neutral" | "Bearish";
  category: "Earnings" | "AI" | "Regulation" | "Insider Trading" | "M&A" | "Macro" | "General";
  summary: string;
}

export interface StockAnalysis {
  ticker: string;
  company_name: string;
  price: number;
  change_percent: number;
  market_cap: number;
  sector: string;
  bubble_analysis_data: BubbleAnalysisData;
  analyst_targets: AnalystTargets;
  hmm_prediction: HmmPrediction;
  news: NewsItem[];
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export interface SectorCompany {
  ticker: string;
  company_name: string;
  market_cap: number;
  alpha_score: number;
  bubble_score: number;
  relative_strength: number;
  change_percent: number;
  sector_rank?: number;
}

export interface SectorRotation {
  sector: string;
  score: number;
  relative_strength: number;
  flow: number;
  companies: SectorCompany[];
}
