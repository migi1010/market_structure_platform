"use client";

import { useState } from "react";
import type { FlowRankingRow, FlowRankingSort } from "@/lib/flowRanking";
import { HeatStrip, StatusDot, ThemeIcon, TickerLogo } from "./Scanability";

interface FlowRankingProps {
  rows: FlowRankingRow[];
  onSort?: (sort: FlowRankingSort) => void;
  onPreview?: (row: FlowRankingRow) => void;
  onPreviewEnd?: () => void;
  onSelect?: (row: FlowRankingRow) => void;
  onDrilldown?: (row: FlowRankingRow) => void;
}

const sorts: Array<{ id: FlowRankingSort; label: string }> = [
  { id: "flow", label: "Flow" },
  { id: "momentum", label: "Momentum" },
  { id: "score", label: "Score" },
];

function value(value: number | null): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "--";
}

export default function FlowRanking({ rows, onSort, onPreview, onPreviewEnd, onSelect, onDrilldown }: FlowRankingProps) {
  const [sort, setSort] = useState<FlowRankingSort>("flow");
  return (
    <div className="flow-ranking">
      <div className="flow-ranking-toolbar" aria-label="Flow ranking sort">
        {sorts.map((item) => (
          <button key={item.id} type="button" data-active={sort === item.id} onClick={() => { setSort(item.id); onSort?.(item.id); }}>{item.label}</button>
        ))}
      </div>
      <div className="flow-ranking-head"><span>#</span><span>Theme</span><span>Flow</span><span>Momentum</span><span>Beneficiaries</span></div>
      <div className="flow-ranking-rows">
        {rows.map((row) => (
          <button
            key={row.id}
            type="button"
            className="flow-ranking-row"
            data-active={row.active}
            onMouseEnter={() => onPreview?.(row)}
            onMouseLeave={onPreviewEnd}
            onFocus={() => onPreview?.(row)}
            onBlur={onPreviewEnd}
            onClick={() => onSelect?.(row)}
            onDoubleClick={() => onDrilldown?.(row)}
          >
            <strong className="flow-ranking-rank">{row.rank}</strong>
            <span className="flow-ranking-theme"><ThemeIcon theme={row.theme} /><span><strong>{row.theme}</strong><StatusDot state={row.state} label={row.state ?? "Theme"} /></span></span>
            <span className="flow-ranking-score">{value(row.flow)}<HeatStrip value={row.flow} /></span>
            <span className="flow-ranking-score">{value(row.momentum)}<HeatStrip value={row.momentum} /></span>
            <span className="flow-ranking-beneficiaries">{row.beneficiaries.slice(0, 3).map((stock) => <span key={stock.ticker}><TickerLogo ticker={stock.ticker} />{stock.ticker}</span>)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
