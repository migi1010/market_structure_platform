export type BubbleClassification =
  | "基本面安全"
  | "中性觀察"
  | "高度泡沫警戒"
  | "Fundamental Safety"
  | "Neutral Watch"
  | "High Bubble Alert";

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
  ai_summary: string;
}

export interface BubbleApiResponse {
  ticker: string;
  company_name: string;
  price: number;
  sector: string;
  bubble_analysis_data: BubbleAnalysisData;
}
