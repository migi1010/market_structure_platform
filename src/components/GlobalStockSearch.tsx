"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Plus, Search } from "lucide-react";
import { searchStocks } from "@/services/stockApi";
import type { SearchResult } from "@/types/stock";

interface GlobalStockSearchProps {
  onSelect: (symbol: string) => void;
  onAddToWatchlist?: (symbol: string) => void;
  placeholder?: string;
}

export default function GlobalStockSearch({ onSelect, onAddToWatchlist, placeholder = "Search any US ticker..." }: GlobalStockSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);

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
    }, 160);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const commit = (symbol: string) => {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized) return;
    setQuery("");
    setOpen(false);
    onSelect(normalized);
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-[360px]">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          commit(results?.[activeIndex]?.symbol ?? query);
        }}
        className="flex h-10 items-center gap-2 rounded-2xl border border-[#2B313C] bg-[#111318] px-3 text-[#E6EDF3] backdrop-blur-md transition focus-within:border-amber-400/30 focus-within:shadow-[0_0_0_1px_rgba(251,191,36,0.15)]"
      >
        <Search size={16} className="text-[#9BA7B4]" />
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value.toUpperCase());
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
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
        <div className="absolute right-0 top-12 z-50 max-h-96 w-full overflow-y-auto rounded-2xl border border-[#2B313C] bg-[#0A0C10]/95 p-2 shadow-[0_18px_48px_rgba(0,0,0,0.42)] backdrop-blur-md">
          {(results?.length ?? 0) === 0 ? (
            <button onMouseDown={() => commit(query)} className="w-full rounded-xl px-3 py-3 text-left font-mono text-sm text-[#C9D1D9] hover:bg-[#161B22]">
              Analyze {query || "ticker"}
            </button>
          ) : (
            results.map((item, index) => (
              <div
                key={`${item.symbol}-${item.exchange}`}
                className={`rounded-xl px-3 py-3 transition ${activeIndex === index ? "bg-[#161B22]" : "hover:bg-[#111318]"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <button onMouseDown={() => commit(item.symbol)} className="min-w-0 flex-1 text-left">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-mono text-sm font-semibold text-[#E6EDF3]">{item?.symbol ?? ""}</span>
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-200">{item?.exchange ?? "US"}</span>
                    </div>
                    <div className="mt-1 truncate text-xs text-[#9BA7B4]">{item?.name ?? item?.type ?? "Equity"}</div>
                  </button>
                  {onAddToWatchlist && (
                    <button
                      type="button"
                      onMouseDown={(event) => {
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
            ))
          )}
        </div>
      )}
    </div>
  );
}
