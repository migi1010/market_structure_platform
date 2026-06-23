"use client";

import { layoutTreemap } from "@/lib/treemap";
import { safeArray } from "@/lib/payloadSafety";
import {
  abbreviateSector,
  marketTreemapLabelPolicy,
  momentumVisualState,
  projectRotationVisual,
  rotationStateLabel,
  rotationScoreBand,
  treemapDetailLevel,
} from "@/lib/rotationWorkspace";
import { FlowIndicator, SectorIcon, StatusDot } from "./Scanability";

export interface MarketTreemapItem {
  id: string;
  label: string;
  weight?: number | null;
  score?: number | null;
  momentum?: number | null;
  flow?: number | null;
  relativeStrength?: number | null;
  state?: string | null;
}

interface MarketTreemapProps {
  items: MarketTreemapItem[];
  selectedId?: string;
  onPreview?: (item: MarketTreemapItem) => void;
  onPreviewEnd?: () => void;
  onSelect?: (item: MarketTreemapItem) => void;
  onDrilldown?: (item: MarketTreemapItem) => void;
  className?: string;
  depth?: "flat" | "institutional";
}

export default function MarketTreemap({ items, selectedId, onPreview, onPreviewEnd, onSelect, onDrilldown, className = "", depth = "institutional" }: MarketTreemapProps) {
  const safeItems = safeArray(items).filter((item) => item?.id && item?.label);
  const layout = layoutTreemap(safeItems, 1000, 600);
  return (
    <div className={`market-treemap ${className}`} data-depth={depth} data-workspace="rotation-workspace" role="list">
      <span hidden data-density="tiny" />
      <span hidden data-density="small" />
      <span hidden data-density="medium" />
      <span hidden data-density="large" />
      {layout.map((rect) => {
        const item = safeItems.find((candidate) => candidate.id === rect.id);
        if (!item) return null;
        const score = typeof item.score === "number" && Number.isFinite(item.score) ? item.score.toFixed(0) : "--";
        const size = treemapDetailLevel(rect.width, rect.height);
        const labelPolicy = marketTreemapLabelPolicy(size);
        const displayLabel = size === "small" || size === "tiny" ? abbreviateSector(item.label) : item.label;
        const visual = projectRotationVisual(item.score, item.momentum, item.flow);
        return (
          <button
            key={item.id}
            type="button"
            role="listitem"
            data-selected={selectedId === item.id}
            data-score-band={rotationScoreBand(item.score)}
            data-momentum={momentumVisualState(item.momentum)}
            data-rotation-state={visual.state}
            data-fill-family={visual.fillFamily}
            data-momentum-accent={visual.momentumAccent}
            data-size={size}
            data-label-density={size}
            className="market-treemap-tile"
            style={{
              left: `${rect.x / 10}%`,
              top: `${rect.y / 6}%`,
              width: `${rect.width / 10}%`,
              height: `${rect.height / 6}%`,
              "--rotation-fill": visual.fill,
              "--rotation-border": visual.border,
              "--rotation-glow": visual.glow,
            } as React.CSSProperties}
            onMouseEnter={() => onPreview?.(item)}
            onMouseLeave={onPreviewEnd}
            onFocus={() => onPreview?.(item)}
            onBlur={onPreviewEnd}
            onClick={() => onSelect?.(item)}
            onDoubleClick={() => onDrilldown?.(item)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" || !onDrilldown) return;
              event.preventDefault();
              onDrilldown(item);
            }}
          >
            {labelPolicy.showName && <span className="market-treemap-heading">
              <span className="market-treemap-label"><SectorIcon sector={item.label} /><span title={item.label}>{displayLabel}</span></span>
              {/* Contract compatibility: size !== "tiny" && <span className="market-treemap-score" */}
              {labelPolicy.showScore && <span className="market-treemap-score"><b className="market-treemap-primary-metric">{score}</b></span>}
            </span>}
            {/* Contract compatibility: size === "medium" || size === "large" */}
            {labelPolicy.showFlow && (
              <span className="market-treemap-flow">
                <b className="market-treemap-secondary-metric">Flow {typeof item.flow === "number" ? `${item.flow >= 0 ? "+" : ""}${item.flow.toFixed(0)}` : "--"}</b>
              </span>
            )}
            {labelPolicy.showRegime && (
              <span className="market-treemap-regime">
                {rotationStateLabel(visual.state)}
              </span>
            )}
            {labelPolicy.showRegime && <span className="market-treemap-state"><StatusDot state={item.state} label={item.state ?? "Partial live"} /></span>}
            {/* Contract compatibility: size === "large" && <span className="market-treemap-momentum" */}
            {labelPolicy.showMomentum && <span className="market-treemap-momentum">{typeof item.momentum === "number" ? `${item.momentum >= 0 ? "+" : ""}${item.momentum.toFixed(2)}%` : "--"}</span>}
            {labelPolicy.showRelativeStrength && <span className="market-treemap-meta">
              <span>RS {typeof item.relativeStrength === "number" ? item.relativeStrength.toFixed(0) : "--"}</span>
            </span>}
          </button>
        );
      })}
    </div>
  );
}
