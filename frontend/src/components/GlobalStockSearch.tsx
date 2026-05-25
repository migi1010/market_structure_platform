"use client";

import { useEffect, useRef, useState } from "react";
import { Command as CommandIcon, Loader2, Plus, Search } from "lucide-react";
import { searchStocks } from "@/services/stockApi";
import type { SearchResult } from "@/types/stock";

interface GlobalStockSearchProps {
  onSelect: (symbol: string) => void;
  onSelectResult?: (result: SearchResult) => void;
  onAddToWatchlist?: (symbol: string) => void;
  placeholder?: string;
}

const RECENT_KEY = "miji:recent-searches";
const RECENT_SCHEMA_VERSION = "stock_v6";

interface RecentEnvelope {
  schema_version: string;
  data: SearchResult[];
}

function normalizeRecentItem(item: SearchResult): SearchResult | null {
  const symbol = item.symbol?.trim().toUpperCase();
  if (!symbol) return null;
  const price = typeof item.price === "number" && Number.isFinite(item.price) && item.price > 0 ? item.price : null;
  const changePercent = typeof item.change_percent === "number" && Number.isFinite(item.change_percent) ? item.change_percent : null;
  return {
    ...item,
    symbol,
    price,
    change_percent: changePercent,
  };
}

function readRecent(): SearchResult[] {
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed) || (parsed as RecentEnvelope).schema_version !== RECENT_SCHEMA_VERSION) {
      window.localStorage.removeItem(RECENT_KEY);
      return [];
    }
    const data = (parsed as RecentEnvelope).data;
    if (!Array.isArray(data)) {
      window.localStorage.removeItem(RECENT_KEY);
      return [];
    }
    return data.map(normalizeRecentItem).filter((item): item is SearchResult => item !== null).slice(0, 6);
  } catch {
    window.localStorage.removeItem(RECENT_KEY);
    return [];
  }
}

function writeRecent(item: SearchResult): void {
  try {
    const normalized = normalizeRecentItem(item);
    if (!normalized) return;
    const next = [normalized, ...readRecent().filter((entry) => entry.symbol !== normalized.symbol)].slice(0, 6);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify({ schema_version: RECENT_SCHEMA_VERSION, data: next }));
  } catch {
    // Recent search cache is best effort.
  }
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
  if (item.target_tab === "alpha-quant") return "Alpha Quant";
  if (item.target_tab === "portfolio") return "Portfolio";
  if (item.target_tab === "theme-intelligence") return "Theme Intelligence";
  if (item.target_tab === "market-intel") return "Sector Rotation";
  return "Stock Analysis";
}

function canAddToWatchlist(item: SearchResult): boolean {
  const group = getResultGroup(item);
  const type = item.type?.toLowerCase();
  return group === "Stocks" && !["theme", "sector", "command"].includes(type);
}

export default function GlobalStockSearch({ onSelect, onSelectResult, onAddToWatchlist, placeholder = "Search ticker, theme, sector, ETF..." }: GlobalStockSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recent, setRecent] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const composingRef = useRef(false);

  useEffect(() => {
    setRecent(readRecent());
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
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

  useEffect(() => {
    function onPointerDown(event: MouseEvent | TouchEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown, { passive: true });
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
    };
  }, []);

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
    writeRecent(normalizedItem);
    setRecent(readRecent());
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

  const visibleResults = (results?.length ?? 0) > 0 ? results : query ? [] : recent;
  const groupedResults = visibleResults.reduce<Array<{ group: (typeof GROUP_ORDER)[number]; items: SearchResult[] }>>((acc, item) => {
    const group = getResultGroup(item);
    const existing = acc.find((entry) => entry.group === group);
    if (existing) existing.items.push(item);
    else acc.push({ group, items: [item] });
    return acc;
  }, []);

  useEffect(() => {
    setActiveIndex((idx) => Math.min(Math.max(visibleResults.length - 1, 0), idx));
  }, [visibleResults.length]);

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

      {open && (
        <div className="miji-search-results absolute right-0 top-12 z-[90] max-h-[min(70vh,28rem)] w-[min(92vw,560px)] min-w-full overflow-y-auto rounded-2xl border border-[#2B313C] bg-[#0A0C10]/95 p-2 shadow-[0_18px_48px_rgba(0,0,0,0.42)] backdrop-blur-md">
          {(visibleResults?.length ?? 0) === 0 ? (
            <button
              onPointerDown={(event) => {
                event.preventDefault();
                commit(query);
              }}
              className="w-full rounded-xl px-3 py-3 text-left font-mono text-sm text-[#C9D1D9] hover:bg-[#161B22]"
            >
              Analyze {query || "ticker"}
            </button>
          ) : (
            <>
            {!query && recent.length > 0 && <div className="px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">Recent Searches</div>}
            {groupedResults.map(({ group, items }) => (
              <div key={group} className="pb-1">
                <div className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-[#6E7681]">{group}</div>
                {items.map((item) => {
                  const index = visibleResults.indexOf(item);
                  const title = getResultTitle(item);
                  const description = getResultDescription(item);
                  const target = getTargetLabel(item);
                  const symbolLabel = item.ticker ?? item.symbol;
                  return (
                    <div
                      key={`${item.symbol}-${item.exchange}-${item.target_tab ?? item.type}`}
                      className={`rounded-xl px-3 py-3 transition ${activeIndex === index ? "bg-[#161B22]" : "hover:bg-[#111318]"}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <button
                          onPointerDown={(event) => {
                            event.preventDefault();
                            commitResult(item);
                          }}
                          className="min-w-0 flex-1 text-left"
                        >
                          <div className="flex min-w-0 items-center justify-between gap-3">
                            <span className="truncate font-mono text-sm font-semibold text-[#E6EDF3]">{symbolLabel}</span>
                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-widest text-amber-200">{item?.exchange ?? "US"}</span>
                          </div>
                          <div className="mt-1 flex min-w-0 items-center justify-between gap-3 text-xs">
                            <span className="min-w-0 truncate text-[#C9D1D9]">{title}</span>
                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[#9BA7B4]">{target}</span>
                          </div>
                          <div className="mt-1 flex min-w-0 items-center justify-between gap-3 text-xs">
                            <span className="truncate text-[#9BA7B4]">{description}</span>
                            {typeof item?.price === "number" && item.price > 0 && (
                              <span className="shrink-0 font-mono text-[#C9D1D9]">
                                ${item.price.toFixed(2)}
                                {typeof item.change_percent === "number" && (
                                  <span className={item.change_percent >= 0 ? "ml-2 text-emerald-300" : "ml-2 text-rose-300"}>
                                    {item.change_percent >= 0 ? "+" : ""}{item.change_percent.toFixed(2)}%
                                  </span>
                                )}
                              </span>
                            )}
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
                            className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-amber-400/20 px-2 py-1 text-[10px] font-semibold text-amber-200 hover:bg-amber-400/10"
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
            ))}
            </>
          )}
          <div className="flex items-center gap-2 px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-[#6E7681]">
            <CommandIcon size={11} />
            <span>Ctrl/Cmd+K</span>
          </div>
        </div>
      )}
    </div>
  );
}
