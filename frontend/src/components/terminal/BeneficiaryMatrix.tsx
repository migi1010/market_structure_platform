"use client";

import { HeatStrip, TickerLogo } from "./Scanability";
import { ChangeCell, MarketCell, MarketRow, MarketTable, NumericCell, TickerCell } from "./MarketTable";

export interface BeneficiaryMatrixRow {
  ticker: string;
  company?: string;
  alpha?: number | null;
  risk?: number | null;
  flow?: number | null;
  relativeStrength?: number | null;
  exposure?: number | null;
}

interface BeneficiaryMatrixProps {
  rows: BeneficiaryMatrixRow[];
  contextLabel?: string;
  selectedTicker?: string;
  onPreview?: (row: BeneficiaryMatrixRow) => void;
  onPreviewEnd?: () => void;
  onSelect?: (row: BeneficiaryMatrixRow) => void;
  onDrilldown?: (row: BeneficiaryMatrixRow) => void;
  density?: "compact" | "terminal";
}

const COLUMNS = "74px minmax(130px,1fr) 50px 50px 50px 50px 96px";

export default function BeneficiaryMatrix({ rows, contextLabel = "selected context", selectedTicker, onPreview, onPreviewEnd, onSelect, onDrilldown, density = "terminal" }: BeneficiaryMatrixProps) {
  return (
    <MarketTable
      columns={COLUMNS}
      density={density === "terminal" ? "compact" : "normal"}
      className="beneficiary-matrix"
      header={<><MarketCell>Ticker</MarketCell><MarketCell>Company</MarketCell><NumericCell>Alpha</NumericCell><NumericCell>Risk</NumericCell><NumericCell>Flow</NumericCell><NumericCell>RS</NumericCell><MarketCell>Exposure</MarketCell></>}
    >
      {rows.length === 0 ? <div className="beneficiary-matrix-empty"><strong>No beneficiaries for {contextLabel}</strong><span>Current selection has no beneficiary payload.</span></div> : rows.map((row) => (
        <MarketRow
          key={row.ticker}
          columns={COLUMNS}
          selected={selectedTicker === row.ticker}
          onPreview={() => onPreview?.(row)}
          onPreviewEnd={onPreviewEnd}
          onClick={() => onSelect?.(row)}
          onDoubleClick={() => onDrilldown?.(row)}
        >
          <TickerCell><span className="flex items-center gap-2"><TickerLogo ticker={row.ticker} />{row.ticker}</span></TickerCell>
          <MarketCell className="truncate text-xs text-[var(--theme-text-secondary)]">{row.company ?? row.ticker}</MarketCell>
          <NumericCell>{format(row.alpha)}</NumericCell>
          <ChangeCell value={riskDirection(row.risk)}>{format(row.risk)}</ChangeCell>
          <NumericCell>{format(row.flow)}</NumericCell>
          <NumericCell>{format(row.relativeStrength)}</NumericCell>
          <MarketCell><HeatStrip value={row.exposure} className="w-full" /></MarketCell>
        </MarketRow>
      ))}
    </MarketTable>
  );
}

function format(value?: number | null): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "--";
}

function riskDirection(value?: number | null): number | null {
  return typeof value === "number" && Number.isFinite(value) ? 50 - value : null;
}
