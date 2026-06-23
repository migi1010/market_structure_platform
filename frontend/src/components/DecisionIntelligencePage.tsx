"use client";

import { useEffect, useMemo, useState } from "react";
import { FileText, RefreshCw } from "lucide-react";
import {
  buildDecisionIntelligenceMemoHierarchy,
  decisionIntelligenceEvidenceState,
  rowLabel,
  rowMeta,
  summarizeDecisionIntelligencePacket,
} from "@/lib/decisionIntelligence";
import { buildRankingLookup, lifecycleBadgeModel, normalizeThemeRankingKey } from "@/lib/themeRanking";
import { fetchDecisionIntelligence, fetchThemeRanking } from "@/services/stockApi";
import type { DecisionIntelligencePacket, DecisionIntelligenceResponse, DecisionIntelligenceSectionKey, ThemeRank } from "@/types/stock";

const EMPTY_RESPONSE: DecisionIntelligenceResponse = {
  available: true,
  packets: [],
  details: [],
};

const SECTION_LABELS: Record<DecisionIntelligenceSectionKey, { zh: string; en: string }> = {
  summary: { zh: "研究摘要", en: "Summary" },
  bull_case: { zh: "正向論據", en: "Bull Case" },
  bear_case: { zh: "反向論據", en: "Bear Case" },
  evidence_strength: { zh: "證據強度", en: "Evidence Strength" },
  research_gaps: { zh: "研究缺口", en: "Research Gaps" },
  monitoring_triggers: { zh: "監測條件", en: "Monitoring Conditions" },
  scenario_matrix: { zh: "情境矩陣", en: "Scenario Matrix" },
  open_questions: { zh: "未決問題", en: "Open Questions" },
  lineage: { zh: "來源譜系", en: "Lineage" },
};

function SectionRows({ packet, sectionKey }: { packet: DecisionIntelligencePacket; sectionKey: DecisionIntelligenceSectionKey }) {
  const rows = packet.sections[sectionKey] ?? [];
  return (
    <section className="decision-memo-section" data-section-key={sectionKey}>
      <header>
        <h2>{SECTION_LABELS[sectionKey].zh}</h2>
        <span>{SECTION_LABELS[sectionKey].en}</span>
      </header>
      <div>
        {rows.length > 0 ? rows.map((row, index) => (
          <article key={`${sectionKey}-${index}`}>
            <strong>{rowLabel(row)}</strong>
            {rowMeta(row) && <span>{rowMeta(row)}</span>}
            {Array.isArray(row.evidence_ids) && row.evidence_ids.length > 0 && (
              <code>Evidence: {row.evidence_ids.join(", ")}</code>
            )}
          </article>
        )) : (
          <p>No structured rows available.</p>
        )}
      </div>
    </section>
  );
}

function PacketSelector({ packets, selectedId, onSelect }: {
  packets: DecisionIntelligencePacket[];
  selectedId: string;
  onSelect: (packetId: string) => void;
}) {
  return (
    <aside className="terminal-panel p-3">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-muted)]">Decision Intelligence Packets</p>
      <div className="space-y-2">
        {packets.map((packet) => {
          const summary = summarizeDecisionIntelligencePacket(packet);
          return (
            <button
              key={packet.packet_id}
              type="button"
              data-selected={packet.packet_id === selectedId}
              onClick={() => onSelect(packet.packet_id)}
              className="w-full border border-[var(--theme-border)] bg-[var(--theme-bg-secondary)] px-3 py-2 text-left text-sm transition data-[selected=true]:border-[var(--theme-border-strong)] data-[selected=true]:bg-[var(--theme-surface-elevated)]"
            >
              <strong className="block text-[var(--theme-text)]">{summary.title}</strong>
              <span className="mt-1 block text-xs text-[var(--theme-muted)]">{summary.themeId} / {summary.status}</span>
              <span className="mt-1 block font-mono text-[11px] text-[var(--theme-text-secondary)]">{summary.lineageLabel}</span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

export default function DecisionIntelligencePage() {
  const [response, setResponse] = useState<DecisionIntelligenceResponse>(EMPTY_RESPONSE);
  const [selectedPacketId, setSelectedPacketId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [themeRanking, setThemeRanking] = useState<ThemeRank[]>([]);

  const refresh = () => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      fetchDecisionIntelligence(controller.signal),
      fetchThemeRanking(controller.signal).catch(() => null),
    ])
      .then(([payload, ranking]) => {
        setResponse(payload);
        setThemeRanking(ranking?.themes ?? []);
        setSelectedPacketId((current) => current || payload.details[0]?.packet_id || "");
        setError("");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Decision Intelligence unavailable");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  };

  useEffect(() => refresh(), []);

  const packet = useMemo(
    () => response.details.find((row) => row.packet_id === selectedPacketId) ?? response.details[0],
    [response.details, selectedPacketId],
  );
  const summary = packet ? summarizeDecisionIntelligencePacket(packet) : null;
  const memoHierarchy = buildDecisionIntelligenceMemoHierarchy();
  const evidenceState = summary ? decisionIntelligenceEvidenceState(summary.evidenceCount) : "Research Incomplete";
  const rankingLookup = useMemo(() => buildRankingLookup(themeRanking), [themeRanking]);
  const selectedThemeRank = summary ? rankingLookup.get(summary.themeId) ?? rankingLookup.get(normalizeThemeRankingKey(summary.themeId)) ?? null : null;
  const selectedLifecycleBadge = selectedThemeRank ? lifecycleBadgeModel(selectedThemeRank.lifecycle) : null;

  return (
    <main id="decision-intelligence" tabIndex={-1} className="miji-page p-5 text-[var(--theme-text)] outline-none ring-0">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--theme-warning)]">Institutional Research Memo</p>
          <h1 className="mt-1 flex items-center gap-2 text-[28px] font-semibold leading-tight"><FileText size={22} /> 決策情報 Decision Intelligence</h1>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Structured evidence, gaps, monitoring conditions, scenarios, and lineage. No investment decision output.</p>
        </div>
        <button type="button" onClick={refresh} className="inline-flex items-center gap-2 border border-[var(--theme-border)] px-3 py-2 text-sm">
          <RefreshCw size={13} /> Refresh
        </button>
      </header>

      {loading && <div className="pipeline-empty"><RefreshCw size={14} className="animate-spin" /> Loading Decision Intelligence...</div>}
      {error && <div className="pipeline-error">{error}</div>}
      {!loading && !packet && (
        <section className="terminal-panel p-8 text-center">
          <h2 className="text-lg font-semibold">No Decision Intelligence packets available</h2>
          <p className="mt-2 text-sm text-[var(--theme-muted)]">Research pipeline cases are required before this read model can assemble a memo.</p>
        </section>
      )}

      {packet && summary && (
        <div className="decision-memo-layout">
          <PacketSelector packets={response.details} selectedId={packet.packet_id} onSelect={setSelectedPacketId} />
          <div className="decision-memo-body">
            <section className="decision-memo-lineage-strip">
              <div>
                <div><small className="text-[var(--theme-muted)]">Theme</small><strong className="block">{summary.themeId}</strong></div>
                <div><small className="text-[var(--theme-muted)]">Theme Rank</small><strong className="block">{selectedThemeRank ? `#${selectedThemeRank.rank}` : "Unavailable"}</strong></div>
                <div><small className="text-[var(--theme-muted)]">Theme Lifecycle</small><strong className={selectedLifecycleBadge?.className}>{selectedThemeRank?.lifecycle ?? "Unavailable"}</strong></div>
                <div><small className="text-[var(--theme-muted)]">Evidence</small><strong className="block">{summary.evidenceCount}</strong></div>
                <div><small className="text-[var(--theme-muted)]">Research Gaps</small><strong className="block">{summary.gapCount}</strong></div>
                <div><small className="text-[var(--theme-muted)]">Monitoring</small><strong className="block">{summary.triggerCount}</strong></div>
              </div>
              {evidenceState === "Research Incomplete" && <strong className="decision-research-incomplete">Research Incomplete</strong>}
              <code className="mt-3 block text-[11px] text-[var(--theme-text-secondary)]">Checksum: {packet.checksum}</code>
            </section>
            <div className="decision-memo-primary">
              {memoHierarchy.primary.map((sectionKey) => (
                <SectionRows key={sectionKey} packet={packet} sectionKey={sectionKey} />
              ))}
            </div>
            <div className="decision-memo-secondary">
              {memoHierarchy.secondary.map((sectionKey) => (
                <SectionRows key={sectionKey} packet={packet} sectionKey={sectionKey} />
              ))}
            </div>
            <div className="decision-memo-tertiary">
              {memoHierarchy.tertiary.map((sectionKey) => (
                <SectionRows key={sectionKey} packet={packet} sectionKey={sectionKey} />
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
