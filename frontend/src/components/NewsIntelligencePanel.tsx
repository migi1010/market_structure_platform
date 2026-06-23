"use client";

import { ExternalLink, Newspaper } from "lucide-react";
import type { NewsItem } from "@/types/stock";

interface NewsIntelligencePanelProps {
  news?: NewsItem[];
}

export default function NewsIntelligencePanel({ news = [] }: NewsIntelligencePanelProps) {
  const items = news?.slice(0, 6) ?? [];
  const sentimentScore = items.reduce((acc, item) => {
    if (item?.sentiment === "Bullish") return acc + 1;
    if (item?.sentiment === "Bearish") return acc - 1;
    return acc;
  }, 0);
  const sentiment = sentimentScore > 0 ? "Bullish" : sentimentScore < 0 ? "Bearish" : "Neutral";

  return (
    <section className="terminal-panel p-5">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="terminal-micro-label">Live Intelligence Feed</p>
          <h3 className="terminal-panel-title text-[var(--theme-text)]">News Intelligence</h3>
        </div>
        <div className="flex items-center gap-2 border-l border-[var(--theme-divider)] pl-3">
          <Newspaper className="text-[var(--theme-warning)]" size={18} />
          <span className={sentiment === "Bullish" ? "text-[var(--theme-bullish)]" : sentiment === "Bearish" ? "text-[var(--theme-bearish)]" : "text-[var(--theme-text-secondary)]"}>
            {sentiment}
          </span>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="border-y border-[var(--theme-divider)] py-5 text-sm text-[var(--theme-muted)]">No News</div>
      ) : (
        <div className="divide-y divide-[var(--theme-divider)]">
          {items.map((item, index) => (
            <a
              key={`${item?.title ?? "news"}-${index}`}
              href={item?.link ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="group block py-3 transition hover:bg-[rgba(255,255,255,0.028)]"
            >
              <div className="mb-2 flex items-start justify-between gap-3">
                <h4 className="text-sm font-bold leading-5 text-[var(--theme-text)] group-hover:text-[var(--theme-highlight)]">{item?.title ?? "No News"}</h4>
                <ExternalLink size={14} className="mt-1 shrink-0 text-[var(--theme-muted)] group-hover:text-[var(--theme-highlight)]" />
              </div>
              <p className="line-clamp-2 text-xs leading-5 text-[var(--theme-text-secondary)]">{item?.summary ?? ""}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
                <span className="text-[var(--theme-warning)]">{item?.category ?? "General"}</span>
                <span className="text-[var(--theme-muted)]">{item?.publisher ?? "Market News"}</span>
                <span className={item?.sentiment === "Bullish" ? "text-[var(--theme-bullish)]" : item?.sentiment === "Bearish" ? "text-[var(--theme-bearish)]" : "text-[var(--theme-text-secondary)]"}>
                  {item?.sentiment ?? "Neutral"}
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
