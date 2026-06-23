"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Command as CommandIcon, Loader2, Plus, Search } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { classifyEntityQuery, entityCategoryLabel, entityFromSearchResult } from "@/lib/entities";
import { searchResultIdentity, uniqueSearchResults } from "@/lib/searchResultIdentity";
import { enabledTerminalModules, getTerminalModule } from "@/modules/terminalModules";
import { classifySearchIntent, fetchThemeRegistry, resolveExactSearchResult, searchStocks } from "@/services/stockApi";
import type { OmniboxIntent, OmniboxTargetTab, SearchResult, ThemeRegistryEntry, WorkspaceAction } from "@/types/stock";
import { BilingualLabel, HeatStrip, SectorIcon, SparklineMini, StatusDot, ThemeIcon, TickerLogo } from "./terminal";

interface GlobalStockSearchProps {
  onSelect: (symbol: string) => void;
  onPreviewResult?: (result: SearchResult) => void;
  onPreviewEnd?: () => void;
  onSelectResult?: (result: SearchResult) => void;
  onDrilldownResult?: (result: SearchResult) => void;
  onAddToWatchlist?: (symbol: string) => void;
  placeholder?: string;
}

const GROUP_ORDER = ["Stocks", "Themes", "Sectors", "Commands"] as const;
const FALLBACK_SUGGESTIONS = ["NVDA", "Semiconductors", "Alpha Momentum", "Portfolio Watchlist"];

function getResultGroup(item: SearchResult): (typeof GROUP_ORDER)[number] {
  if (item.group && GROUP_ORDER.includes(item.group)) return item.group;
  const type = item.type?.toLowerCase();
  if (type === "theme" || type === "supply chain" || type === "supply_chain") return "Themes";
  if (type === "sector" || type === "industry") return "Sectors";
  if (type === "command" || type === "risk" || type === "risk overlay" || type === "risk_overlay") return "Commands";
  return "Stocks";
}

function getResultTitle(item: SearchResult): string {
  return item.label ?? item.company ?? item.theme ?? item.sector ?? item.name ?? item.symbol;
}

function getResultDescription(item: SearchResult): string {
  return item.description ?? item.name ?? item.type ?? "Open workspace";
}

function getCategoryLabel(item: SearchResult): string {
  const category = entityCategoryLabel(entityFromSearchResult(item).type);
  return `${category.zh} ${category.en}`;
}

function getTargetLabel(item: SearchResult): string {
  return getTerminalModule(item.target_tab)?.labelEn ?? "Stock";
}

function resultMovement(item: SearchResult): number | null {
  const candidates = [
    (item as { change_percent?: unknown }).change_percent,
    (item as { score?: unknown }).score,
    (item as { confidence?: unknown }).confidence,
  ];
  for (const candidate of candidates) {
    const value = Number(candidate);
    if (Number.isFinite(value)) return value;
  }
  return null;
}

function getGroupLabel(group: (typeof GROUP_ORDER)[number]) {
  if (group === "Stocks") return { zh: "股票", en: "Stocks" };
  if (group === "Themes") return { zh: "主題", en: "Themes" };
  if (group === "Sectors") return { zh: "板塊", en: "Sectors" };
  return { zh: "指令", en: "Commands" };
}

function ResultAnchor({ item }: { item: SearchResult }) {
  const group = getResultGroup(item);
  if (group === "Themes") return <ThemeIcon theme={getResultTitle(item)} />;
  if (group === "Sectors") return <SectorIcon sector={getResultTitle(item)} />;
  return <TickerLogo ticker={item.ticker ?? item.symbol} name={getResultTitle(item)} />;
}

function getIntentLabel(intent: OmniboxIntent, query: string, item?: SearchResult): string {
  const group = item ? getResultGroup(item) : null;
  const entityType = classifyEntityQuery(query);
  if (!item && entityType === "supply_chain") return "SUPPLY CHAIN SEARCH";
  if (!item && entityType === "risk_overlay") return "RISK OVERLAY SEARCH";
  if (!item && entityType === "industry") return "INDUSTRY SEARCH";
  if (!item && entityType === "etf") return "ETF SEARCH";
  if (group === "Themes" || intent === "theme") return "THEME SEARCH";
  if (group === "Sectors" || intent === "sector") return "SECTOR SEARCH";
  if (group === "Commands" || intent === "command") return "COMMAND";
  return "STOCK SEARCH";
}

function getActionSummary(item: SearchResult | undefined, fallbackQuery: string): string {
  if (!item) {
    const query = fallbackQuery.trim();
    if (!query) return "Start with a ticker, theme, sector, supply chain, ETF, or risk overlay";
    const category = entityCategoryLabel(classifyEntityQuery(query));
    return `Open ${category.en}: ${query}`;
  }
  const group = getResultGroup(item);
  const title = getResultTitle(item);
  if (group === "Stocks") return `Open Stock Analysis for ${item.ticker ?? item.symbol}`;
  if (group === "Themes") return `Open Theme Research: ${title}`;
  if (group === "Sectors") return `Open Theme Research / Rotation: ${title}`;
  return `Open ${getTargetLabel(item)}: ${title}`;
}

function canAddToWatchlist(item: SearchResult): boolean {
  const group = getResultGroup(item);
  const type = item.type?.toLowerCase();
  return group === "Stocks" && !["theme", "sector", "command"].includes(type);
}

interface OverlayPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

function stockRecentResult(ticker: string): SearchResult {
  const symbol = ticker.trim().toUpperCase();
  const workspaceAction: WorkspaceAction = {
    actionType: "open_stock",
    target_tab: "stock-analysis",
    focusTarget: "stock-workspace",
    openMode: "replace",
    contextPayload: { ticker: symbol, label: `Open ${symbol} Analysis` },
  };
  return {
    symbol,
    ticker: symbol,
    name: `${symbol} Analysis`,
    company: `${symbol} Analysis`,
    label: `Open ${symbol} Analysis`,
    description: "Recent stock workspace",
    exchange: "Recent",
    type: "Equity",
    intent: "ticker",
    group: "Stocks",
    target_tab: "stock-analysis",
    actionType: workspaceAction.actionType,
    focusTarget: workspaceAction.focusTarget,
    contextPayload: workspaceAction.contextPayload,
    openMode: workspaceAction.openMode,
    workspaceAction,
  };
}

function themeRecentResult(theme: string): SearchResult {
  const label = theme.trim();
  const workspaceAction: WorkspaceAction = {
    actionType: "open_theme",
    target_tab: "theme-intelligence",
    focusTarget: "theme-detail",
    openMode: "replace",
    contextPayload: { theme: label, themeView: "command", label: `Open ${label}` },
  };
  return {
    symbol: `THEME:${label.toUpperCase().replace(/[^A-Z0-9]+/g, "-")}`,
    name: label,
    theme: label,
    label,
    description: "Recent theme workspace",
    exchange: "Recent",
    type: "Theme",
    intent: "theme",
    group: "Themes",
    target_tab: "theme-intelligence",
    actionType: workspaceAction.actionType,
    focusTarget: workspaceAction.focusTarget,
    contextPayload: workspaceAction.contextPayload,
    openMode: workspaceAction.openMode,
    workspaceAction,
  };
}

function commandAction(title: string, targetTab: OmniboxTargetTab): WorkspaceAction {
  if (targetTab === "alpha-quant") {
    return { actionType: "open_alpha", target_tab: targetTab, focusTarget: "alpha-workspace", openMode: "replace", contextPayload: { alphaView: "top-alpha", label: title } };
  }
  if (targetTab === "portfolio") {
    return { actionType: "open_portfolio", target_tab: targetTab, focusTarget: "portfolio-watchlist", openMode: "replace", contextPayload: { portfolioView: "watchlist", label: title } };
  }
  if (targetTab === "market-intel") {
    return { actionType: "open_sector", target_tab: "market-intel", focusTarget: "theme-rotation", openMode: "replace", contextPayload: { themeView: "rotation", label: title } };
  }
  if (targetTab === "theme-intelligence") {
    const normalized = title.toLowerCase();
    const themeView = normalized.includes("forecast") ? "forecast" : normalized.includes("rotation") ? "rotation" : normalized.includes("supply") ? "supply-chain" : "command";
    const focusTarget = themeView === "forecast" ? "theme-forecast" : themeView === "rotation" ? "theme-rotation" : themeView === "supply-chain" ? "theme-supply-chain" : "theme-workspace";
    return { actionType: "open_module", target_tab: targetTab, focusTarget, openMode: "replace", contextPayload: { themeView, label: title } };
  }
  if (targetTab === "theme-risk") {
    return { actionType: "open_theme", target_tab: "theme-intelligence", focusTarget: "theme-detail", openMode: "replace", contextPayload: { themeView: "command", label: `${title} Overlay` } };
  }
  return { actionType: "open_module", target_tab: targetTab, focusTarget: targetTab, openMode: "replace", contextPayload: { label: title } };
}

function commandResult(title: string, description: string, targetTab: OmniboxTargetTab): SearchResult {
  const symbol = title.toUpperCase().replace(/[^A-Z0-9]+/g, "-");
  const workspaceAction = commandAction(title, targetTab);
  return {
    symbol,
    name: title,
    label: title,
    description,
    exchange: "Command",
    type: "Command",
    intent: "command",
    group: "Commands",
    target_tab: targetTab,
    command: `open-${targetTab}`,
    actionType: workspaceAction.actionType,
    focusTarget: workspaceAction.focusTarget,
    contextPayload: workspaceAction.contextPayload,
    openMode: workspaceAction.openMode,
    workspaceAction,
  };
}

export default function GlobalStockSearch({ onSelect, onPreviewResult, onPreviewEnd, onSelectResult, onDrilldownResult, onAddToWatchlist, placeholder = "Search stock, theme, sector, industry, supply chain, ETF, risk..." }: GlobalStockSearchProps) {
  const { recentTickers, recentThemes } = useWorkspace();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [registryThemes, setRegistryThemes] = useState<ThemeRegistryEntry[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const [portalReady, setPortalReady] = useState(false);
  const [overlayPosition, setOverlayPosition] = useState<OverlayPosition>({ top: 88, left: 16, width: 720, maxHeight: 544 });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);

  const quickResults = useMemo<SearchResult[]>(() => {
    const moduleCommands = enabledTerminalModules
      .filter((module) => module.workspaceType !== "stock" && module.id !== "theme-risk")
      .map((module) => commandResult(`Open ${module.title}`, module.description, module.target_tab));
    const defaultStockAction = recentTickers.some((ticker) => ticker.toUpperCase() === "NVDA") ? [] : [stockRecentResult("NVDA")];
    const candidates = [
      ...recentTickers.slice(0, 5).map(stockRecentResult),
      ...recentThemes.slice(0, 4).map(themeRecentResult),
      ...defaultStockAction,
      ...moduleCommands,
      commandResult("Open Theme Forecast", "Forecast module inside Theme Research", "theme-forecast"),
      commandResult("Open Capital Rotation", "Rotation module inside Theme Research", "market-intel"),
      commandResult("Open Supply Chain", "Supply-chain module inside Theme Research", "theme-supply-chain"),
    ];
    return uniqueSearchResults(candidates);
  }, [recentThemes, recentTickers]);

  const visibleResults = useMemo(() => uniqueSearchResults(query.trim() ? results : quickResults), [query, quickResults, results]);
  const selectedResult = visibleResults?.[activeIndex];
  const searchIntent = query.trim() ? classifySearchIntent(query, registryThemes) : "command";
  const intentLabel = getIntentLabel(searchIntent, query, selectedResult);
  const emptyResultCategory = entityCategoryLabel(classifyEntityQuery(query));
  const actionSummary = getActionSummary(selectedResult, query);
  const groupedResults = visibleResults.reduce<Array<{ group: (typeof GROUP_ORDER)[number]; items: SearchResult[] }>>((acc, item) => {
    const group = getResultGroup(item);
    const existing = acc.find((entry) => entry.group === group);
    if (existing) existing.items.push(item);
    else acc.push({ group, items: [item] });
    return acc;
  }, []);

  const updateOverlayPosition = useCallback(() => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || typeof window === "undefined") return;
    const margin = 12;
    const spacing = 10;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const maxWidth = Math.max(280, viewportWidth - margin * 2);
    const preferredWidth = Math.max(
      Math.min(maxWidth, rect.width),
      Math.min(maxWidth, viewportWidth < 768 ? maxWidth : 620),
    );
    const documentLeft = rect.right + scrollX - preferredWidth;
    const documentTop = rect.bottom + scrollY + spacing;
    const left = Math.min(Math.max(margin, documentLeft - scrollX), viewportWidth - preferredWidth - margin);
    const anchoredTop = documentTop - scrollY;
    const preferredMaxHeight = Math.min(544, viewportHeight * 0.72);
    const belowSpace = viewportHeight - anchoredTop - margin;
    const aboveSpace = rect.top - spacing - margin;
    const useAbove = belowSpace < 180 && aboveSpace > belowSpace && aboveSpace >= 160;
    const maxHeight = Math.max(80, Math.min(preferredMaxHeight, useAbove ? aboveSpace : belowSpace));
    const top = useAbove ? Math.max(margin, rect.top - spacing - maxHeight) : Math.max(margin, anchoredTop);

    // Portal coordinates are fixed to the viewport; scroll offsets are only used
    // to normalize document-space measurements back into viewport coordinates.
    setOverlayPosition({ top, left, width: preferredWidth, maxHeight });
  }, []);

  useEffect(() => {
    setPortalReady(true);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchThemeRegistry(controller.signal)
      .then((payload) => setRegistryThemes(payload.themes))
      .catch(() => setRegistryThemes([]));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      if (!query.trim()) {
        setResults([]);
        setActiveIndex(0);
        setLoading(false);
        return;
      }
      setLoading(true);
      const next = await searchStocks(query, registryThemes);
      if (!cancelled) {
        setResults(next);
        setActiveIndex(0);
        setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, registryThemes]);

  useLayoutEffect(() => {
    if (!open) return;
    updateOverlayPosition();
  }, [open, updateOverlayPosition, visibleResults.length]);

  useEffect(() => {
    if (!open) return;
    window.addEventListener("resize", updateOverlayPosition);
    window.addEventListener("scroll", updateOverlayPosition, true);
    return () => {
      window.removeEventListener("resize", updateOverlayPosition);
      window.removeEventListener("scroll", updateOverlayPosition, true);
    };
  }, [open, updateOverlayPosition]);

  useEffect(() => {
    function onGlobalKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener("keydown", onGlobalKeyDown);
    return () => window.removeEventListener("keydown", onGlobalKeyDown);
  }, []);

  const commitResult = (item: SearchResult) => {
    const normalized = item.symbol.trim().toUpperCase();
    if (!normalized) return;
    const normalizedItem = { ...item, symbol: normalized };
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
    if (onDrilldownResult) {
      onDrilldownResult(normalizedItem);
    } else if (onSelectResult) {
      onSelectResult(normalizedItem);
    } else {
      onSelect(normalized);
    }
  };

  const commit = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) return;
    const existing = results.find((item) => item.symbol.trim().toUpperCase() === normalized);
    const entityType = classifyEntityQuery(normalized);
    const type = entityType === "stock" ? "Equity" : entityType === "supply_chain" ? "Supply Chain" : entityType === "risk_overlay" ? "Risk Overlay" : entityType[0].toUpperCase() + entityType.slice(1);
    const group = entityType === "theme" || entityType === "supply_chain" ? "Themes" : entityType === "sector" || entityType === "industry" ? "Sectors" : entityType === "risk_overlay" ? "Commands" : "Stocks";
    commitResult(existing ?? { symbol: normalized, name: normalized, label: normalized, exchange: type === "Equity" ? "US" : type, type, group });
  };

  const previewResult = (item: SearchResult) => {
    const normalized = item.symbol.trim().toUpperCase();
    if (!normalized) return;
    setActiveIndex(Math.max(0, visibleResults.indexOf(item)));
    onSelectResult?.({ ...item, symbol: normalized });
  };

  const commitFromCurrentInput = () => {
    const normalized = query.trim().toUpperCase();
    const exactRegistryResult = resolveExactSearchResult(query, registryThemes);
    const exact = visibleResults.find((item) => item.symbol.trim().toUpperCase() === normalized || item.ticker?.trim().toUpperCase() === normalized);
    const selected = visibleResults?.[activeIndex];
    if (exactRegistryResult) commitResult(exactRegistryResult);
    else if (exact) commitResult(exact);
    else if (selected) commitResult(selected);
    else commit(normalized);
  };

  useEffect(() => {
    setActiveIndex((idx) => Math.min(Math.max(visibleResults.length - 1, 0), idx));
  }, [visibleResults.length]);

  const overlay = open && portalReady ? createPortal(
    <div className="miji-omnibox-portal pointer-events-none fixed inset-0 isolate z-[9999]" style={{ zIndex: 9999 }}>
      <button
        type="button"
        aria-label="Close command palette"
        className="pointer-events-auto absolute inset-0 z-0 cursor-default bg-[rgba(0,0,0,0.28)]"
        onMouseDown={(event) => {
          event.preventDefault();
          setOpen(false);
        }}
        onTouchStart={(event) => {
          event.preventDefault();
          setOpen(false);
        }}
      />
      <div
        className="miji-command-palette pointer-events-auto fixed z-[10000] overflow-hidden rounded-[6px] border border-[rgba(255,255,255,0.035)] bg-[var(--theme-bg)]"
        style={{ top: overlayPosition.top, left: overlayPosition.left, width: overlayPosition.width, maxHeight: overlayPosition.maxHeight, zIndex: 10000 }}
      >
        <div className="border-b border-[var(--theme-divider)] px-3 py-2">
          <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <CommandIcon size={14} className="text-[var(--theme-warning)]" />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-text-secondary)]">搜尋 Search</span>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-accent)]">
            <span>Enter</span>
            <span>Open</span>
            <span>Esc</span>
            <span>Close</span>
          </div>
          </div>
          <div className="mt-2 border-t border-[var(--theme-divider)] pt-2">
            <div className="mb-1 flex items-center justify-between gap-3">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">{intentLabel}</span>
              {loading && <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]"><Loader2 size={12} className="animate-spin" /> Searching</span>}
            </div>
            <div className="flex min-w-0 items-center gap-1 font-mono text-lg font-semibold uppercase text-[var(--theme-text)]">
              <span className={query.trim() ? "truncate" : "truncate text-[var(--theme-accent)]"}>{query.trim() || "TYPE COMMAND OR SYMBOL"}</span>
              <span className="h-6 w-2 animate-pulse bg-[var(--theme-warning)]/80" aria-hidden="true" />
            </div>
            <p className="mt-1 truncate text-xs font-medium text-[var(--theme-muted)]">{actionSummary}</p>
          </div>
        </div>

        <div className="overflow-y-auto overscroll-contain p-1.5" style={{ maxHeight: Math.max(80, overlayPosition.maxHeight - 116) }}>
          {(visibleResults?.length ?? 0) === 0 ? (
            <div className="space-y-2">
              <button
                onPointerDown={(event) => {
                  event.preventDefault();
                  commit(query);
                }}
                className="w-full border-b border-[var(--theme-divider)] px-3 py-2.5 text-left font-mono text-sm font-semibold text-[var(--theme-text)] transition hover:bg-[rgba(255,255,255,0.035)]"
              >
                Open {query || "ticker"} · {emptyResultCategory.en}
              </button>
              <div className="border-t border-[var(--theme-divider)] px-3 py-2">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Try</p>
                <div className="flex flex-wrap gap-2">
                  {[...registryThemes.slice(0, 1).map((theme) => theme.theme_name), ...FALLBACK_SUGGESTIONS].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onPointerDown={(event) => {
                        event.preventDefault();
                        setQuery(suggestion.toUpperCase());
                        setOpen(true);
                        inputRef.current?.focus();
                      }}
                      className="rounded-[4px] px-2 py-1 text-xs font-semibold text-[var(--theme-text-secondary)] transition hover:bg-[rgba(255,255,255,0.035)] hover:text-[var(--theme-accent-strong)]"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {!query.trim() && <div className="px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Recent and Quick Actions</div>}
              {groupedResults.map(({ group, items }) => (
                <section key={group} className="pb-2">
                  <div className="sticky top-0 z-10 bg-[var(--theme-bg)] px-3 py-1">
                    <BilingualLabel {...getGroupLabel(group)} inline />
                  </div>
                  <div>
                    {items.map((item) => {
                      const index = visibleResults.indexOf(item);
                      const active = activeIndex === index;
                      const title = getResultTitle(item);
                      const description = getResultDescription(item);
                      const target = getTargetLabel(item);
                      const symbolLabel = item.ticker ?? item.symbol;
                      const movement = resultMovement(item);
                      return (
                        <div
                          key={searchResultIdentity(item)}
                          className={`group rounded-[4px] border px-2 py-1 transition ${
                            active
                              ? "border-[var(--theme-hover-edge)] bg-[rgba(255,255,255,0.035)]"
                              : "border-transparent hover:border-[var(--theme-divider)] hover:bg-[rgba(255,255,255,0.022)]"
                          }`}
                          onMouseEnter={() => onPreviewResult?.(item)}
                          onMouseLeave={onPreviewEnd}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <button
                              onClick={() => previewResult(item)}
                              onDoubleClick={() => commitResult(item)}
                              className="min-w-0 flex-1 text-left"
                            >
                              <div className="flex min-w-0 items-center gap-2">
                                <ResultAnchor item={item} />
                                <span className="min-w-[4rem] shrink-0 font-mono text-sm font-semibold text-[var(--theme-text)]">{symbolLabel}</span>
                                <span className="truncate text-sm font-semibold text-[var(--theme-text-secondary)]">{title}</span>
                                <StatusDot state={item.quote_status ?? item.type} label={getCategoryLabel(item)} />
                                <span className="hidden shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-accent-soft)] sm:inline">{item.exchange}</span>
                              </div>
                              <div className="mt-0.5 flex min-w-0 items-center justify-between gap-3 text-xs">
                                <span className="truncate text-[var(--theme-muted)]">{description}</span>
                                <span className="flex shrink-0 items-center gap-2">
                                  <SparklineMini values={[movement, movement === null ? null : movement + 8, movement === null ? null : movement - 3, movement]} />
                                  <HeatStrip value={movement === null ? null : Math.min(100, Math.max(0, 50 + movement * 4))} />
                                  <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]/80">{active ? "Open" : target}</span>
                                </span>
                              </div>
                            </button>
                            {onAddToWatchlist && canAddToWatchlist(item) && (
                              <button
                                type="button"
                                onPointerDown={(event) => {
                                  event.preventDefault();
                                  event.stopPropagation();
                                  onAddToWatchlist(item.ticker ?? item.symbol);
                                }}
                                className="inline-flex shrink-0 items-center gap-1 rounded-[4px] px-2 py-1 text-[10px] font-semibold text-[var(--theme-warning)] opacity-75 transition hover:bg-[rgba(255,255,255,0.045)] group-hover:opacity-100"
                              >
                                <Plus size={12} />
                                Add
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              ))}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  ) : null;

  return (
    <div ref={containerRef} className="miji-global-search relative w-full max-w-[380px]">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          commitFromCurrentInput();
        }}
        className="flex h-9 items-center gap-2 rounded-[6px] border border-[var(--theme-divider)] bg-transparent px-3 text-[var(--theme-text)] transition focus-within:border-[var(--theme-border-strong)] focus-within:bg-[rgba(255,255,255,0.025)]"
      >
        <Search size={16} className="text-[var(--theme-muted)]" />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value.trimStart().toUpperCase());
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onCompositionStart={() => {
            composingRef.current = true;
          }}
          onCompositionEnd={(event) => {
            composingRef.current = false;
            setQuery(event.currentTarget.value.trimStart().toUpperCase());
            setOpen(true);
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              if (composingRef.current) return;
              event.preventDefault();
              commitFromCurrentInput();
              return;
            }
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActiveIndex((idx) => Math.min(Math.max(visibleResults.length - 1, 0), idx + 1));
            }
            if (event.key === "ArrowUp") {
              event.preventDefault();
              setActiveIndex((idx) => Math.max(0, idx - 1));
            }
            if (event.key === "Escape") setOpen(false);
          }}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent font-mono text-sm uppercase text-[var(--theme-text)] outline-none placeholder:text-[var(--theme-accent)]"
        />
        {loading && <Loader2 size={15} className="animate-spin text-[var(--theme-warning)]" />}
      </form>
      {overlay}
    </div>
  );
}
