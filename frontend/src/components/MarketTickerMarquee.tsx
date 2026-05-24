"use client";

import { memo, useEffect, useMemo, useState } from "react";
import { fetchMarketOverview } from "@/services/stockApi";
import type { MarketOverviewItem } from "@/types/stock";

const fallbackTape: MarketOverviewItem[] = [
  { ticker: "SPY", price: null, change: null, change_percent: null },
  { ticker: "QQQ", price: null, change: null, change_percent: null },
  { ticker: "SMH", price: null, change: null, change_percent: null },
  { ticker: "NVDA", price: null, change: null, change_percent: null },
  { ticker: "AAPL", price: null, change: null, change_percent: null },
  { ticker: "MSFT", price: null, change: null, change_percent: null },
];

function MarketTickerMarquee() {
  const [marketOverviewData, setMarketOverviewData] = useState<MarketOverviewItem[]>(fallbackTape);

  useEffect(() => {
    let cancelled = false;
    async function loadTape() {
      try {
        const result = await fetchMarketOverview();
        if (!cancelled && result?.length) setMarketOverviewData(result);
      } catch {
        if (!cancelled) setMarketOverviewData(fallbackTape);
      }
    }
    loadTape();
    const timer = window.setInterval(loadTape, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const tape = useMemo(() => [...marketOverviewData, ...marketOverviewData], [marketOverviewData]);

  return (
    <div className="miji-ticker-marquee flex h-8 items-center overflow-hidden border-b border-[#2A2F3D] bg-[#0B0E14]">
      <div className="miji-ticker-track animate-[ticker_42s_linear_infinite] whitespace-nowrap pl-6 font-mono text-[11px] tracking-wide will-change-transform">
        {tape.map((item, index) => {
          const price = typeof item?.price === "number" && Number.isFinite(item.price) && item.price > 0 ? item.price : null;
          const change = typeof item?.change === "number" && Number.isFinite(item.change) ? item.change : null;
          const pct = typeof item?.change_percent === "number" && Number.isFinite(item.change_percent) ? item.change_percent : null;
          const up = pct !== null && pct >= 0;
          return (
            <span key={`${item?.ticker ?? "T"}-${index}`} className="miji-ticker-item mr-10 inline-flex h-8 min-w-[148px] items-center gap-2 tabular-nums">
              <b className="text-[#E6EDF3]">{item?.ticker ?? "N/A"}</b>
              <span className="text-[#C9D1D9]">{price !== null ? price.toFixed(2) : "--"}</span>
              <span className={pct === null ? "text-[#6E7681]" : up ? "text-green-400" : "text-red-400"}>
                {pct === null || change === null ? "--" : `${up ? "UP" : "DN"} ${change >= 0 ? "+" : ""}${change.toFixed(2)}`}
              </span>
              <span className={pct === null ? "text-[#6E7681]" : up ? "text-green-400" : "text-red-400"}>
                {pct === null ? "--" : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default memo(MarketTickerMarquee);
