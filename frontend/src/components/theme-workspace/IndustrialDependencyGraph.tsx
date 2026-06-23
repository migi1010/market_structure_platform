"use client";

import { useEffect, useMemo, useState } from "react";
import {
  projectIndustrialGraph,
  type IndustrialGraphRoleContext,
  type ProjectedIndustrialEdge,
} from "@/lib/industrialGraphProjection";
import type { DrilldownTarget } from "@/lib/drilldown";
import type { ThemeAggregateResponse, ThemeIndustrialIntelligence } from "@/types/stock";
import { BilingualLabel } from "../terminal";

function edgeFamily(relationshipType: string): string {
  if (relationshipType.includes("LIMIT") || relationshipType.includes("CONSTRAINT")) return "bottleneck";
  if (relationshipType.includes("CONTROL")) return "control";
  if (relationshipType.includes("RESOLV")) return "resolution";
  if (relationshipType.includes("DEPEND") || relationshipType.includes("REQUIR") || relationshipType.includes("SUPPL")) return "dependency";
  return "neutral";
}

function curve(edge: ProjectedIndustrialEdge): string {
  const bend = Math.max(34, Math.abs(edge.x2 - edge.x1) * 0.36);
  const direction = edge.x2 >= edge.x1 ? 1 : -1;
  return `M ${edge.x1} ${edge.y1} C ${edge.x1 + bend * direction} ${edge.y1}, ${edge.x2 - bend * direction} ${edge.y2}, ${edge.x2} ${edge.y2}`;
}

function companyKey(ticker: string | null | undefined): string | null {
  const normalized = ticker?.trim().toUpperCase();
  return normalized ? `company:${normalized}` : null;
}

function roleContext(
  controllers: ThemeIndustrialIntelligence["controllers"],
  beneficiaries: ThemeAggregateResponse["beneficiaries"],
): IndustrialGraphRoleContext {
  const controllerCompanyKeys = new Set(controllers.map((row) => row.company_key));
  const beneficiaryCompanyKeys = new Set(
    [...beneficiaries.direct_beneficiaries, ...beneficiaries.indirect_beneficiaries]
      .map((row) => companyKey(row.ticker))
      .filter((key): key is string => Boolean(key)),
  );
  const resolutionEnablerCompanyKeys = new Set(
    beneficiaries.resolution_enablers
      .map((row) => companyKey(row.ticker))
      .filter((key): key is string => Boolean(key)),
  );
  return { controllerCompanyKeys, beneficiaryCompanyKeys, resolutionEnablerCompanyKeys };
}

function edgeKey(edge: ProjectedIndustrialEdge): string {
  return `${edge.sourceKey}:${edge.relationshipType}:${edge.targetKey}`;
}

export default function IndustrialDependencyGraph({
  graph,
  controllers,
  beneficiaries,
  selectedNodeKey: persistedSelectedNodeKey,
  onSelectedNodeChange,
  onPreview,
  onPreviewEnd,
  onContext,
  onDrilldown,
}: {
  graph: ThemeIndustrialIntelligence["graph"];
  controllers: ThemeIndustrialIntelligence["controllers"];
  beneficiaries: ThemeAggregateResponse["beneficiaries"];
  selectedNodeKey?: string | null;
  onSelectedNodeChange?: (nodeKey: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}) {
  const projection = useMemo(
    () => projectIndustrialGraph(graph, roleContext(controllers, beneficiaries)),
    [beneficiaries, controllers, graph],
  );
  const [selectedNodeKey, setSelectedNodeKey] = useState<string | null>(persistedSelectedNodeKey ?? null);
  const [selectedEdgeKey, setSelectedEdgeKey] = useState<string | null>(null);
  const [hoveredEdgeKey, setHoveredEdgeKey] = useState<string | null>(null);
  const selectedEdge = projection.edges.find((edge) => edgeKey(edge) === selectedEdgeKey) ?? null;
  const nodeNames = new Map(projection.nodes.map((node) => [node.node.canonical_key, node.node.display_name]));

  useEffect(() => {
    if (persistedSelectedNodeKey) setSelectedNodeKey(persistedSelectedNodeKey);
  }, [persistedSelectedNodeKey]);

  const targetForNode = (projected: (typeof projection.nodes)[number]): DrilldownTarget => ({
    kind: "supply",
    name: projected.node.display_name,
    label: projected.node.display_name,
    subject: projected.node.node_type,
    meta: projected.node.canonical_key,
  });

  return (
    <section className="industrial-dependency-graph" aria-label="Persisted industrial dependency graph">
      <header>
        <span><BilingualLabel zh="產業依賴圖" en="Industrial Dependency Map" inline /><small>瓶頸中心 · persisted edges only</small></span>
        <b>{projection.nodes.length} nodes · {projection.edges.length} relationships · {graph.evidence_count} evidence</b>
      </header>

      <div className="industrial-graph-zone-labels" aria-hidden="true">
        <span><strong>上游依賴</strong><small>Upstream Dependencies</small></span>
        <span><strong>關鍵瓶頸</strong><small>Bottleneck Anchor</small></span>
        <span><strong>控制與受益角色</strong><small>Controllers, Enablers, Beneficiaries</small></span>
      </div>

      <div className="industrial-graph-canvas">
        <div style={{ width: projection.width, height: projection.height }}>
          <svg viewBox={`0 0 ${projection.width} ${projection.height}`} role="img" aria-label="Evidence-backed industrial relationships">
            <defs>
              {["dependency", "bottleneck", "control", "resolution", "neutral"].map((family) => (
                <marker key={family} id={`industrial-arrow-${family}`} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
                  <path d="M0,0 L7,3.5 L0,7 z" className={`industrial-edge-${family}`} />
                </marker>
              ))}
            </defs>
            {projection.edges.map((edge) => {
              const key = edgeKey(edge);
              const family = edgeFamily(edge.relationshipType);
              const selected = key === selectedEdgeKey || key === hoveredEdgeKey;
              const incident = selectedNodeKey
                ? edge.sourceKey === selectedNodeKey || edge.targetKey === selectedNodeKey
                : edge.focus || edge.anchor;
              const muted = selectedNodeKey
                ? !incident
                : Boolean(selectedEdgeKey) && key !== selectedEdgeKey;
              return (
                <g
                  key={key}
                  role="button"
                  tabIndex={0}
                  data-relationship={edge.relationshipType}
                  data-active={selected || incident}
                  data-muted={muted}
                  onClick={() => setSelectedEdgeKey(key)}
                  onFocus={() => setHoveredEdgeKey(key)}
                  onBlur={() => setHoveredEdgeKey(null)}
                  onMouseEnter={() => setHoveredEdgeKey(key)}
                  onMouseLeave={() => setHoveredEdgeKey(null)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") setSelectedEdgeKey(key);
                  }}
                >
                  <path
                    d={curve(edge)}
                    className={`industrial-edge industrial-edge-${family}`}
                    markerEnd={`url(#industrial-arrow-${family})`}
                  />
                  <title>{`${edge.relationshipType} · evidence ${edge.evidenceIds.join(", ") || "unavailable"}`}</title>
                </g>
              );
            })}
          </svg>

          {projection.companyGroups.map((group) => {
            const first = group.nodes[0];
            return first ? (
              <span
                key={group.role}
                className="industrial-company-group-label"
                style={{ left: first.x, top: Math.max(48, first.y - 18) }}
              >
                <strong>{group.labelZh}</strong><small>{group.labelEn}</small>
              </span>
            ) : null;
          })}

          {projection.nodes.map((projected) => (
            <button
              key={projected.node.canonical_key}
              type="button"
              className="industrial-graph-node"
              data-node-type={projected.node.node_type}
              data-zone={projected.zone}
              data-primary-bottleneck={projection.constraintAnchor?.node.canonical_key === projected.node.canonical_key}
              data-selected={selectedNodeKey === projected.node.canonical_key}
              style={{
                left: projected.x,
                top: projected.y,
                width: projected.width,
                height: projected.height,
              }}
              onClick={() => {
                setSelectedNodeKey((current) => current === projected.node.canonical_key ? null : projected.node.canonical_key);
                onSelectedNodeChange?.(projected.node.canonical_key);
                onContext?.(targetForNode(projected));
                setSelectedEdgeKey(null);
              }}
              onDoubleClick={() => onDrilldown?.(targetForNode(projected))}
              onMouseEnter={() => onPreview?.(targetForNode(projected))}
              onMouseLeave={onPreviewEnd}
              onFocus={() => onPreview?.(targetForNode(projected))}
              onBlur={onPreviewEnd}
              onKeyDown={(event) => {
                if (event.key !== "Enter") return;
                event.preventDefault();
                onDrilldown?.(targetForNode(projected));
              }}
            >
              <small>{projected.node.node_type}</small>
              <strong>{projected.node.display_name}</strong>
              <code>{projected.node.canonical_key}</code>
            </button>
          ))}

          {!projection.constraintAnchor && (
            <div className="industrial-missing-anchor">
              <strong>尚無已驗證瓶頸</strong><small>Verified bottleneck unavailable</small>
            </div>
          )}
        </div>
      </div>

      <aside className="industrial-edge-inspector" data-active={Boolean(selectedEdge)}>
        {selectedEdge ? (
          <>
            <span><small>關係 / Relationship</small><strong>{selectedEdge.relationshipType.replaceAll("_", " ")}</strong></span>
            <span><small>來源 / Source</small><strong>{nodeNames.get(selectedEdge.sourceKey) ?? selectedEdge.sourceKey}</strong></span>
            <span><small>目標 / Target</small><strong>{nodeNames.get(selectedEdge.targetKey) ?? selectedEdge.targetKey}</strong></span>
            <span><small>證據 / Evidence</small><strong>{selectedEdge.evidenceIds.join(", ") || "不可用"}</strong></span>
          </>
        ) : (
          <p>選取節點或關係以檢視已保存的方向與證據。 Select a node or relationship to inspect persisted direction and evidence.</p>
        )}
      </aside>
    </section>
  );
}
