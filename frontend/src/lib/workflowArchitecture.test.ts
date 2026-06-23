import {
  SCOUT_WORKFLOW_STAGES,
  SUPPLY_WORKFLOW_STAGES,
  THEME_WORKFLOW_STAGES,
} from "./workflowArchitecture";

export function workflowArchitectureContractTest() {
  return {
    themeStages:
      THEME_WORKFLOW_STAGES.map((stage) => stage.id).join(",")
      === "thesis,why-now,bottleneck,controller,beneficiary,opportunity,validation,decision",
    supplyStages:
      SUPPLY_WORKFLOW_STAGES.map((stage) => stage.id).join(",")
      === "Theme,Technology,Process,Material,Equipment,Constraint,Company",
    scoutStages:
      SCOUT_WORKFLOW_STAGES.map((stage) => stage.id).join(",")
      === "signals,clusters,constraint-watch,research-queue,validation,approval",
    chineseFirst:
      THEME_WORKFLOW_STAGES.map((stage) => stage.zh).join(",")
        === "主題論點,為何現在,關鍵瓶頸,控制層,受益者,機會,驗證,決策"
      && SUPPLY_WORKFLOW_STAGES[1]?.zh === "技術"
      && SCOUT_WORKFLOW_STAGES[3]?.zh === "研究佇列",
  };
}
