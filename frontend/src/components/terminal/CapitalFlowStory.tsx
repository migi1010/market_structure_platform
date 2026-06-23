"use client";

import { buildRotationStory } from "@/lib/researchNarrative";
import type { SectorRotation } from "@/types/stock";
import { BilingualLabel } from "./Scanability";

export default function CapitalFlowStory({ sector }: { sector: SectorRotation | null }) {
  const story = buildRotationStory(sector);
  return (
    <section className="capital-flow-story" aria-label="Capital Flow Story">
      <header>
        <BilingualLabel zh={story.title.zh} en={story.title.en} inline />
        <span>證據不足 / Insufficient evidence when links are unavailable</span>
      </header>
      <div>
        {story.steps.map((item, index) => (
          <article key={`${item.kind}:${item.sourceField}:${index}`} data-availability={item.availabilityState}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            <span><strong>{item.labelZh}</strong><small>{item.labelEn}</small></span>
            <p>{item.value}</p>
            <code>{item.sourceType} · {item.sourceField}</code>
          </article>
        ))}
      </div>
    </section>
  );
}
