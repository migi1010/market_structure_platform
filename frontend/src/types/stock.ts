import type { BubbleAnalysisData } from "./bubble";

export interface AnalystTargets {
  available?: boolean;
  high?: number | null;
  high_target?: number | null;
  average?: number | null;
  average_target?: number | null;
  low?: number | null;
  low_target?: number | null;
  implied_upside?: number | null;
  buy?: number | null;
  hold?: number | null;
  sell?: number | null;
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
  fetched_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  cache_age_seconds?: number | null;
  is_stale?: boolean;
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
  source?: string;
  fetched_at?: string | null;
  updated_at?: string | null;
  expires_at?: string | null;
  cache_age_seconds?: number | null;
  is_stale?: boolean;
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
  lifecycle_state?: string;
  reason?: string;
}

export interface MarketOverviewResponse {
  generated_at?: string;
  overview_status?: "live" | "partial_live" | "degraded" | "unavailable" | string;
  lifecycle_state?: "live" | "partial_live" | "degraded" | "unavailable" | string;
  degraded_sections?: string[];
  timing_ms?: Record<string, number>;
  items: MarketOverviewItem[];
}

export type OmniboxIntent = "ticker" | "theme" | "sector" | "command" | "natural_language";
export type OmniboxGroup = "Stocks" | "Themes" | "Sectors" | "Commands";
export type OmniboxTargetTab =
  | "theme-intelligence"
  | "theme-scout"
  | "theme-forecast"
  | "market-intel"
  | "theme-stocks"
  | "theme-supply-chain"
  | "theme-risk"
  | "portfolio"
  | "alpha-quant"
  | "stock-analysis";
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
    themeView?: string;
    sector?: string;
    supplyChainNode?: string;
    scoutCandidate?: string;
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

export type ThemeScoutLifecycle =
  | "DISCOVERED"
  | "OBSERVING"
  | "VALIDATING"
  | "APPROVED"
  | "REJECTED";

export interface ThemeScoutMetrics {
  confidence: number;
  novelty: number;
  velocity: number;
  breadth: number;
  capital: number;
  bottleneck: number;
  serendipity: number;
  theme_score: number;
  coverage: number;
  raw_values?: Record<string, unknown>;
  normalized_values?: Record<string, number>;
  applied_weights?: Record<string, number>;
}

export interface ThemeScoutReadiness {
  technology: number;
  process: number;
  material: number;
  equipment: number;
  constraint: number;
  company: number;
  overall: number;
}

export interface ThemeScoutEvidence {
  evidence_id: string;
  source_table: string;
  source_record_id: string;
  source_type: string;
  source_timestamp: string;
  source_identifier: string;
  citation: string;
  domain_type: string;
  cluster_key: string;
  availability_state: "available";
}

export interface ThemeScoutPath {
  path_type: string;
  label: string;
  evidence_ids: string[];
  steps: Array<Record<string, unknown>>;
}

export interface ThemeScoutInfluence {
  target_type: string;
  target_label: string;
  evidence_ids: string[];
  cluster_keys: string[];
  hypothesis_state: "hypothesis";
}

export interface ThemeScoutCandidate {
  candidate_key: string;
  name: string;
  description: string;
  status: ThemeScoutLifecycle;
  metrics: ThemeScoutMetrics;
  readiness: ThemeScoutReadiness;
  evidence: ThemeScoutEvidence[];
  signal_clusters: Array<{
    cluster_key: string;
    label: string;
    evidence_ids: string[];
  }>;
  paths: ThemeScoutPath[];
  influence_map: ThemeScoutInfluence[];
  rank: number;
  generated_summary: string;
  signal_count: number;
  evidence_count: number;
  source_count: number;
}

export interface ThemeScoutResponse {
  available: boolean;
  snapshot: {
    scout_version: string;
    algorithm_version: string;
    provider_name: string;
    provider_model: string;
    prompt_version: string;
    source_watermark: string;
    evidence_bundle_checksum?: string;
    proposal_checksum?: string;
    checksum: string;
    candidate_count: number;
    status: string;
    activated_at: string | null;
  } | null;
  candidates: ThemeScoutCandidate[];
}

export type ResearchPipelineStatus =
  | "DISCOVERED"
  | "OBSERVING"
  | "RESEARCHING"
  | "VALIDATING"
  | "REVIEW_READY"
  | "APPROVED_RESEARCH"
  | "MONITORING"
  | "ARCHIVED";

export type ResearchPipelineSourceType = "SCOUT_CANDIDATE" | "THEME";
export type ResearchPipelineLinkedType =
  | "SCOUT_CANDIDATE"
  | "THEME"
  | "SUPPLY_CHAIN_VALIDATION"
  | "GRAPH_SNAPSHOT"
  | "CONTROLLER"
  | "OPPORTUNITY"
  | "DECISION_PACKET";

export interface ResearchPipelineCase {
  case_id: string;
  source_type: ResearchPipelineSourceType | string;
  source_id: string;
  theme_id: string;
  title: string;
  status: ResearchPipelineStatus;
  created_at: string;
  updated_at: string;
  activated_at: string | null;
  archived_at: string | null;
  lineage_checksum: string;
}

export interface ResearchPipelineEvent {
  event_id: string;
  case_id: string;
  previous_status: ResearchPipelineStatus | null;
  new_status: ResearchPipelineStatus;
  reason: string;
  created_at: string;
}

export interface ResearchPipelineLink {
  link_id: string;
  case_id: string;
  linked_type: ResearchPipelineLinkedType | string;
  linked_id: string;
  created_at: string;
}

export interface ResearchPipelineProgress {
  percent: number;
  sections: {
    theme_narrative: boolean;
    supply_chain_validation: boolean;
    controller_review: boolean;
    opportunity_review: boolean;
    decision_packet_link: boolean;
  };
}

export interface ResearchPipelineCaseDetail {
  case: ResearchPipelineCase;
  timeline: ResearchPipelineEvent[];
  links: ResearchPipelineLink[];
  progress: ResearchPipelineProgress;
}

export interface ResearchPipelineCaseSummary extends ResearchPipelineCase {
  progress: ResearchPipelineProgress;
  linked_artifact_count: number;
  event_count: number;
}

export interface ResearchPipelineResponse {
  available: boolean;
  cases: ResearchPipelineCaseSummary[];
  details: ResearchPipelineCaseDetail[];
}

export interface DecisionIntelligenceLineage {
  scout_candidate_id: string | null;
  research_case_id: string;
  theme_id: string;
  graph_snapshot_id: number | null;
  controller_snapshot_id: number | string | null;
  opportunity_snapshot_id: number | string | null;
  decision_packet_family_version: string | null;
  decision_packet_family_revision: number | null;
  evidence_ids: string[];
}

export type DecisionIntelligenceSectionKey =
  | "summary"
  | "bull_case"
  | "bear_case"
  | "evidence_strength"
  | "research_gaps"
  | "monitoring_triggers"
  | "scenario_matrix"
  | "open_questions"
  | "lineage";

export type DecisionIntelligenceRow = Record<string, unknown>;

export interface DecisionIntelligencePacket {
  packet_id: string;
  title: string;
  theme_id: string;
  status: string;
  checksum: string;
  sections: Record<DecisionIntelligenceSectionKey, DecisionIntelligenceRow[]>;
  lineage: DecisionIntelligenceLineage;
  answers: {
    currently_known: DecisionIntelligenceRow[];
    still_unknown: DecisionIntelligenceRow[];
    supporting_evidence: DecisionIntelligenceRow[];
    invalidation_conditions: DecisionIntelligenceRow[];
  };
}

export interface DecisionIntelligenceSummary {
  packet_id: string;
  title: string;
  theme_id: string;
  status: string;
  checksum: string;
  lineage: DecisionIntelligenceLineage;
  section_count: number;
}

export interface DecisionIntelligenceResponse {
  available: boolean;
  packets: DecisionIntelligenceSummary[];
  details: DecisionIntelligencePacket[];
}

export interface DecisionIntelligenceDetailResponse {
  available: boolean;
  packet: DecisionIntelligencePacket;
}

export type ForecastHorizon = "1w" | "1m" | "3m";

export interface ThemeForecastRecord {
  theme: string;
  forecast_horizon: ForecastHorizon | string;
  forecast_score: number | null;
  expected_excess_return: number | null;
  outperformance_probability: number | null;
  confidence: number;
  lifecycle_state: string;
  risk_state: string;
  crowding_state: string;
  forecast_label: string;
  explanation: string;
  top_positive_drivers: string[];
  top_negative_drivers: string[];
  regime_context?: Record<string, unknown>;
  feature_snapshot?: Record<string, unknown>;
}

export interface ThemeForecastResponse {
  available: boolean;
  status: string;
  lifecycle_state: string;
  horizon: ForecastHorizon | string;
  generated_at?: string;
  regime_context?: Record<string, unknown>;
  top_future_themes: ThemeForecastRecord[];
  emerging_themes: ThemeForecastRecord[];
  weakening_themes: ThemeForecastRecord[];
  crowded_themes: ThemeForecastRecord[];
  defensive_rotation: ThemeForecastRecord[];
  forecasts: ThemeForecastRecord[];
  message?: string;
}

export interface ThemeForecastValidationResponse {
  horizon: ForecastHorizon | string;
  status: string;
  lifecycle_state: string;
  observations: number;
  hit_rate: number | null;
  precision_at_5: number | null;
  information_ratio: number | null;
  max_drawdown: number | null;
  calibration_quality: number | null;
  turnover: number | null;
  excess_return_stability: number | null;
  confusion_matrix: Record<string, Record<string, number>>;
  walk_forward: Record<string, unknown>;
  reason?: string | null;
}

export interface SectorCompany {
  ticker: string;
  company_name: string;
  market_cap?: number | null;
  alpha_score?: number | null;
  bubble_score?: number | null;
  relative_strength?: number | null;
  change_percent?: number | null;
  sector_rank?: number;
}

export interface SectorRotation {
  id?: string;
  name?: string;
  type?: "sector" | "theme" | "industry" | "etf";
  sector: string;
  sector_id?: string;
  etf?: string;
  score: number | null | undefined;
  sector_score?: number | null;
  relative_strength: number | null | undefined;
  flow: number | null | undefined;
  leadership?: number | null;
  momentum?: number | null;
  participation?: number | null;
  acceleration?: number | null;
  sector_strength?: number | null;
  leadership_score?: number | null;
  momentum_20d?: number | null;
  momentum_60d?: number | null;
  relative_strength_spy?: number | null;
  relative_strength_qqq?: number | null;
  volatility_quality?: number | null;
  volume_participation?: number | null;
  trend_consistency?: number | null;
  companies: SectorCompany[];
  rotation_state?: string;
  trend?: string;
  evidence_source?: string | null;
  updated_at?: string | null;
  linked_themes?: string[];
  rotation_score?: number | null;
  rotation_momentum?: number | null;
  rotation_relative_strength?: number | null;
  rotation_flow_quality?: number | null;
  rotation_confidence?: number | null;
  confidence_score?: number | null;
  confidence_label?: string;
  explanation?: string[];
  fallback?: boolean;
  message?: string;
  status?: string;
  sector_rank?: number;
  leadership_state?: string;
  momentum_direction?: string;
  participation_strength?: number | null;
  lifecycle_state?: string;
  capital_rotation?: string;
  narrative_state?: string;
  acceleration_velocity?: number | null;
  participation_breadth?: number | null;
  institutional_alignment?: number | null;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
  narrative_intelligence?: NarrativeIntelligence;
  universe_ranking?: UniverseScreenerRow;
  leadership_intelligence?: {
    sector_rank?: number;
    leadership_state?: string;
    momentum_direction?: string;
    participation_strength?: number | null;
    confidence?: number | null;
    confidence_label?: string;
    lifecycle_state?: string;
    explanation?: string;
  };
}

export type RotationStatus = "live" | "cached" | "stale" | "partial" | "unavailable";

export interface RotationSelectedSector {
  sector: string;
  sector_id: string;
  leadership: number | null;
  momentum: number | null;
  flow: number | null;
  related_themes: string[];
  risk_overlay: number | null;
  updated_at: string | null;
  status: RotationStatus;
  rotation_score: number | null;
  rotation_momentum: number | null;
  rotation_relative_strength: number | null;
  rotation_flow_quality: number | null;
  rotation_confidence: number | null;
}

export interface RotationDiagnosticRecord {
  id: string;
  label: string;
  value: string | number | null;
  status: RotationStatus;
}

export interface RotationSnapshotResponse {
  status: RotationStatus;
  source: string;
  updated_at: string | null;
  market_regime: string;
  risk_appetite: string;
  volatility_state: string;
  rotation_bias: string;
  leaders: SectorRotation[];
  laggards: SectorRotation[];
  sector_ranking: SectorRotation[];
  selected_sector: RotationSelectedSector | null;
  diagnostics: RotationDiagnosticRecord[];
  theme_links: Array<Record<string, unknown>>;
  data_quality: {
    available_sectors: number;
    unavailable_sectors?: number;
    stale_sectors?: number;
    total_sectors: number;
    benchmark_available?: boolean;
    coverage_ratio?: number;
    underlying_status?: string;
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
  alpha_score: number | null;
  score?: number | null;
  flow?: number | null;
  relative_strength?: number | null;
  leadership?: number | null;
  momentum?: number | null;
  participation?: number | null;
  acceleration?: number | null;
  base_alpha_score?: number | null;
  universe_context_score?: number | null;
  universe_adjustment?: number | null;
  universe_percentile?: number | null;
  rank_in_universe?: number;
  universe?: string;
  quality: number | null;
  growth: number | null;
  smart_money: number | null;
  valuation: number | null;
  earnings_quality: number | null;
  market_structure: number | null;
  bubble_risk: number | null;
  sector_alignment: number | null;
  theme_alignment?: number | null;
  theme_strength?: number | null;
  theme_capital_flow?: number | null;
  momentum_20d?: number | null;
  momentum_60d?: number | null;
  relative_strength_spy?: number | null;
  relative_strength_qqq?: number | null;
  volatility_quality?: number | null;
  volume_participation?: number | null;
  drawdown_pressure?: number | null;
  trend_consistency?: number | null;
  theme_explanation?: string[];
  confidence_score?: number | null;
  confidence_label?: string;
  bullish_factors?: string[];
  risk_factors?: string[];
  suggested_action: "Strong Buy" | "Accumulation" | "Watchlist" | "Hold" | "Bubble Risk" | "Avoid";
  factor_importance: Record<string, number>;
  universe_ranking?: UniverseScreenerRow;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
  lifecycle_state?: string;
  lightweight_factors?: FactorResult[];
}

export interface FactorResult {
  factor_id: string;
  score: number | null;
  confidence?: number | null;
  status?: string;
  source?: string;
  freshness?: string;
  explanation?: string;
  lifecycle_state?: string;
}

export interface AlphaQuantResponse {
  generated_at: string;
  universe: string;
  qlib_engine: {
    available: boolean;
    /**
     * "qlib"          — Microsoft Qlib is installed and active.
     * "live_pipeline" — Qlib not installed; Alpha158-compatible pipeline ran successfully.
     * "fallback"      — Endpoint fallback; score fields remain null until finite live inputs arrive.
     */
    mode?: "qlib" | "live_pipeline" | "fallback";
    provider: string;
    factor_set: string;
    version?: string;
    reason?: string;
  };
  market_regime: {
    name: string;
    confidence: number | null;
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
  theme_strength_score: number | null;
  score?: number | null;
  flow?: number | null;
  relative_strength?: number | null;
  leadership?: number | null;
  momentum?: number | null;
  participation?: number | null;
  acceleration?: number | null;
  theme_capital_flow_score: number | null;
  emerging_score: number | null;
  overheating_score: number | null;
  relative_momentum: number | null;
  etf_relative_strength: number | null;
  volume_expansion: number | null;
  institutional_accumulation: number | null;
  earnings_acceleration: number | null;
  revenue_acceleration: number | null;
  capex_trend: number | null;
  smart_money_accumulation: number | null;
  narrative_strength: number | null;
  narrative_acceleration: number | null;
  narrative_saturation: number | null;
  narrative_bubble_risk: number | null;
  breadth_participation: number | null;
  leadership_concentration: number | null;
  relative_strength_vs_spy: number | null;
  relative_strength_qqq?: number | null;
  momentum_strength?: number | null;
  trend_consistency?: number | null;
  sector_leadership?: number | null;
  options_activity: number | null;
  supply_chain_acceleration: number | null;
  macro_alignment: number | null;
  leaders: ThemeLeader[];
  related_stocks?: ThemeLeader[];
  top_alpha_stocks?: ThemeLeader[];
  etfs: string[];
  macro_tags: string[];
  explainability: string[];
  risks?: string[];
  status?: "Emerging" | "Accumulating" | "Leadership" | "Overheated" | "Cooling" | "Weak" | "Watchlist" | string;
  confidence_score?: number | null;
  confidence_label?: string;
  data_completeness?: number;
  theme_id?: string;
  leadership_score?: number | null;
  acceleration_score?: number | null;
  participation_score?: number | null;
  lifecycle_state?: string;
  narrative_state?: string;
  acceleration_velocity?: number | null;
  participation_breadth?: number | null;
  institutional_alignment?: number | null;
  ranking_score?: number | null;
  overall_rank?: number | null;
  market_classification?: string;
  narrative_intelligence?: NarrativeIntelligence;
  universe_ranking?: UniverseScreenerRow;
  leadership_intelligence?: {
    theme_id: string;
    theme_name: string;
    leadership_score: number | null;
    acceleration_score: number | null;
    participation_score: number | null;
    participating_sectors: string[];
    representative_symbols: string[];
    confidence: number | null;
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
  narrative_strength: number | null;
  score?: number | null;
  flow?: number | null;
  relative_strength?: number | null;
  leadership?: number | null;
  momentum?: number | null;
  participation?: number | null;
  acceleration?: number | null;
  narrative_acceleration?: number | null;
  narrative_saturation?: number | null;
  narrative_bubble_risk?: number | null;
  acceleration_velocity: number | null;
  participation_breadth: number | null;
  institutional_alignment: number | null;
  narrative_state: string;
  representative_themes: string[];
  representative_symbols: string[];
  confidence: number | null;
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

export interface ThemeScoreRecord {
  theme: string;
  theme_id: string;
  ai_potential_score: number | null;
  research_importance: number | null;
  allocation_readiness: number | null;
  risk_adjusted_score: number | null;
  conviction_level: string;
  score_components?: Record<string, unknown>;
  why_high_score?: string;
  why_low_score?: string;
  major_strengths?: string[];
  major_risks?: string[];
  allocation_notes?: string[];
  conviction_reason?: string;
  updated_at?: string;
}

export interface ThemeScoresResponse {
  themes: ThemeScoreRecord[];
  rankings?: {
    top_ai_themes?: ThemeScoreRecord[];
    top_emerging_themes?: ThemeScoreRecord[];
    highest_conviction?: ThemeScoreRecord[];
    highest_research_priority?: ThemeScoreRecord[];
    best_risk_adjusted?: ThemeScoreRecord[];
  };
  source_status?: Record<string, unknown>;
}

export interface ThemeDiscoveryBrief {
  why_now?: string;
  signals?: string[];
  risks?: string[];
  watch_triggers?: string[];
}

export interface ThemeDiscoveryRecord {
  theme_id: string;
  name: string;
  name_zh?: string;
  ai_score: number | null;
  final_ai_score?: number | null;
  discovery_score: number | null;
  emerging_score: number | null;
  catalyst_score: number | null;
  entity_strength_score: number | null;
  confidence_score: number | null;
  crowding_proxy?: number | null;
  lifecycle_stage?: string;
  lifecycle_confidence?: number | null;
  expected_next_stage?: string;
  time_window?: string;
  key_catalysts?: ThemeCatalystRecord[];
  beneficiaries?: ThemeBeneficiaryRecord[];
  brief?: ThemeDiscoveryBrief;
}

export interface ThemeDiscoveryResponse {
  themes: ThemeDiscoveryRecord[];
  source_status?: Record<string, unknown>;
}

export interface ThemeCatalystRecord {
  name?: string;
  catalyst_name?: string;
  type?: string;
  catalyst_type?: string;
  source?: string;
  description?: string;
  impact_score?: number | null;
  confidence_score?: number | null;
  novelty_score?: number | null;
  duration_score?: number | null;
  stage_relevance?: number | null;
  catalyst_strength?: number | null;
  timeline_status?: "past" | "current" | "future" | string;
  polarity?: "positive" | "risk" | "neutral" | string;
  cluster_key?: string;
  updated_at?: string;
}

export interface ThemeBottleneckRecord {
  name?: string;
  bottleneck_name?: string;
  type?: string;
  bottleneck_type?: string;
  severity_score?: number | null;
  duration_score?: number | null;
  resolution_probability?: number | null;
  impact_score?: number | null;
  bottleneck_strength?: number | null;
  timeline_status?: string;
  description?: string;
  controllers?: Array<Record<string, unknown>>;
  beneficiaries?: Array<Record<string, unknown>>;
  what_fixes_it?: string[];
  what_to_monitor?: string[];
  evidence?: Record<string, unknown>[];
  updated_at?: string;
}

export interface ThemeBeneficiaryRecord {
  ticker: string;
  company?: string;
  company_name?: string;
  beneficiary_type?: string;
  beneficiary_score?: number | null;
  allocation_score?: number | null;
  allocation_bucket?: string;
  relationship_strength?: number | null;
  role?: string;
  updated_at?: string;
}

export interface ThemePortfolioTheme {
  theme?: string;
  theme_id: string;
  weight: number | null;
  allocation_rationale?: string;
}

export interface ThemePortfolioRecord {
  portfolio_type: string;
  portfolio_name: string;
  portfolio_score: number | null;
  risk_profile?: string;
  lifecycle_mix?: Record<string, number>;
  bubble_exposure?: number | null;
  allocation_quality?: number | null;
  themes?: ThemePortfolioTheme[];
  explanation?: string;
  risk_notes?: string[];
  updated_at?: string;
}

export interface ThemePortfolioResponse {
  portfolios: ThemePortfolioRecord[];
  rankings?: Record<string, ThemePortfolioRecord[]>;
  source_status?: Record<string, unknown>;
}

export interface ThemeAggregateLifecycle {
  theme_id: string;
  name: string;
  lifecycle_stage: string | null;
  lifecycle_confidence: number | null;
  expected_next_stage: string | null;
  time_window?: string | null;
  stage_reason?: string | null;
  source?: string | null;
  history?: Array<Record<string, unknown>>;
}

export interface ThemeAggregateSupplyEntity {
  ticker: string;
  company: string;
  role: string;
  strength: number;
  is_bottleneck_controller: boolean;
}

export interface ThemeAggregateSupplyLayer {
  layer_id: string;
  layer_name: string;
  entities: ThemeAggregateSupplyEntity[];
  has_bottleneck: boolean;
}

export interface ThemeAggregateSupplyChain {
  layers: ThemeAggregateSupplyLayer[];
  bottleneck_controllers: string[];
  dependency_paths: Array<{
    path: string;
    strength: number | null;
    explanation?: string;
    risk?: string;
  }>;
  risks: Array<{
    risk_type: string;
    value: number | null;
    explanation?: string;
  }>;
  resolutions: Array<{
    resolution: string;
    resolution_probability: number | null;
    impact: number | null;
    timeline?: string;
  }>;
}

export interface ThemeRelationshipRecord {
  theme_id: string;
  related_theme_id: string;
  overlap_score: number | null;
  components: {
    beneficiary_overlap: number | null;
    controller_overlap: number | null;
    bottleneck_overlap: number | null;
    catalyst_overlap: number | null;
    portfolio_overlap: number | null;
  };
  shared_beneficiaries: string[];
  shared_controllers: string[];
  shared_bottlenecks: string[];
  shared_catalysts: string[];
  shared_portfolios: string[];
  shared_supply_chain_roles: string[];
}

export interface ThemeRelationshipIntelligence {
  related_themes: ThemeRelationshipRecord[];
  shared_controllers: string[];
  shared_beneficiaries: string[];
  portfolio_exposure: string[];
  shared_supply_chain_roles: string[];
}

export interface ThemeIndustrialNode {
  node_type: string;
  canonical_key: string;
  display_name: string;
  aliases: string[];
  external_ids: Record<string, unknown>;
}

export interface ThemeIndustrialEdge {
  source_type: string;
  source_key: string;
  relationship_type: string;
  target_type: string;
  target_key: string;
  evidence_ids: number[];
}

export interface ThemeIndustrialPath {
  path_id?: string;
  depth: number;
  nodes: ThemeIndustrialNode[];
  edges?: ThemeIndustrialEdge[];
  evidence_ids?: number[];
}

export interface ThemeIndustrialConstraint {
  canonical_key: string;
  display_name: string;
  constraint_type?: string | null;
  severity: number | null;
  evidence_count: number;
  resolution_state: string;
  resolver_company_keys: string[];
  exposed_company_keys: string[];
  severity_source?: string | null;
  coverage: number | null;
}

export interface ThemeIndustrialController {
  company_key: string;
  company_name: string;
  rank: number | null;
  controller_score: number | null;
  coverage: number | null;
  coverage_confidence: number | null;
  controller_types: string[];
  evidence_count: number;
  evidence_ids: number[];
  reasoning_paths: ThemeIndustrialPath[];
}

export interface ThemeIndustrialOpportunity {
  company_key: string;
  company_name: string;
  rank: number | null;
  opportunity_score: number | null;
  coverage_confidence: number | null;
  coverage_component: number | null;
  controller_contribution: number | null;
  constraint_contribution: number | null;
  opportunity_types: string[];
  evidence_count: number;
  evidence_ids: number[];
  availability_states: Record<string, string>;
  reasoning_paths: ThemeIndustrialPath[];
}

export interface ThemeIndustrialPacketSummary {
  family: Record<string, unknown> | null;
  theme_packet: Record<string, unknown> | null;
  matching_packets: Array<Record<string, unknown>>;
}

export interface ThemeIndustrialCoverageMetric {
  numerator: number;
  denominator: number;
  coverage: number;
  availability_state: string;
}

export interface ThemeIndustrialIntelligence {
  identity: {
    requested_theme_id: string;
    canonical_theme_key: string;
    display_name: string;
    aliases: string[];
    resolution_state: string;
  };
  lineage: {
    graph_snapshot_id: number | null;
    graph_build_version: string | null;
    controller_snapshot_id: number | null;
    controller_version: string | null;
    opportunity_snapshot_id: number | null;
    opportunity_version: string | null;
    packet_family_version: string | null;
    packet_family_revision: number | null;
    lineage_state: string;
  };
  graph: {
    snapshot_id: number | null;
    build_version: string | null;
    nodes: ThemeIndustrialNode[];
    edges: ThemeIndustrialEdge[];
    evidence_count: number;
    dependency_paths: ThemeIndustrialPath[];
    counts_by_type: Record<string, number>;
  };
  constraints: ThemeIndustrialConstraint[];
  controllers: ThemeIndustrialController[];
  opportunities: ThemeIndustrialOpportunity[];
  decision_packets: ThemeIndustrialPacketSummary;
  coverage: {
    overall_coverage: number;
    components: Record<string, ThemeIndustrialCoverageMetric>;
  };
  research_gaps: Array<{
    code: string;
    label: string;
    layer: string;
    state: string;
    observed_count: number;
  }>;
}

export interface ThemeAggregateResponse {
  theme_id: string;
  name: string;
  score: Partial<ThemeScoreRecord>;
  discovery: Partial<ThemeDiscoveryRecord>;
  lifecycle: ThemeAggregateLifecycle;
  catalysts: {
    top_catalysts: ThemeCatalystRecord[];
    future_catalysts: ThemeCatalystRecord[];
    key_blockers: ThemeCatalystRecord[];
  };
  bottlenecks: {
    primary_bottleneck: ThemeBottleneckRecord | null;
    secondary_bottlenecks: ThemeBottleneckRecord[];
    controllers: Array<Record<string, unknown>>;
    beneficiaries: Array<Record<string, unknown>>;
    what_fixes_it: string[];
    what_to_monitor: string[];
  };
  beneficiaries: {
    top_beneficiaries: ThemeBeneficiaryRecord[];
    controllers: ThemeBeneficiaryRecord[];
    resolution_enablers: ThemeBeneficiaryRecord[];
    direct_beneficiaries: ThemeBeneficiaryRecord[];
    indirect_beneficiaries: ThemeBeneficiaryRecord[];
  };
  portfolio_context: {
    portfolios: Array<{
      portfolio_type: string;
      portfolio_name: string;
      weight: number | null;
      risk_profile?: string;
      portfolio_score?: number | null;
      allocation_rationale?: string;
    }>;
  };
  supply_chain: ThemeAggregateSupplyChain;
  relationship_intelligence: ThemeRelationshipIntelligence;
  industrial_intelligence: ThemeIndustrialIntelligence;
}

export type ThemeRegistryStatus = "ACTIVE" | "DISCOVERED" | "ARCHIVED";
export type ThemeRegistrySource = "GRAPH" | "SCOUT" | "MANUAL";
export type ThemeRegistryType = "INDUSTRIAL" | "TECHNOLOGY" | "INFRASTRUCTURE" | "SUPPLY_CHAIN" | "EMERGING";
export type ThemeRankingLifecycle = "EMERGING" | "ACCELERATING" | "ACTIVE" | "MONITORING" | "DECLINING";

export interface ThemeRank {
  theme_id: string;
  theme_name: string;
  lifecycle: ThemeRankingLifecycle;
  rank_score: number;
  momentum_score: number;
  evidence_score: number;
  research_score: number;
  controller_score: number;
  opportunity_score: number;
  updated_at: string;
}

export interface ThemeRankingResponse {
  available: boolean;
  generated_at: string;
  algorithm_version: string;
  weights: {
    evidence: number;
    research: number;
    controller: number;
    opportunity: number;
    momentum: number;
  };
  themes: ThemeRank[];
}

export interface ThemeRegistryEntry {
  theme_id: string;
  theme_name: string;
  status: ThemeRegistryStatus;
  source: ThemeRegistrySource;
  theme_type: ThemeRegistryType;
  rank: number;
  research_case_count: number;
  graph_snapshot_count: number;
  controller_count: number;
  opportunity_count: number;
  updated_at: string;
  rankBadge?: string | null;
  rankingLifecycle?: ThemeRankingLifecycle | null;
}

export interface ThemeRegistryResponse {
  available: boolean;
  generated_at: string;
  source_priority: ThemeRegistrySource[];
  themes: ThemeRegistryEntry[];
}

export interface StockResearchRole {
  role_type: "Controller" | "Beneficiary" | "Enabler" | "Supplier" | "Constraint Resolver" | string;
  role_description: string;
  role_importance: number;
  evidence_count: number;
  evidence_ids: number[];
}

export interface StockResearchThemeExposure {
  theme_id: string;
  theme_name: string;
  rank: number | null;
  lifecycle: ThemeRankingLifecycle | "Unavailable" | string;
  importance: number;
  coverage: number;
  evidence_count: number;
}

export interface StockResearchEvidenceStep {
  step_type: string;
  label: string;
  source: string;
  evidence_ids: number[];
}

export interface StockResearchCompleteness {
  coverage: number;
  evidence_strength: number;
  validation_status: "Evidence Available" | "Research Incomplete" | string;
  open_questions: string[];
  research_gaps: string[];
}

export interface StockResearchDecisionSupport {
  research_state: "Evidence Available" | "Research Incomplete" | string;
  bull_case: Array<Record<string, unknown>>;
  bear_case: Array<Record<string, unknown>>;
  monitoring_triggers: Array<Record<string, unknown>>;
  research_gaps: Array<Record<string, unknown> | string>;
}

export interface StockResearchRelatedCompany {
  ticker: string;
  company_name: string;
  relationship: string;
  evidence_count: number;
}

export interface StockResearchResponse {
  available: boolean;
  ticker: string;
  generated_at: string;
  company_header: {
    company_name: string;
    ticker: string;
    theme_rank: number | null;
    theme_lifecycle: ThemeRankingLifecycle | "Unavailable" | string;
    research_coverage: number;
    primary_theme: string;
    lineage?: Record<string, unknown>;
  };
  supply_chain_roles: StockResearchRole[];
  theme_exposure: StockResearchThemeExposure[];
  investment_thesis: {
    why_it_matters: string[];
    current_drivers: string[];
    catalysts: string[];
    risks: string[];
    research_gaps: string[];
  };
  evidence_chain: StockResearchEvidenceStep[];
  research_completeness: StockResearchCompleteness;
  decision_support: StockResearchDecisionSupport;
  related_companies: {
    same_theme: StockResearchRelatedCompany[];
    same_bottleneck: StockResearchRelatedCompany[];
    same_controller: StockResearchRelatedCompany[];
    same_opportunity: StockResearchRelatedCompany[];
  };
}
