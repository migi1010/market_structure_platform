"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Command as CommandIcon, Loader2, Plus, Search } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { enabledTerminalModules, getTerminalModule } from "@/modules/terminalModules";
import { searchStocks } from "@/services/stockApi";
import type { OmniboxTargetTab, SearchResult, WorkspaceAction } from "@/types/stock";

interface GlobalStockSearchProps {
  onSelect: (symbol: string) => void;
  onSelectResult?: (result: SearchResult) => void;
  onAddToWatchlist?: (symbol: string) => void;
  placeholder?: string;
}

const GROUP_ORDER = ["Stocks", "Themes", "Sectors", "Commands"] as const;

function getResultGroup(item: SearchResult): (typeof GROUP_ORDER)[number] {
  if (item.group && GROUP_ORDER.includes(item.group)) return item.group;
  const type = item.type?.toLowerCase();
  if (type === "theme") return "Themes";
  if (type === "sector") return "Sectors";
  if (type === "command") return "Commands";
  return "Stocks";
}

function getResultTitle(item: SearchResult): string {
  return item.label ?? item.company ?? item.theme ?? item.sector ?? item.name ?? item.symbol;
}

function getResultDescription(item: SearchResult): string {
  return item.description ?? item.name ?? item.type ?? "Open workspace";
}

function getTargetLabel(item: SearchResult): string {
  return getTerminalModule(item.target_tab)?.title ?? "Stock Analysis";
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
    contextPayload: { theme: label, label: `Open ${label}` },
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
    return { actionType: "open_sector", target_tab: targetTab, focusTarget: "sector-drilldown", openMode: "replace", contextPayload: { label: title } };
  }
  if (targetTab === "theme-intelligence") {
    return { actionType: "open_module", target_tab: targetTab, focusTarget: "theme-workspace", openMode: "replace", contextPayload: { label: title } };
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

export default function GlobalStockSearch({ onSelect, onSelectResult, onAddToWatchlist, placeholder = "Search ticker, theme, sector, ETF..." }: GlobalStockSearchProps) {
  const { recentTickers, recentThemes } = useWorkspace();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [portalReady, setPortalReady] = useState(false);
  const [overlayPosition, setOverlayPosition] = useState<OverlayPosition>({ top: 88, left: 16, width: 720, maxHeight: 544 });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);

  const quickResults = useMemo<SearchResult[]>(() => {
    const moduleCommands = enabledTerminalModules
      .filter((module) => module.workspaceType !== "stock")
      .map((module) => commandResult(`Open ${module.title}`, module.description, module.target_tab));
    const defaultStockAction = recentTickers.some((ticker) => ticker.toUpperCase() === "NVDA") ? [] : [stockRecentResult("NVDA")];
    return [
      ...recentTickers.slice(0, 5).map(stockRecentResult),
      ...recentThemes.slice(0, 4).map(themeRecentResult),
      ...defaultStockAction,
      ...moduleCommands,
    ];
  }, [recentThemes, recentTickers]);

  const visibleResults = query.trim() ? results : quickResults;
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
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      if (!query.trim()) {
        setResults([]);
        setActiveIndex(0);
        setLoading(false);
        return;
      }
      setLoading(true);
      const next = await searchStocks(query);
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
  }, [query]);

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
    if (onSelectResult) {
      onSelectResult(normalizedItem);
    } else {
      onSelect(normalized);
    }
  };

  const commit = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) return;
    const existing = results.find((item) => item.symbol.trim().toUpperCase() === normalized);
    commitResult(existing ?? { symbol: normalized, name: normalized, exchange: "US", type: "Equity" });
  };

  const commitFromCurrentInput = () => {
    const normalized = query.trim().toUpperCase();
    const exact = visibleResults.find((item) => item.symbol.trim().toUpperCase() === normalized || item.ticker?.trim().toUpperCase() === normalized);
    const selected = visibleResults?.[activeIndex];
    if (exact) commitResult(exact);
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
        className="pointer-events-auto absolute inset-0 z-0 cursor-default bg-[#05070A]/65 backdrop-blur-[3px]"
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
        className="miji-command-palette pointer-events-auto fixed z-[10000] overflow-hidden rounded-xl border border-[#2B313C] bg-[#090B0F]/98 shadow-[0_28px_80px_rgba(0,0,0,0.62)] ring-1 ring-amber-200/10 backdrop-blur-xl"
        style={{ top: overlayPosition.top, left: overlayPosition.left, width: overlayPosition.width, maxHeight: overlayPosition.maxHeight, zIndex: 10000 }}
      >
        <div className="flex items-center justify-between border-b border-[#2B313C] bg-[#0D1117]/95 px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <CommandIcon size={14} className="text-amber-200" />
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[#C9D1D9]">Terminal Command Palette</span>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-[#6E7681]">
            <span>Enter</span>
            <span>Open</span>
            <span>Esc</span>
            <span>Close</span>
          </div>
        </div>

        <div className="overflow-y-auto overscroll-contain p-2" style={{ maxHeight: Math.max(80, overlayPosition.maxHeight - 40) }}>
          {(visibleResults?.length ?? 0) === 0 ? (
            <button
              onPointerDown={(event) => {
                event.preventDefault();
                commit(query);
              }}
              className="w-full rounded-lg border border-[#2B313C] bg-[#111318] px-3 py-3 text-left font-mono text-sm text-[#C9D1D9] transition hover:border-amber-400/20 hover:bg-[#161B22]"
            >
              Open {query || "ticker"} Analysis
            </button>
          ) : (
            <>
              {!query.trim() && <div className="px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Recent and Quick Actions</div>}
              {groupedResults.map(({ group, items }) => (
                <section key={group} className="pb-2">
                  <div className="sticky top-0 z-10 bg-[#090B0F]/95 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#6E7681] backdrop-blur-md">{group}</div>
                  <div className="space-y-1">
                    {items.map((item) => {
                      const index = visibleResults.indexOf(item);
                      const active = activeIndex === index;
                      const title = getResultTitle(item);
                      const description = getResultDescription(item);
                      const target = getTargetLabel(item);
                      const symbolLabel = item.ticker ?? item.symbol;
                      return (
                        <div
                          key={`${item.symbol}-${item.exchange}-${item.target_tab ?? item.type}`}
                          className={`group rounded-lg border px-3 py-2.5 transition ${
                            active
                              ? "border-amber-400/25 bg-[#1A1F29] shadow-[inset_3px_0_0_rgba(251,191,36,0.65)]"
                              : "border-transparent hover:border-[#2B313C] hover:bg-[#111318]"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-3">
                            <button
                              onPointerDown={(event) => {
                                event.preventDefault();
                                commitResult(item);
                              }}
                              className="min-w-0 flex-1 text-left"
                            >
                              <div className="flex min-w-0 items-center gap-2">
                                <span className="min-w-[4.25rem] shrink-0 font-mono text-sm font-semibold text-[#E6EDF3]">{symbolLabel}</span>
                                <span className="truncate text-sm font-medium text-[#C9D1D9]">{title}</span>
                                <span className="shrink-0 rounded border border-[#2B313C] bg-[#0A0C10] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">{item.type}</span>
                              </div>
                              <div className="mt-1 flex min-w-0 items-center justify-between gap-3 text-xs">
                                <span className="truncate text-[#7D8590]">{description}</span>
                                <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-amber-200/80">{target}</span>
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
                                className="inline-flex shrink-0 items-center gap-1 rounded border border-amber-400/20 px-2 py-1 text-[10px] font-semibold text-amber-200 opacity-80 transition hover:bg-amber-400/10 group-hover:opacity-100"
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
    <div ref={containerRef} className="miji-global-search relative w-full max-w-[360px]">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          commitFromCurrentInput();
        }}
        className="flex h-10 items-center gap-2 rounded-2xl border border-[#2B313C] bg-[#111318] px-3 text-[#E6EDF3] backdrop-blur-md transition focus-within:border-amber-400/30 focus-within:shadow-[0_0_0_1px_rgba(251,191,36,0.15)]"
      >
        <Search size={16} className="text-[#9BA7B4]" />
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
          className="min-w-0 flex-1 bg-transparent font-mono text-sm uppercase text-[#E6EDF3] outline-none placeholder:text-[#6E7681]"
        />
        {loading && <Loader2 size={15} className="animate-spin text-amber-200" />}
      </form>
      {overlay}
    </div>
  );
}
