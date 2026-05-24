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
  revenue: number | null;
  net_income: number | null;
  gross_margin: number | null;
  operating_cash_flow: number | null;
  free_cash_flow: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  debt_ratio: number | null;
  pe_ratio: number | null;
  ps_ratio: number | null;
  bubble_index: number | null;
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
  price: number | null;
  sector: string;
  bubble_analysis_data: BubbleAnalysisData;
}
