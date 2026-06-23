"use client";

import { buildDependencyStory } from "@/lib/researchNarrative";
import type { ThemeIndustrialIntelligence } from "@/types/stock";
import { BilingualLabel } from "../terminal";

export default function DependencyStoryPanel({ graph }: { graph: ThemeIndustrialIntelligence["graph"] }) {
  const story = buildDependencyStory(graph);
  return (
    <section className="dependency-story-panel" aria-label="Dependency Story">
      <header>
        <BilingualLabel zh="依賴敘事" en="Dependency Story" inline />
        <span>證據鏈 / Evidence Chain · {story.pathId ?? "active graph"}</span>
      </header>
      <div className="dependency-story-chain">
        {story.edges.length > 0 ? story.edges.map((edge, index) => (
          <article key={`${edge.sourceKey}:${edge.relationshipType}:${edge.targetKey}`}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            <span><strong>{edge.sourceLabel}</strong><small>{edge.relationshipType.replaceAll("_", " ")}</small></span>
            <i>→</i>
            <span><strong>{edge.targetLabel}</strong><small>{edge.sourceType} · {edge.sourceField}</small></span>
            <code>evidence {edge.evidenceIds.join(", ") || "不可用"}</code>
          </article>
        )) : (
          <p className="workflow-unavailable">證據不足 / Insufficient evidence</p>
        )}
      </div>
    </section>
  );
}
