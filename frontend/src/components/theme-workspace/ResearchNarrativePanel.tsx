"use client";

import { buildThemeNarrative } from "@/lib/researchNarrative";
import type { ThemeAggregateResponse } from "@/types/stock";
import { BilingualLabel } from "../terminal";

function evidenceLabel(ids: Array<number | string>): string {
  return ids.length > 0 ? ids.join(", ") : "不可用";
}

export default function ResearchNarrativePanel({ aggregate }: { aggregate: ThemeAggregateResponse }) {
  const narrative = buildThemeNarrative(aggregate);
  return (
    <section className="research-narrative-panel" aria-label="Research Narrative">
      <header>
        <BilingualLabel zh={narrative.title.zh} en={narrative.title.en} inline />
        <span>證據鏈 / Evidence Chain</span>
      </header>
      <div className="research-narrative-chain">
        {narrative.steps.length > 0 ? narrative.steps.map((item, index) => (
          <article key={`${item.kind}:${item.sourceField}:${index}`} data-availability={item.availabilityState}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            <span>
              <strong>{item.labelZh}</strong>
              <small>{item.labelEn}</small>
            </span>
            <p>{item.value}</p>
            <code>{item.sourceType} · {item.sourceField}</code>
            <em>evidence {evidenceLabel(item.evidenceIds)}</em>
          </article>
        )) : (
          <p className="workflow-unavailable">證據不足 / Insufficient evidence</p>
        )}
      </div>
    </section>
  );
}
