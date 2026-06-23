import {
  buildResearchOsContextPersistenceContract,
  preserveResearchOsContext,
} from "./researchOsContextPersistence";

export function researchOsContextPersistenceContractTest() {
  const contract = buildResearchOsContextPersistenceContract();
  const preserved = preserveResearchOsContext(
    {
      selectedTheme: "ai_infrastructure",
      selectedTicker: "NVDA",
      selectedSupplyChainNode: "constraint:power_availability",
      selectedScoutCandidate: "candidate:ai_infrastructure_constraint_watch",
      scrollPositions: { "theme-intelligence": 420 },
      activeFilters: { "theme-supply-chain": ["controllers"] },
    },
    { activeModule: "theme-supply-chain" },
  );

  return {
    requiredKeysCovered:
      contract.preservedKeys.join(">")
      === "selectedTheme>selectedTicker>selectedSupplyChainNode>selectedScoutCandidate>scrollPositions>activeFilters",
    themePreservedAcrossSupplyChain:
      preserved.selectedTheme === "ai_infrastructure"
      && preserved.activeModule === "theme-supply-chain",
    stockPreservedAcrossWorkspaceSwitch:
      preserved.selectedTicker === "NVDA",
    supplyChainNodePreserved:
      preserved.selectedSupplyChainNode === "constraint:power_availability",
    scoutCandidatePreserved:
      preserved.selectedScoutCandidate === "candidate:ai_infrastructure_constraint_watch",
    scrollAndFiltersPreserved:
      preserved.scrollPositions["theme-intelligence"] === 420
      && preserved.activeFilters["theme-supply-chain"]?.[0] === "controllers",
  };
}
