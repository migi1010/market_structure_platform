import type { BubbleAnalysisData } from "./bubble";

export interface AnalystTargets {
  available?: boolean;
  high: number | null;
  average: number | null;
  low: number | null;
  average_target?: number | null;
  implied_upside?: number | null;
  buy: number | null;
  hold: number | null;
  sell: number | null;
}

export interface AnalystConsensus {
  available?: boolean;
  average_target: number | null;
  implied_upside: number | null;
  buy: number | null;
  hold: number | null;
  sell: number | null;
}

export interface HmmPrediction {
  available?: boolean;
  predicted_trend: string;
  bull_probability: number | null;
  bear_probability: number | null;
  regime_state: string;
  confidence: number | null;
  message?: string;
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
  price: number | null;
  change?: number | null;
  change_percent: number | null;
  market_cap: number | null;
  sector: string;
  quote_status?: "live_or_cached" | "unavailable" | string;
  bubble_analysis_data: BubbleAnalysisData;
  analyst_targets: AnalystTargets;
  analyst_consensus?: AnalystConsensus;
  hmm_prediction: HmmPrediction;
  news: NewsItem[];
}

export interface MarketOverviewItem {
  ticker: string;
  price: number;
  change: number;
  change_percent: number;
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
  rotation_state?: string;
  confidence_score?: number;
  confidence_label?: string;
  explanation?: string[];
  fallback?: boolean;
  message?: string;
}

export interface AlphaQuantRow {
  ticker: string;
  company_name: string;
  sector: string;
  alpha_score: number;
  quality: number;
  growth: number;
  smart_money: number;
  valuation: number;
  earnings_quality: number;
  market_structure: number;
  bubble_risk: number;
  sector_alignment: number;
  theme_alignment?: number;
  theme_strength?: number;
  theme_capital_flow?: number;
  theme_explanation?: string[];
  confidence_score?: number;
  confidence_label?: string;
  bullish_factors?: string[];
  risk_factors?: string[];
  suggested_action: "Strong Buy" | "Accumulation" | "Watchlist" | "Hold" | "Bubble Risk" | "Avoid";
  factor_importance: Record<string, number>;
}

export interface AlphaQuantResponse {
  generated_at: string;
  universe: string;
  qlib_engine: {
    available: boolean;
    mode?: "qlib" | "fallback";
    provider: string;
    factor_set: string;
    version?: string;
    reason?: string;
  };
  market_regime: {
    name: string;
    confidence: number;
  };
  factor_importance: Record<string, number>;
  top_alpha: AlphaQuantRow[];
  recommendations: AlphaQuantRow[];
  summary: string;
}

export interface ThemeLeader {
  ticker: string;
  momentum_3m?: number;
  relative_volume?: number;
  day_change_percent?: number;
  change_percent?: number;
  company_name?: string;
  market_cap?: number;
  price?: number;
  role?: string;
  alpha_score?: number | null;
  smart_money?: number | null;
  bubble_risk?: number | null;
  confidence_score?: number;
  confidence_label?: string;
  quote_status?: string;
}

export interface ThemeScore {
  theme: string;
  category: string;
  description?: string;
  theme_strength_score: number;
  theme_capital_flow_score: number;
  emerging_score: number;
  overheating_score: number;
  relative_momentum: number;
  etf_relative_strength: number;
  volume_expansion: number;
  institutional_accumulation: number;
  earnings_acceleration: number;
  revenue_acceleration: number;
  capex_trend: number;
  smart_money_accumulation: number;
  narrative_strength: number;
  narrative_acceleration: number;
  narrative_saturation: number;
  narrative_bubble_risk: number;
  breadth_participation: number;
  leadership_concentration: number;
  relative_strength_vs_spy: number;
  options_activity: number;
  supply_chain_acceleration: number;
  macro_alignment: number;
  leaders: ThemeLeader[];
  related_stocks?: ThemeLeader[];
  top_alpha_stocks?: ThemeLeader[];
  etfs: string[];
  macro_tags: string[];
  explainability: string[];
  risks?: string[];
  status?: "Emerging" | "Accumulating" | "Leadership" | "Overheated" | "Cooling" | "Weak" | "Watchlist" | string;
  confidence_score?: number;
  confidence_label?: string;
  data_completeness?: number;
}

export interface CrossAssetRegime {
  generated_at?: string;
  risk_on_off?: string;
  risk_on_score?: number;
  liquidity_regime?: string;
  liquidity_score?: number;
  volatility_regime?: string;
  volatility_score?: number;
  inflation_regime?: string;
  inflation_score?: number;
  AI_capex_regime?: string;
  AI_capex_score?: number;
}

export interface ThemeTopResponse {
  generated_at: string;
  cross_asset_regime: CrossAssetRegime;
  themes: ThemeScore[];
  summary: string;
}

export interface EmergingThemeResponse {
  generated_at: string;
  emerging_themes: ThemeScore[];
  summary: string;
}

export interface ThemeRotationResponse {
  generated_at: string;
  rotation_map: ThemeScore[];
  strengthening: ThemeScore[];
  weakening: ThemeScore[];
  overheated_themes: ThemeScore[];
  undervalued_themes: ThemeScore[];
  summary: string;
}

export interface ThemeCapitalFlowResponse {
  generated_at: string;
  capital_flow: Array<Partial<ThemeScore> & { theme: string; category: string }>;
  summary: string;
}

export interface ThemeSupplyChainResponse {
  generated_at: string;
  themes: Array<{
    theme: string;
    category: string;
    generated_at: string;
    supply_chain: Record<string, ThemeLeader[]>;
    leaders: ThemeLeader[];
    summary: string;
  }>;
}

export interface ThemeNarrativeResponse {
  generated_at: string;
  narratives: Array<{
    theme: string;
    narrative_strength: number;
    narrative_acceleration: number;
    narrative_saturation: number;
    narrative_bubble_risk: number;
    summary: string;
  }>;
}

export interface ThemeStocksResponse {
  generated_at: string;
  theme: string;
  theme_id: string;
  category?: string;
  description?: string;
  related_stocks: ThemeLeader[];
  top_alpha_stocks: ThemeLeader[];
  summary: string;
  fallback?: boolean;
}

export interface ThemeDetailResponse extends ThemeStocksResponse {
  theme_score?: number | null;
  confidence?: string | null;
  confidence_score?: number | null;
  status?: string | null;
  supply_chain: Record<string, ThemeLeader[]>;
  capital_flow?: number | null;
  bubble_risk?: number | null;
  explainability?: string[];
  risks?: string[];
}
