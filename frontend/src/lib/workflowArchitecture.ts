export interface WorkflowStage {
  id: string;
  zh: string;
  en: string;
}

export const THEME_WORKFLOW_STAGES = [
  { id: "thesis", zh: "主題論點", en: "Thesis" },
  { id: "why-now", zh: "為何現在", en: "Why Now" },
  { id: "bottleneck", zh: "關鍵瓶頸", en: "Bottleneck" },
  { id: "controller", zh: "控制層", en: "Controller" },
  { id: "beneficiary", zh: "受益者", en: "Beneficiary" },
  { id: "opportunity", zh: "機會", en: "Opportunity" },
  { id: "validation", zh: "驗證", en: "Validation" },
  { id: "decision", zh: "決策", en: "Decision" },
] as const satisfies readonly WorkflowStage[];

export const SUPPLY_WORKFLOW_STAGES = [
  { id: "Theme", zh: "主題", en: "Theme" },
  { id: "Technology", zh: "技術", en: "Technology" },
  { id: "Process", zh: "製程", en: "Process" },
  { id: "Material", zh: "材料", en: "Material" },
  { id: "Equipment", zh: "設備", en: "Equipment" },
  { id: "Constraint", zh: "瓶頸", en: "Constraint" },
  { id: "Company", zh: "公司", en: "Company" },
] as const satisfies readonly WorkflowStage[];

export const SCOUT_WORKFLOW_STAGES = [
  { id: "signals", zh: "訊號", en: "Signals" },
  { id: "clusters", zh: "訊號叢集", en: "Clusters" },
  { id: "constraint-watch", zh: "瓶頸觀察", en: "Constraint Watch" },
  { id: "research-queue", zh: "研究佇列", en: "Research Queue" },
  { id: "validation", zh: "驗證", en: "Validation" },
  { id: "approval", zh: "審核", en: "Approval" },
] as const satisfies readonly WorkflowStage[];
