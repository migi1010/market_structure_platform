"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getTerminalModule, type TerminalModuleId } from "@/modules/terminalModules";

const WORKSPACE_STORAGE_KEY = "miji:workspace-context";
const WORKSPACE_SCHEMA_VERSION = "workspace_v1";
const DEFAULT_TICKER = "NVDA";
const DEFAULT_THEME = "";
const DEFAULT_MODULE: TerminalModuleId = "theme-intelligence";
const MAX_RECENTS = 8;

interface WorkspaceEnvelope {
  schema_version: string;
  data: Partial<WorkspaceState>;
}

interface WorkspaceState {
  selectedTicker: string;
  selectedTheme: string;
  activeModule: TerminalModuleId;
  recentTickers: string[];
  recentThemes: string[];
}

interface WorkspaceContextValue extends WorkspaceState {
  setSelectedTicker: (ticker: string) => void;
  setSelectedTheme: (theme: string) => void;
  setActiveModule: (module: TerminalModuleId) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

function normalizeTheme(theme: string): string {
  return theme.trim().replace(/\s+/g, " ");
}

function uniqueRecent(value: string, existing: string[]): string[] {
  const normalized = value.trim();
  if (!normalized) return existing.slice(0, MAX_RECENTS);
  return [normalized, ...existing.filter((item) => item.toUpperCase() !== normalized.toUpperCase())].slice(0, MAX_RECENTS);
}

function validModule(value: unknown): TerminalModuleId {
  return typeof value === "string" && getTerminalModule(value) ? (value as TerminalModuleId) : DEFAULT_MODULE;
}

function validStringList(value: unknown, normalizer: (item: string) => string): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === "string")
    .map(normalizer)
    .filter(Boolean)
    .slice(0, MAX_RECENTS);
}

function readWorkspaceState(): WorkspaceState {
  if (typeof window === "undefined") {
    return {
      selectedTicker: DEFAULT_TICKER,
      selectedTheme: DEFAULT_THEME,
      activeModule: DEFAULT_MODULE,
      recentTickers: [DEFAULT_TICKER],
      recentThemes: [],
    };
  }
  try {
    const raw = window.localStorage.getItem(WORKSPACE_STORAGE_KEY);
    if (!raw) {
      return {
        selectedTicker: DEFAULT_TICKER,
        selectedTheme: DEFAULT_THEME,
        activeModule: DEFAULT_MODULE,
        recentTickers: [DEFAULT_TICKER],
        recentThemes: [],
      };
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || (parsed as WorkspaceEnvelope).schema_version !== WORKSPACE_SCHEMA_VERSION) {
      window.localStorage.removeItem(WORKSPACE_STORAGE_KEY);
      return {
        selectedTicker: DEFAULT_TICKER,
        selectedTheme: DEFAULT_THEME,
        activeModule: DEFAULT_MODULE,
        recentTickers: [DEFAULT_TICKER],
        recentThemes: [],
      };
    }
    const data = (parsed as WorkspaceEnvelope).data ?? {};
    const selectedTicker = normalizeTicker(data.selectedTicker ?? DEFAULT_TICKER) || DEFAULT_TICKER;
    const selectedTheme = normalizeTheme(data.selectedTheme ?? DEFAULT_THEME) || DEFAULT_THEME;
    return {
      selectedTicker,
      selectedTheme,
      activeModule: validModule(data.activeModule),
      recentTickers: uniqueRecent(selectedTicker, validStringList(data.recentTickers, normalizeTicker)),
      recentThemes: selectedTheme ? uniqueRecent(selectedTheme, validStringList(data.recentThemes, normalizeTheme)) : validStringList(data.recentThemes, normalizeTheme),
    };
  } catch {
    window.localStorage.removeItem(WORKSPACE_STORAGE_KEY);
    return {
      selectedTicker: DEFAULT_TICKER,
      selectedTheme: DEFAULT_THEME,
      activeModule: DEFAULT_MODULE,
      recentTickers: [DEFAULT_TICKER],
      recentThemes: [],
    };
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
    activeModule: DEFAULT_MODULE,
    recentTickers: [DEFAULT_TICKER],
    recentThemes: [],
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

  const setActiveModule = useCallback((module: TerminalModuleId) => {
    if (!getTerminalModule(module)) return;
    setState((current) => ({
      ...current,
      activeModule: module,
    }));
  }, []);

  const value = useMemo<WorkspaceContextValue>(() => ({
    ...state,
    setSelectedTicker,
    setSelectedTheme,
    setActiveModule,
  }), [setActiveModule, setSelectedTheme, setSelectedTicker, state]);

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return value;
}
