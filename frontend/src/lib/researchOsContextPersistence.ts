import type { TerminalModuleId } from "@/modules/terminalModules";

export interface ResearchOsPersistentContext {
  selectedTheme: string;
  selectedTicker: string;
  selectedSupplyChainNode: string;
  selectedScoutCandidate: string;
  scrollPositions: Record<string, number>;
  activeFilters: Record<string, string[]>;
  activeModule?: TerminalModuleId;
}

export interface ResearchOsContextPatch {
  selectedTheme?: string;
  selectedTicker?: string;
  selectedSupplyChainNode?: string;
  selectedScoutCandidate?: string;
  scrollPositions?: Record<string, number>;
  activeFilters?: Record<string, string[]>;
  activeModule?: TerminalModuleId;
}

export function buildResearchOsContextPersistenceContract() {
  return {
    preservedKeys: [
      "selectedTheme",
      "selectedTicker",
      "selectedSupplyChainNode",
      "selectedScoutCandidate",
      "scrollPositions",
      "activeFilters",
    ] as const,
  };
}

export function preserveResearchOsContext(
  current: ResearchOsPersistentContext,
  patch: ResearchOsContextPatch,
): ResearchOsPersistentContext {
  return {
    selectedTheme: patch.selectedTheme ?? current.selectedTheme,
    selectedTicker: patch.selectedTicker ?? current.selectedTicker,
    selectedSupplyChainNode: patch.selectedSupplyChainNode ?? current.selectedSupplyChainNode,
    selectedScoutCandidate: patch.selectedScoutCandidate ?? current.selectedScoutCandidate,
    scrollPositions: patch.scrollPositions ?? current.scrollPositions,
    activeFilters: patch.activeFilters ?? current.activeFilters,
    activeModule: patch.activeModule ?? current.activeModule,
  };
}
