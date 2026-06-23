"use client";

import { buildScoutHypothesisNarrative } from "@/lib/researchNarrative";
import type { ThemeScoutCandidate } from "@/types/stock";
import { BilingualLabel } from "../terminal";

export default function ScoutHypothesisPanel({ candidate }: { candidate: ThemeScoutCandidate }) {
  const narrative = buildScoutHypothesisNarrative(candidate);
  return (
    <section className="scout-hypothesis-panel" aria-label="Scout Research Hypothesis">
      <header>
        <BilingualLabel zh={narrative.title.zh} en={narrative.title.en} inline />
        <span>Scout hypotheses are not graph constraints</span>
      </header>
      <div>
        {narrative.steps.map((item, index) => (
          <article key={`${item.kind}:${item.sourceField}:${index}`} data-kind={item.kind}>
            <b>{String(index + 1).padStart(2, "0")}</b>
            <span><strong>{item.labelZh}</strong><small>{item.labelEn}</small></span>
            <p>{item.value}</p>
            <code>{item.evidenceIds.join(", ") || "不可用"}</code>
          </article>
        ))}
      </div>
    </section>
  );
}
