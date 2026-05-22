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
    <section className="rounded-2xl border border-[#2B313C] bg-[#161B22]/95 p-5 shadow-[0_4px_24px_rgba(0,0,0,0.25)] backdrop-blur-xl">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-amber-200">Live Intelligence Feed</p>
          <h3 className="text-lg font-black text-[#E6EDF3]">News Intelligence</h3>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-[#2B313C] bg-[#0A0C10] px-3 py-2">
          <Newspaper className="text-amber-200" size={18} />
          <span className={sentiment === "Bullish" ? "text-emerald-300" : sentiment === "Bearish" ? "text-rose-300" : "text-[#C9D1D9]"}>
            {sentiment}
          </span>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-xl border border-[#2B313C] bg-[#0A0C10] p-5 text-sm text-[#9BA7B4]">No News</div>
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <a
              key={`${item?.title ?? "news"}-${index}`}
              href={item?.link ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="group block rounded-xl border border-[#2B313C] bg-[#0A0C10] p-4 transition hover:border-amber-400/20 hover:bg-[#161B22]"
            >
              <div className="mb-2 flex items-start justify-between gap-3">
                <h4 className="text-sm font-bold leading-5 text-[#E6EDF3] group-hover:text-amber-200">{item?.title ?? "No News"}</h4>
                <ExternalLink size={14} className="mt-1 shrink-0 text-[#6E7681] group-hover:text-amber-200" />
              </div>
              <p className="line-clamp-2 text-xs leading-5 text-[#9BA7B4]">{item?.summary ?? ""}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-widest">
                <span className="rounded border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-amber-200">{item?.category ?? "General"}</span>
                <span className="text-[#6E7681]">{item?.publisher ?? "Market News"}</span>
                <span className={item?.sentiment === "Bullish" ? "text-emerald-300" : item?.sentiment === "Bearish" ? "text-rose-300" : "text-[#C9D1D9]"}>
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
