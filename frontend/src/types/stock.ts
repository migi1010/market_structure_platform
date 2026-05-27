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

export interface StockQuote {
  ticker: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  previous_close?: number | null;
  market_cap: number | null;
  pe_ratio?: number | null;
  ps_ratio?: number | null;
  currency?: string;
  status: string;
  source?: string;
}

export interface StockAnalysis {
  ticker: string;
  company_name: string;
  price: number | null;
  change?: number | null;
  change_percent: number | null;
  market_cap: number | null;
  canonicalPrice: number | null;
  canonicalChange: number | null;
  canonicalChangePercent: number | null;
  canonicalMarketCap: number | null;
  canonicalQuoteStatus: string;
  canonicalSector: string;
  sector: string;
  quote_status?: "live_or_cached" | "unavailable" | string;
  /** Backend lifecycle state embedded in every /stock/ response. */
  lifecycle_state?: "cold_start" | "warming" | "partial_live" | "live" | "degraded" | "recovery" | string;
  quote?: StockQuote;
  bubble_analysis_data: BubbleAnalysisData;
  earnings_quality?: Record<string, unknown>;
  smart_money?: Record<string, unknown>;
  analyst_targets: AnalystTargets;
  analyst_consensus?: AnalystConsensus;
  hmm_prediction: HmmPrediction;
  news: NewsItem[];
}

export interface MarketOverviewItem {
  ticker: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  quote_status?: string;
}

export type OmniboxIntent = "ticker" | "theme" | "sector" | "command" | "natural_language";
export type OmniboxGroup = "Stocks" | "Themes" | "Sectors" | "Commands";
export type OmniboxTargetTab = "theme-intelligence" | "portfolio" | "alpha-quant" | "market-intel" | "stock-analysis";
export type WorkspaceActionType = "open_stock" | "open_theme" | "open_sector" | "open_alpha" | "open_portfolio" | "open_module";
export type WorkspaceOpenMode = "replace" | "focus" | "background";

export interface WorkspaceAction {
  actionType: WorkspaceActionType;
  target_tab: OmniboxTargetTab;
  focusTarget?: string;
  openMode?: WorkspaceOpenMode;
  contextPayload?: {
    ticker?: string;
    theme?: string;
    sector?: string;
    alphaView?: string;
    portfolioView?: string;
    label?: string;
  };
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
  id?: string;
  label?: string;
  description?: string;
  company?: string;
  theme?: string;
  sector?: string;
  etf?: string;
  command?: string;
  ticker?: string;
  intent?: OmniboxIntent;
  group?: OmniboxGroup;
  target_tab?: OmniboxTargetTab;
  actionType?: WorkspaceActionType;
  focusTarget?: string;
  contextPayload?: WorkspaceAction["contextPayload"];
  openMode?: WorkspaceOpenMode;
  workspaceAction?: WorkspaceAction;
  price?: number | null;
  change_percent?: number | null;
  quote_status?: string;
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
  sector_rank?: number;
  leadership_state?: string;
  momentum_direction?: string;
  participation_strength?: number;
  lifecycle_state?: string;
  capital_rotation?: string;
  narrative_state?: string;
  acceleration_velocity?: number;
  participation_breadth?: number;
  institutional_alignment?: number;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
  narrative_intelligence?: NarrativeIntelligence;
  universe_ranking?: UniverseScreenerRow;
  leadership_intelligence?: {
    sector_rank?: number;
    leadership_state?: string;
    momentum_direction?: string;
    participation_strength?: number;
    confidence?: number;
    confidence_label?: string;
    lifecycle_state?: string;
    explanation?: string;
  };
}

export interface AlphaQuantRow {
  ticker: string;
  company_name: string;
  sector: string;
  price?: number | null;
  change?: number | null;
  change_percent?: number | null;
  quote_status?: string;
  alpha_score: number;
  base_alpha_score?: number;
  universe_context_score?: number;
  universe_adjustment?: number;
  universe_percentile?: number;
  rank_in_universe?: number;
  universe?: string;
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
  universe_ranking?: UniverseScreenerRow;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
}

export interface AlphaQuantResponse {
  generated_at: string;
  universe: string;
  qlib_engine: {
    available: boolean;
    /**
     * "qlib"          — Microsoft Qlib is installed and active.
     * "live_pipeline" — Qlib not installed; Alpha158-compatible pipeline ran successfully.
     * "fallback"      — True fallback (_fallback_alpha); all scores are neutral placeholders.
     */
    mode?: "qlib" | "live_pipeline" | "fallback";
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
  universe_screener?: UniverseRankingResponse;
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
  change?: number | null;
  role?: string;
  alpha_score?: number | null;
  smart_money?: number | null;
  bubble_risk?: number | null;
  confidence_score?: number;
  confidence_label?: string;
  quote_status?: string;
  quote?: StockQuote;
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
  theme_id?: string;
  leadership_score?: number | null;
  acceleration_score?: number;
  participation_score?: number;
  lifecycle_state?: string;
  narrative_state?: string;
  acceleration_velocity?: number;
  participation_breadth?: number;
  institutional_alignment?: number;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
  narrative_intelligence?: NarrativeIntelligence;
  universe_ranking?: UniverseScreenerRow;
  leadership_intelligence?: {
    theme_id: string;
    theme_name: string;
    leadership_score: number | null;
    acceleration_score: number;
    participation_score: number;
    participating_sectors: string[];
    representative_symbols: string[];
    confidence: number;
    confidence_label: string;
    lifecycle_state: string;
    status: string;
    explanation: string;
    capital_rotation: string;
  };
}

export interface NarrativeIntelligence {
  narrative_id: string;
  narrative_name: string;
  theme?: string;
  narrative_strength: number;
  narrative_acceleration?: number;
  narrative_saturation?: number;
  narrative_bubble_risk?: number;
  acceleration_velocity: number;
  participation_breadth: number;
  institutional_alignment: number;
  narrative_state: string;
  representative_themes: string[];
  representative_symbols: string[];
  confidence: number;
  confidence_label?: string;
  lifecycle_state: string;
  explanation: string;
  capital_flow_semantics?: string;
  summary?: string;
  source?: string;
  status?: string;
}

export interface UniverseScreenerRow {
  symbol: string;
  company_name: string;
  entity_type?: string;
  overall_rank?: number | null;
  ranking_score: number | null;
  confidence?: number | null;
  confidence_label?: string;
  lifecycle_state: string;
  narrative_strength?: number | null;
  momentum_strength?: number | null;
  sector_leadership?: number | null;
  institutional_alignment?: number | null;
  participation_breadth?: number | null;
  volatility_quality?: number | null;
  crowding_risk?: number | null;
  defensive_rotation?: number | null;
  risk_state?: string;
  crowding_state?: string;
  market_classification: string;
  explanation: string;
  status?: string;
  source?: string;
}

export interface UniverseRankingResponse {
  generated_at: string;
  status?: string;
  lifecycle_state?: string;
  screener: UniverseScreenerRow[];
  strongest_leadership?: UniverseScreenerRow[];
  accelerating?: UniverseScreenerRow[];
  emerging?: UniverseScreenerRow[];
  weakening?: UniverseScreenerRow[];
  crowded?: UniverseScreenerRow[];
  defensive?: UniverseScreenerRow[];
  risk_on?: UniverseScreenerRow[];
  risk_off?: UniverseScreenerRow[];
  summary?: string;
  future_hooks?: string[];
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
  status?: string;
  lifecycle_state?: string;
  top_narratives?: NarrativeIntelligence[];
  emerging_narratives?: NarrativeIntelligence[];
  weakening_narratives?: NarrativeIntelligence[];
  crowded_narratives?: NarrativeIntelligence[];
  defensive_narratives?: NarrativeIntelligence[];
  narratives: NarrativeIntelligence[];
  universe_ranking?: UniverseRankingResponse;
  summary?: string;
  future_hooks?: string[];
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
