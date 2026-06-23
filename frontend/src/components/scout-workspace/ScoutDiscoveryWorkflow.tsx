"use client";

import { buildScoutVisualModel, scoutScore } from "@/lib/themeScout";
import type { DrilldownTarget } from "@/lib/drilldown";
import { findThemeRegistryEntry } from "@/lib/themeRegistry";
import type { ThemeRegistryEntry, ThemeScoutCandidate, ThemeScoutResponse } from "@/types/stock";
import { BilingualLabel } from "../terminal";
import ScoutHypothesisPanel from "./ScoutHypothesisPanel";

interface ScoutDiscoveryWorkflowProps {
  candidates: ThemeScoutCandidate[];
  selected: ThemeScoutCandidate;
  snapshot: NonNullable<ThemeScoutResponse["snapshot"]>;
  registryThemes?: ThemeRegistryEntry[];
  onSelect: (candidateKey: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

function companyDisplayLabel(company: { displayName?: string; canonicalKey: string }): string {
  return company.displayName?.trim()
    || (company.canonicalKey.startsWith("company:") ? company.canonicalKey.slice(8) : company.canonicalKey);
}

function companyEvidenceMetadata(company: { canonicalKey: string; evidenceId?: string; citation: string }): string {
  return [company.evidenceId, company.canonicalKey, company.citation].filter(Boolean).join(" · ");
}

function StageHeader({ zh, en, count }: { zh: string; en: string; count?: number | string }) {
  return <header><BilingualLabel zh={zh} en={en} inline />{count !== undefined && <span>{count}</span>}</header>;
}

export default function ScoutDiscoveryWorkflow({
  candidates,
  selected,
  snapshot,
  registryThemes = [],
  onSelect,
  onPreview,
  onPreviewEnd,
  onContext,
  onDrilldown,
}: ScoutDiscoveryWorkflowProps) {
  const visual = buildScoutVisualModel(selected);
  const noveltyUnavailable = selected.metrics.raw_values?.novelty_availability_state === "unavailable";
  const keyBottleneck = visual.bottlenecks[0]?.label ?? "Unavailable";
  const evidenceLinkedCompanies = visual.companies.slice(0, 4);
  const researchPriority = selected.readiness.overall >= 70
    ? "High"
    : selected.readiness.overall >= 40
      ? "Medium"
      : "Watch";

  return (
    <section className="scout-research-queue-workspace" aria-label="Theme Scout research workflow">
      <section className="scout-emerging-radar">
      {/* Contract compatibility: className="scout-candidate-selector" */}
      <nav className="scout-candidate-selector scout-candidate-selector-compact" aria-label="Scout candidate selector">
        <header><BilingualLabel zh="候選主題" en="Candidate Themes" inline /><b>{candidates.length}</b></header>
        {candidates.slice(0, 5).map((candidate) => {
          const registry = findThemeRegistryEntry(registryThemes, candidate.candidate_key.replace(/^candidate:/, "")) ?? findThemeRegistryEntry(registryThemes, candidate.name);
          const target: DrilldownTarget = {
            kind: "theme",
            name: registry?.theme_id ?? candidate.candidate_key.replace(/^candidate:/, ""),
            label: candidate.name,
            subject: registry?.theme_id ?? candidate.name,
            value: candidate.metrics.confidence,
            meta: candidate.status,
          };
          return (
          <button
            key={candidate.candidate_key}
            type="button"
            data-selected={candidate.candidate_key === selected.candidate_key}
            onMouseEnter={() => onPreview?.(target)}
            onMouseLeave={onPreviewEnd}
            onClick={() => {
              onSelect(candidate.candidate_key);
              onContext?.(target);
            }}
            onDoubleClick={() => onDrilldown?.(target)}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              onDrilldown?.(target);
            }}
          >
            <b>#{candidate.rank}</b><span><strong>{candidate.name}</strong><small>{registry ? `${registry.status} / ${registry.source}` : candidate.status}</small></span>
            <em>{candidate.evidence_count} evidence</em>
          </button>
        );})}
      </nav>
      </section>

      <section className="scout-research-command-surface">
      <section className="scout-top-candidate-summary" aria-label="Top Candidate">
        <header><BilingualLabel zh="主題候選" en="AI Top Candidate" inline /><span>{selected.status}</span></header>
        <div>
          <strong>{selected.name}</strong>
          <p>{selected.description}</p>
        </div>
        <dl>
          <span><dt>Research priority</dt><dd>{researchPriority}</dd></span>
          <span><dt>Confidence</dt><dd>{scoutScore(selected.metrics.confidence)}</dd></span>
          <span><dt>Coverage</dt><dd>{scoutScore(selected.metrics.coverage)}</dd></span>
          <span><dt>Evidence</dt><dd>{selected.evidence_count}</dd></span>
          <span><dt>Clusters</dt><dd>{visual.clusters.length}</dd></span>
          <span><dt>Key bottleneck</dt><dd>{keyBottleneck}</dd></span>
        </dl>
        <div className="scout-summary-companies">
          <small>Evidence-linked companies</small>
          {evidenceLinkedCompanies.length > 0
            ? evidenceLinkedCompanies.map((company) => (
              <details className="scout-company-chip" key={`${company.canonicalKey}:${company.citation}`}>
                <summary>{companyDisplayLabel(company)}</summary>
                <code className="scout-company-evidence-metadata">Evidence metadata: {companyEvidenceMetadata(company)}</code>
              </details>
            ))
            : <b>Unavailable</b>}
        </div>
      </section>

      <div className="scout-candidate-context">
        <div>
          <small>研究候選 / Theme Candidate · {selected.status}</small>
          <h2>{selected.name}</h2>
          <p>{selected.description}</p>
        </div>
      </div>

      <ScoutHypothesisPanel candidate={selected} />
      </section>

      <section className="why-theme-matters" aria-label="Why this theme matters">
        <header><BilingualLabel zh="為何重要" en="Why This Theme Matters" inline /><span>persisted candidate data only</span></header>
        <div>
          <article><strong>Signal clusters</strong><span>{visual.clusters.map((cluster) => cluster.label).join(", ") || "Unavailable"}</span></article>
          <article><strong>Constraint watch</strong><span>{visual.bottlenecks.map((item) => item.label).join(", ") || "Unavailable"}</span></article>
          <article><strong>Research tasks</strong><span>{visual.researchQueue.map((item) => item.label).join(", ") || "Unavailable"}</span></article>
        </div>
      </section>

      <section className="scout-workflow-stage scout-signals-stage" data-workflow-stage="signals">
        <StageHeader zh="訊號" en="Signals" count={selected.signal_count} />
        <div className="scout-signal-grid">
          {selected.signal_clusters.flatMap((cluster) => (
            cluster.evidence_ids.map((evidenceId) => {
              const evidence = selected.evidence.find((item) => item.evidence_id === evidenceId);
              return (
                <article key={`${cluster.cluster_key}:${evidenceId}`}>
                  <strong>{evidence?.domain_type ?? "Evidence"}</strong>
                  <p>{evidence?.citation ?? "Citation unavailable"}</p>
                  <code>{evidenceId}</code>
                </article>
              );
            })
          ))}
        </div>
      </section>

      <section className="scout-workflow-stage scout-clusters-stage" data-workflow-stage="clusters">
        <StageHeader zh="訊號叢集" en="Clusters" count={visual.clusters.length} />
        <div className="scout-cluster-grid">{visual.clusters.map((cluster) => (
          <article key={cluster.key}><strong>{cluster.label}</strong><span>{cluster.evidenceCount} evidence</span></article>
        ))}</div>
      </section>

      <section className="scout-workflow-stage scout-constraint-stage" data-workflow-stage="constraint-watch">
        <StageHeader zh="瓶頸觀察" en="Constraint Watch" count={`${visual.bottlenecks.length} hypotheses`} />
        <div className="scout-constraint-list">{visual.bottlenecks.map((item) => (
          <article key={item.label}>
            <span><strong>{item.label}</strong><small>Scout hypothesis, not a graph constraint</small></span>
            <b>{item.evidenceCount} evidence</b><code>{item.evidenceIds.join(", ")}</code>
          </article>
        ))}</div>
      </section>

      <section className="scout-workflow-stage scout-queue-stage" data-workflow-stage="research-queue">
        <StageHeader zh="研究佇列" en="Research Queue" count={visual.researchQueue.length} />
        <div>{visual.researchQueue.map((item, index) => (
          <article key={`${item.label}:${index}`}>
            <b>{index + 1}</b>
            <span><strong>{item.label}</strong><small>{item.state}</small></span>
            <code>{item.evidenceIds.join(", ")}</code>
          </article>
        ))}</div>
      </section>

      <section className="scout-workflow-stage scout-validation-stage" data-workflow-stage="validation">
        <StageHeader zh="驗證" en="Validation" count={`${selected.evidence_count} evidence`} />
        <div className="scout-evidence-companies">
          {visual.companies.map((company) => (
            <article key={`${company.canonicalKey}:${company.citation}`}>
              <strong>{companyDisplayLabel(company)}</strong><small>{companyEvidenceMetadata(company)}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="scout-workflow-stage scout-approval-stage" data-workflow-stage="approval">
        <StageHeader zh="審核" en="Approval" count="Manual lifecycle" />
        <div className="scout-lifecycle">
          {visual.lifecycle.map((stage) => (
            <span key={stage.status} data-active={stage.active}><i /><strong>{stage.status}</strong></span>
          ))}
        </div>
        <p>Scout output is a research candidate only. It is not verified graph evidence and creates no downstream records.</p>
      </section>

      <aside className="scout-metadata-strip" aria-label="Scout candidate metadata">
        <span><small>信心 / Confidence</small><strong>{scoutScore(selected.metrics.confidence)}</strong></span>
        <span><small>覆蓋 / Coverage</small><strong>{scoutScore(selected.metrics.coverage)}</strong></span>
        <span><small>研究成熟度 / Readiness</small><strong>{scoutScore(selected.readiness.overall)}</strong></span>
        <span><small>新穎度 / Novelty</small><strong>{noveltyUnavailable ? "方法待定" : scoutScore(selected.metrics.novelty)}</strong></span>
        <span><small>證據 / Evidence</small><strong>{selected.evidence_count}</strong></span>
        <span><small>來源 / Sources</small><strong>{selected.source_count}</strong></span>
      </aside>

      <aside className="scout-provenance-strip">
        <span><small>Snapshot</small><b>{snapshot.scout_version}</b></span>
        <span><small>Provider</small><b>{snapshot.provider_name}/{snapshot.provider_model}</b></span>
        <span><small>Evidence checksum</small><b>{snapshot.evidence_bundle_checksum?.slice(0, 12) ?? "不可用"}</b></span>
        <span><small>Proposal checksum</small><b>{snapshot.proposal_checksum?.slice(0, 12) ?? "不可用"}</b></span>
      </aside>
    </section>
  );
}
