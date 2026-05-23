export type BubbleClassification =
  | "Healthy"
  | "Speculative"
  | "Overheated"
  | "Bubble Risk"
  | "Extreme Mania"
  | "Fundamental Safety"
  | "Neutral Watch"
  | "High Bubble Alert"
  | "Undervalued"
  | "Neutral"
  | "Extreme Bubble Risk"
  | "Calibrating";

export interface BubbleAnalysisData {
  revenue: number;
  net_income: number;
  gross_margin: number;
  operating_cash_flow: number;
  free_cash_flow: number;
  total_assets: number;
  total_liabilities: number;
  debt_ratio: number;
  pe_ratio: number;
  ps_ratio: number;
  bubble_index: number;
  classification: BubbleClassification;
  valuation_heat?: number;
  revenue_divergence?: number;
  fcf_quality?: number;
  dilution_risk?: number;
  distribution_signal?: number;
  retail_speculation?: number;
  accrual_ratio?: number;
  net_income_quality?: number;
  confidence_score?: number;
  confidence_label?: string;
  data_completeness?: number;
  factor_breakdown?: Record<string, number>;
  ai_summary: string;
}

export interface BubbleApiResponse {
  ticker: string;
  company_name: string;
  price: number;
  sector: string;
  bubble_analysis_data: BubbleAnalysisData;
}
