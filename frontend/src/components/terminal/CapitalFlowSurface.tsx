"use client";

import { ChevronRight } from "lucide-react";
import { HeatStrip, StatusDot, ThemeIcon } from "./Scanability";

export interface CapitalFlowNode {
  id: string;
  label: string;
  strength?: number | null;
  flow?: number | null;
  risk?: number | null;
}

export interface CapitalFlowLane {
  id: string;
  label: string;
  rank?: number;
  strength?: number | null;
  beneficiaries?: string[];
  state?: string | null;
}

interface CapitalFlowSurfaceProps {
  source: CapitalFlowNode;
  lanes: CapitalFlowLane[];
  selectedId?: string;
  onPreview?: (lane: CapitalFlowLane) => void;
  onPreviewEnd?: () => void;
  onSelect?: (lane: CapitalFlowLane) => void;
  onDrilldown?: (lane: CapitalFlowLane) => void;
  className?: string;
  depth?: "flat" | "institutional";
}

export default function CapitalFlowSurface({ source, lanes, selectedId, onPreview, onPreviewEnd, onSelect, onDrilldown, className = "", depth = "institutional" }: CapitalFlowSurfaceProps) {
  return (
    <div className={`capital-flow-surface ${className}`} data-depth={depth}>
      <div className="capital-flow-source">
        <ThemeIcon theme={source.label} />
        <strong>{source.label}</strong>
        <span>Strength {typeof source.strength === "number" ? source.strength.toFixed(0) : "--"}</span>
        <span>Flow {typeof source.flow === "number" ? source.flow.toFixed(0) : "--"}</span>
        <span>Risk {typeof source.risk === "number" ? source.risk.toFixed(0) : "--"}</span>
      </div>
      <ChevronRight size={18} className="capital-flow-arrow" />
      <div className="capital-flow-lanes">
        {lanes.map((lane) => (
          <button
            key={lane.id}
            type="button"
            className="capital-flow-lane"
            data-selected={selectedId === lane.id}
            data-strongest={lane.rank === 1}
            onMouseEnter={() => onPreview?.(lane)}
            onMouseLeave={onPreviewEnd}
            onFocus={() => onPreview?.(lane)}
            onBlur={onPreviewEnd}
            onClick={() => onSelect?.(lane)}
            onDoubleClick={() => onDrilldown?.(lane)}
          >
            <span className="capital-flow-lane-label"><b>#{lane.rank ?? "–"}</b>{lane.label}</span>
            <HeatStrip value={lane.strength} className="w-full" />
            <span className="capital-flow-beneficiaries">{lane.beneficiaries?.join(" · ") || "Mapping"}</span>
            <StatusDot state={lane.state ?? "live"} />
          </button>
        ))}
      </div>
    </div>
  );
}
