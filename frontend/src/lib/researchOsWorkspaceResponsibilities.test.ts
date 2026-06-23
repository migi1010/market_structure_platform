import {
  assertWorkspaceResponsibilities,
  buildDecisionMemoHierarchy,
  buildPipelineLifecycleHierarchy,
  buildResearchOsVisualContract,
  buildWorkspacePrimarySurfaces,
} from "./researchOsWorkspaceResponsibilities";

export function researchOsWorkspaceResponsibilityContractTest() {
  const surfaces = buildWorkspacePrimarySurfaces();
  const contract = buildResearchOsVisualContract();
  const decision = buildDecisionMemoHierarchy();
  const pipeline = buildPipelineLifecycleHierarchy();

  return {
    rotationOwnsCapitalFlowOnly:
      surfaces.rotation.question === "Where is capital moving?"
      && surfaces.rotation.primary.join(">") === "treemap>market-diagnostics>capital-flow-story>selected-sector-intelligence>theme-ranking"
      && !surfaces.rotation.primary.includes("theme-memo")
      && !surfaces.rotation.primary.includes("supply-chain-graph")
      && !surfaces.rotation.primary.includes("decision-packet"),
    scoutOwnsResearchQueueOnly:
      surfaces.scout.question === "What themes deserve research?"
      && surfaces.scout.primary.join(">") === "top-themes-worth-research>why-this-theme-matters>research-queue>evidence"
      && !surfaces.scout.primary.includes("supply-chain-graph")
      && !surfaces.scout.primary.includes("decision-intelligence"),
    themeOwnsInvestmentMemoOnly:
      surfaces.theme.question === "Why does this theme matter?"
      && surfaces.theme.primary.join(">") === "theme-selector>thesis>why-now>catalysts>risks>research-gaps>research-objects-summary"
      && !surfaces.theme.primary.includes("industrial-dependency-graph")
      && !surfaces.theme.primary.includes("supply-chain-visualization")
      && !surfaces.theme.primary.includes("pipeline-board")
      && !surfaces.theme.primary.includes("decision-packet"),
    supplyOwnsIndustrialMapOnly:
      surfaces.supplyChain.question === "How does this industry work?"
      && surfaces.supplyChain.primary.join(">") === "bottleneck>constraint-network>industrial-dependency-map"
      && !surfaces.supplyChain.primary.includes("dominant-path")
      && !surfaces.supplyChain.primary.includes("thesis")
      && !surfaces.supplyChain.primary.includes("conviction")
      && !surfaces.supplyChain.primary.includes("investment-memo"),
    stockOwnsCompanyReviewOnly:
      surfaces.stock.question === "Which company benefits?"
      && surfaces.stock.primary.join(">") === "company-header>supply-chain-role>theme-exposure>investment-thesis>evidence-chain>research-completeness>decision-support>related-companies"
      && !surfaces.stock.primary.includes("treemap")
      && !surfaces.stock.primary.includes("capital-flow-story")
      && !surfaces.stock.primary.includes("dependency-graph")
      && !surfaces.stock.primary.includes("pipeline-board"),
    pipelineAndDecisionRemovedFromWorkspaceOrder:
      !contract.workspaceOrder.includes("pipeline")
      && !contract.workspaceOrder.includes("decision-intelligence")
      && pipeline.secondary.join(">") === "timeline"
      && decision.primary.join(">") === "summary>bull_case>bear_case",
    noDuplicatePrimarySurfaces: assertWorkspaceResponsibilities(surfaces).duplicatePrimarySurfaces.length === 0,
    workspaceDifferentiation:
      contract.workspaceOrder.join(">")
      === "rotation>scout>themes>supply-chain>stock",
  };
}
