"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getEnabledTerminalModule, type TerminalModuleId } from "@/modules/terminalModules";
import type { WorkspaceAction } from "@/types/stock";

const WORKSPACE_STORAGE_KEY = "miji:workspace-context";
const WORKSPACE_SCHEMA_VERSION = "workspace_v1";
const DEFAULT_TICKER = "NVDA";
const DEFAULT_THEME = "";
const DEFAULT_SECTOR = "Technology";
const DEFAULT_THEME_VIEW = "command";
const DEFAULT_ALPHA_VIEW = "top-alpha";
const DEFAULT_PORTFOLIO_VIEW = "watchlist";
const DEFAULT_MODULE: TerminalModuleId = "market-intel";
const MAX_RECENTS = 8;

interface WorkspaceEnvelope {
  schema_version: string;
  data: Partial<WorkspaceState>;
}

interface WorkspaceState {
  selectedTicker: string;
  selectedTheme: string;
  selectedSector: string;
  selectedSupplyChainNode: string;
  selectedScoutCandidate: string;
  selectedThemeView: string;
  selectedAlphaView: string;
  selectedPortfolioView: string;
  activeModule: TerminalModuleId;
  lastWorkspaceAction: WorkspaceAction | null;
  recentTickers: string[];
  recentThemes: string[];
  scrollPositions: Record<string, number>;
  activeFilters: Record<string, string[]>;
}

interface WorkspaceContextValue extends WorkspaceState {
  setSelectedTicker: (ticker: string) => void;
  setSelectedTheme: (theme: string) => void;
  setSelectedSector: (sector: string) => void;
  setSelectedSupplyChainNode: (nodeKey: string) => void;
  setSelectedScoutCandidate: (candidateKey: string) => void;
  setSelectedThemeView: (view: string) => void;
  setSelectedAlphaView: (view: string) => void;
  setSelectedPortfolioView: (view: string) => void;
  setActiveModule: (module: TerminalModuleId) => void;
  setWorkspaceScrollPosition: (workspace: TerminalModuleId, position: number) => void;
  setWorkspaceActiveFilters: (workspace: TerminalModuleId, filters: string[]) => void;
  dispatchWorkspaceAction: (action: WorkspaceAction) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

function normalizeTheme(theme: string): string {
  return theme.trim().replace(/\s+/g, " ");
}

function normalizeWorkspaceLabel(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function uniqueRecent(value: string, existing: string[]): string[] {
  const normalized = value.trim();
  if (!normalized) return existing.slice(0, MAX_RECENTS);
  return [normalized, ...existing.filter((item) => item.toUpperCase() !== normalized.toUpperCase())].slice(0, MAX_RECENTS);
}

function validModule(value: unknown): TerminalModuleId {
  return typeof value === "string" && getEnabledTerminalModule(value) ? (value as TerminalModuleId) : DEFAULT_MODULE;
}

function themeViewForModule(module: TerminalModuleId): string | null {
  if (module === "theme-intelligence") return "command";
  if (module === "theme-scout") return "scout";
  if (module === "theme-forecast") return "forecast";
  if (module === "market-intel") return "rotation";
  if (module === "theme-stocks") return "stocks";
  if (module === "theme-supply-chain") return "supply-chain";
  if (module === "theme-risk") return "risk";
  return null;
}

function validStringList(value: unknown, normalizer: (item: string) => string): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === "string")
    .map(normalizer)
    .filter(Boolean)
    .slice(0, MAX_RECENTS);
}

function validNumberRecord(value: unknown): Record<string, number> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.entries(value).reduce<Record<string, number>>((acc, [key, item]) => {
    const parsed = Number(item);
    const normalizedKey = normalizeWorkspaceLabel(key);
    if (normalizedKey && Number.isFinite(parsed) && parsed >= 0) acc[normalizedKey] = parsed;
    return acc;
  }, {});
}

function validStringArrayRecord(value: unknown): Record<string, string[]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.entries(value).reduce<Record<string, string[]>>((acc, [key, item]) => {
    const normalizedKey = normalizeWorkspaceLabel(key);
    const filters = validStringList(item, normalizeWorkspaceLabel);
    if (normalizedKey && filters.length > 0) acc[normalizedKey] = filters;
    return acc;
  }, {});
}

function readWorkspaceState(): WorkspaceState {
  const fallbackState = {
    selectedTicker: DEFAULT_TICKER,
    selectedTheme: DEFAULT_THEME,
    selectedSector: DEFAULT_SECTOR,
    selectedSupplyChainNode: "",
    selectedScoutCandidate: "",
    selectedThemeView: DEFAULT_THEME_VIEW,
    selectedAlphaView: DEFAULT_ALPHA_VIEW,
    selectedPortfolioView: DEFAULT_PORTFOLIO_VIEW,
    activeModule: DEFAULT_MODULE,
    lastWorkspaceAction: null,
    recentTickers: [DEFAULT_TICKER],
    recentThemes: [],
    scrollPositions: {},
    activeFilters: {},
  };
  if (typeof window === "undefined") {
    return fallbackState;
  }
  try {
    const raw = window.localStorage.getItem(WORKSPACE_STORAGE_KEY);
    if (!raw) {
      return fallbackState;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || (parsed as WorkspaceEnvelope).schema_version !== WORKSPACE_SCHEMA_VERSION) {
      window.localStorage.removeItem(WORKSPACE_STORAGE_KEY);
      return fallbackState;
    }
    const data = (parsed as WorkspaceEnvelope).data ?? {};
    const selectedTicker = normalizeTicker(data.selectedTicker ?? DEFAULT_TICKER) || DEFAULT_TICKER;
    const selectedTheme = normalizeTheme(data.selectedTheme ?? DEFAULT_THEME) || DEFAULT_THEME;
    return {
      selectedTicker,
      selectedTheme,
      selectedSector: normalizeWorkspaceLabel(data.selectedSector ?? DEFAULT_SECTOR) || DEFAULT_SECTOR,
      selectedSupplyChainNode: normalizeWorkspaceLabel(data.selectedSupplyChainNode ?? ""),
      selectedScoutCandidate: normalizeWorkspaceLabel(data.selectedScoutCandidate ?? ""),
      selectedThemeView: normalizeWorkspaceLabel(data.selectedThemeView ?? DEFAULT_THEME_VIEW) || DEFAULT_THEME_VIEW,
      selectedAlphaView: normalizeWorkspaceLabel(data.selectedAlphaView ?? DEFAULT_ALPHA_VIEW) || DEFAULT_ALPHA_VIEW,
      selectedPortfolioView: normalizeWorkspaceLabel(data.selectedPortfolioView ?? DEFAULT_PORTFOLIO_VIEW) || DEFAULT_PORTFOLIO_VIEW,
      activeModule: validModule(data.activeModule),
      lastWorkspaceAction: data.lastWorkspaceAction ?? null,
      recentTickers: uniqueRecent(selectedTicker, validStringList(data.recentTickers, normalizeTicker)),
      recentThemes: selectedTheme ? uniqueRecent(selectedTheme, validStringList(data.recentThemes, normalizeTheme)) : validStringList(data.recentThemes, normalizeTheme),
      scrollPositions: validNumberRecord(data.scrollPositions),
      activeFilters: validStringArrayRecord(data.activeFilters),
    };
  } catch {
    window.localStorage.removeItem(WORKSPACE_STORAGE_KEY);
    return fallbackState;
  }
}

function writeWorkspaceState(state: WorkspaceState): void {
  if (typeof window === "undefined") return;
  try {
    const envelope: WorkspaceEnvelope = {
      schema_version: WORKSPACE_SCHEMA_VERSION,
      data: state,
    };
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, JSON.stringify(envelope));
  } catch {
    // Workspace persistence is best effort and must never block navigation.
  }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  const [state, setState] = useState<WorkspaceState>({
    selectedTicker: DEFAULT_TICKER,
    selectedTheme: DEFAULT_THEME,
    selectedSector: DEFAULT_SECTOR,
    selectedSupplyChainNode: "",
    selectedScoutCandidate: "",
    selectedThemeView: DEFAULT_THEME_VIEW,
    selectedAlphaView: DEFAULT_ALPHA_VIEW,
    selectedPortfolioView: DEFAULT_PORTFOLIO_VIEW,
    activeModule: DEFAULT_MODULE,
    lastWorkspaceAction: null,
    recentTickers: [DEFAULT_TICKER],
    recentThemes: [],
    scrollPositions: {},
    activeFilters: {},
  });

  useEffect(() => {
    setState(readWorkspaceState());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    writeWorkspaceState(state);
  }, [hydrated, state]);

  const setSelectedTicker = useCallback((ticker: string) => {
    const symbol = normalizeTicker(ticker);
    if (!symbol) return;
    setState((current) => ({
      ...current,
      selectedTicker: symbol,
      recentTickers: uniqueRecent(symbol, current.recentTickers),
    }));
  }, []);

  const setSelectedTheme = useCallback((theme: string) => {
    const normalized = normalizeTheme(theme);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedTheme: normalized,
      recentThemes: uniqueRecent(normalized, current.recentThemes),
    }));
  }, []);

  const setSelectedSector = useCallback((sector: string) => {
    const normalized = normalizeWorkspaceLabel(sector);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedSector: normalized,
    }));
  }, []);

  const setSelectedSupplyChainNode = useCallback((nodeKey: string) => {
    const normalized = normalizeWorkspaceLabel(nodeKey);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedSupplyChainNode: normalized,
    }));
  }, []);

  const setSelectedScoutCandidate = useCallback((candidateKey: string) => {
    const normalized = normalizeWorkspaceLabel(candidateKey);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedScoutCandidate: normalized,
    }));
  }, []);

  const setSelectedThemeView = useCallback((view: string) => {
    const normalized = normalizeWorkspaceLabel(view);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedThemeView: normalized,
    }));
  }, []);

  const setSelectedAlphaView = useCallback((view: string) => {
    const normalized = normalizeWorkspaceLabel(view);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedAlphaView: normalized,
    }));
  }, []);

  const setSelectedPortfolioView = useCallback((view: string) => {
    const normalized = normalizeWorkspaceLabel(view);
    if (!normalized) return;
    setState((current) => ({
      ...current,
      selectedPortfolioView: normalized,
    }));
  }, []);

  const setActiveModule = useCallback((module: TerminalModuleId) => {
    if (!getEnabledTerminalModule(module)) return;
    setState((current) => ({
      ...current,
      activeModule: module,
      selectedThemeView: themeViewForModule(module) ?? current.selectedThemeView,
    }));
  }, []);

  const setWorkspaceScrollPosition = useCallback((workspace: TerminalModuleId, position: number) => {
    if (!getEnabledTerminalModule(workspace) || !Number.isFinite(position) || position < 0) return;
    setState((current) => ({
      ...current,
      scrollPositions: {
        ...current.scrollPositions,
        [workspace]: position,
      },
    }));
  }, []);

  const setWorkspaceActiveFilters = useCallback((workspace: TerminalModuleId, filters: string[]) => {
    if (!getEnabledTerminalModule(workspace)) return;
    const normalized = validStringList(filters, normalizeWorkspaceLabel);
    setState((current) => ({
      ...current,
      activeFilters: {
        ...current.activeFilters,
        [workspace]: normalized,
      },
    }));
  }, []);

  const dispatchWorkspaceAction = useCallback((action: WorkspaceAction) => {
    const resolvedTarget = getEnabledTerminalModule(action.target_tab)?.id ?? null;
    if (!resolvedTarget) return;
    setState((current) => {
      const payload = action.contextPayload ?? {};
      const ticker = payload.ticker ? normalizeTicker(payload.ticker) : "";
      const theme = payload.theme ? normalizeTheme(payload.theme) : "";
      const themeView = payload.themeView ? normalizeWorkspaceLabel(payload.themeView) : themeViewForModule(resolvedTarget) ?? "";
      const sector = payload.sector ? normalizeWorkspaceLabel(payload.sector) : "";
      const alphaView = payload.alphaView ? normalizeWorkspaceLabel(payload.alphaView) : "";
      const portfolioView = payload.portfolioView ? normalizeWorkspaceLabel(payload.portfolioView) : "";
      const supplyChainNode = payload.supplyChainNode ? normalizeWorkspaceLabel(payload.supplyChainNode) : "";
      const scoutCandidate = payload.scoutCandidate ? normalizeWorkspaceLabel(payload.scoutCandidate) : "";
      return {
        ...current,
        activeModule: resolvedTarget,
        selectedTicker: ticker || current.selectedTicker,
        selectedTheme: theme || current.selectedTheme,
        selectedSupplyChainNode: supplyChainNode || current.selectedSupplyChainNode,
        selectedScoutCandidate: scoutCandidate || current.selectedScoutCandidate,
        selectedThemeView: themeView || current.selectedThemeView,
        selectedSector: sector || current.selectedSector,
        selectedAlphaView: alphaView || current.selectedAlphaView,
        selectedPortfolioView: portfolioView || current.selectedPortfolioView,
        lastWorkspaceAction: action,
        recentTickers: ticker ? uniqueRecent(ticker, current.recentTickers) : current.recentTickers,
        recentThemes: theme ? uniqueRecent(theme, current.recentThemes) : current.recentThemes,
      };
    });
  }, []);

  const value = useMemo<WorkspaceContextValue>(() => ({
    ...state,
    setSelectedTicker,
    setSelectedTheme,
    setSelectedSector,
    setSelectedSupplyChainNode,
    setSelectedScoutCandidate,
    setSelectedThemeView,
    setSelectedAlphaView,
    setSelectedPortfolioView,
    setActiveModule,
    setWorkspaceScrollPosition,
    setWorkspaceActiveFilters,
    dispatchWorkspaceAction,
  }), [dispatchWorkspaceAction, setActiveModule, setSelectedAlphaView, setSelectedPortfolioView, setSelectedScoutCandidate, setSelectedSector, setSelectedSupplyChainNode, setSelectedTheme, setSelectedThemeView, setSelectedTicker, setWorkspaceActiveFilters, setWorkspaceScrollPosition, state]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return value;
}
