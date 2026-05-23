"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Plus, Search } from "lucide-react";
import { searchStocks } from "@/services/stockApi";
import type { SearchResult } from "@/types/stock";

interface GlobalStockSearchProps {
  onSelect: (symbol: string) => void;
  onSelectResult?: (result: SearchResult) => void;
  onAddToWatchlist?: (symbol: string) => void;
  placeholder?: string;
}

const RECENT_KEY = "miji:recent-searches";

function readRecent(): SearchResult[] {
  try {
    return JSON.parse(window.localStorage.getItem(RECENT_KEY) ?? "[]") as SearchResult[];
  } catch {
    return [];
  }
}

function writeRecent(item: SearchResult): void {
  try {
    const next = [item, ...readRecent().filter((entry) => entry.symbol !== item.symbol)].slice(0, 6);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // Recent search cache is best effort.
  }
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
    const exact = results.find((item) => item.symbol.trim().toUpperCase() === normalized);
    const selected = results?.[activeIndex];
    if (exact) commitResult(exact);
    else if (selected) commitResult(selected);
    else commit(normalized);
  };

  const visibleResults = (results?.length ?? 0) > 0 ? results : query ? [] : recent;

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
              setActiveIndex((idx) => Math.min((results?.length ?? 1) - 1, idx + 1));
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
        <div className="miji-search-results absolute right-0 top-12 z-50 max-h-96 w-full overflow-y-auto rounded-2xl border border-[#2B313C] bg-[#0A0C10]/95 p-2 shadow-[0_18px_48px_rgba(0,0,0,0.42)] backdrop-blur-md">
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
            {visibleResults.map((item, index) => (
              <div
                key={`${item.symbol}-${item.exchange}`}
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
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-mono text-sm font-semibold text-[#E6EDF3]">{item?.symbol ?? ""}</span>
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-200">{item?.exchange ?? "US"}</span>
                    </div>
                    <div className="mt-1 truncate text-xs text-[#9BA7B4]">{item?.name ?? item?.type ?? "Equity"}</div>
                  </button>
                  {onAddToWatchlist && !["Theme", "Sector"].includes(item.type) && (
                    <button
                      type="button"
                      onPointerDown={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        onAddToWatchlist(item.symbol);
                      }}
                      className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-amber-400/20 px-2 py-1 text-[10px] font-semibold text-amber-200 hover:bg-amber-400/10"
                    >
                      <Plus size={12} />
                      Add to Watchlist
                    </button>
                  )}
                </div>
              </div>
            ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
