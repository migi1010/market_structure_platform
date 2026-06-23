"use client";

import { useEffect, useMemo, useState } from "react";
import { ClipboardList, RefreshCw } from "lucide-react";
import {
  PIPELINE_BOARD_COLUMNS,
  PIPELINE_STAGE_LABELS,
  buildPipelineBoard,
  evidenceCount,
  nextPipelineStatus,
  primaryBottleneck,
} from "@/lib/researchPipeline";
import {
  fetchThemeRegistry,
  fetchResearchPipeline,
  transitionResearchPipelineCase,
} from "@/services/stockApi";
import type {
  ResearchPipelineCaseDetail,
  ResearchPipelineResponse,
  ResearchPipelineStatus,
  ThemeRegistryEntry,
} from "@/types/stock";
import { findThemeRegistryEntry } from "@/lib/themeRegistry";

const EMPTY_RESPONSE: ResearchPipelineResponse = {
  available: true,
  cases: [],
  details: [],
};

const SECTION_LABELS: Array<[keyof ResearchPipelineCaseDetail["progress"]["sections"], string, string]> = [
  ["theme_narrative", "主題敘事", "Theme Narrative"],
  ["supply_chain_validation", "供應鏈驗證", "Supply Chain Validation"],
  ["controller_review", "控制層檢核", "Controller Review"],
  ["opportunity_review", "機會檢核", "Opportunity Review"],
  ["decision_packet_link", "決策包連結", "Decision Packet Link"],
];

function StageLabel({ status }: { status: ResearchPipelineStatus }) {
  const label = PIPELINE_STAGE_LABELS[status];
  return <span>{label.zh}<small>{label.en}</small></span>;
}

function ProgressStrip({ value }: { value: number }) {
  return <span className="pipeline-progress-strip"><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></span>;
}

function CaseCard({ detail, selected, registryThemes, onSelect, onThemeNavigate }: {
  detail: ResearchPipelineCaseDetail;
  selected: boolean;
  registryThemes: ThemeRegistryEntry[];
  onSelect: () => void;
  onThemeNavigate?: (themeId: string) => void;
}) {
  const theme = findThemeRegistryEntry(registryThemes, detail.case.theme_id);
  return (
    <button type="button" className="pipeline-case-card" data-selected={selected} onClick={onSelect}>
      <strong>{detail.case.title}</strong>
      <span>{theme?.theme_name ?? detail.case.theme_id}</span>
      {theme && <em onClick={(event) => { event.stopPropagation(); onThemeNavigate?.(theme.theme_id); }}>Open Theme</em>}
      <small>{primaryBottleneck(detail)}</small>
      <div>
        <b>{detail.progress.percent}%</b>
        <em>{evidenceCount(detail)} evidence</em>
      </div>
      <ProgressStrip value={detail.progress.percent} />
    </button>
  );
}

function DetailPanel({ detail, onAdvanced, onDecisionNavigate }: {
  detail: ResearchPipelineCaseDetail | undefined;
  onAdvanced: (detail: ResearchPipelineCaseDetail, next: ResearchPipelineStatus) => void;
  onDecisionNavigate?: () => void;
}) {
  if (!detail) {
    return (
      <section className="pipeline-detail-panel">
        <header><span>研究個案</span><small>Case Detail</small></header>
        <p className="pipeline-empty">Select a research case to inspect lifecycle, links, progress, and evidence audit.</p>
      </section>
    );
  }
  const next = nextPipelineStatus(detail.case.status);
  return (
    <section className="pipeline-detail-panel">
      <header>
        <span>{detail.case.title}</span>
        <small>{detail.case.case_id}</small>
      </header>
      <div className="pipeline-detail-hero">
        <div><small>目前階段 Current Stage</small><strong>{PIPELINE_STAGE_LABELS[detail.case.status].zh}</strong><span>{PIPELINE_STAGE_LABELS[detail.case.status].en}</span></div>
        <div><small>研究進度 Progress</small><strong>{detail.progress.percent}%</strong><ProgressStrip value={detail.progress.percent} /></div>
        <div><small>主要瓶頸 Key Bottleneck</small><strong>{primaryBottleneck(detail)}</strong><span>persisted links only</span></div>
      </div>
      <div className="pipeline-review-grid">
        {SECTION_LABELS.map(([key, zh, en]) => (
          <article key={key} data-complete={detail.progress.sections[key]}>
            <small>{zh}</small>
            <strong>{detail.progress.sections[key] ? "complete" : "pending"}</strong>
            <span>{en}</span>
          </article>
        ))}
      </div>
      <div className="pipeline-action-row">
        <button type="button" onClick={onDecisionNavigate}>
          Open Decision Intelligence
        </button>
        {next ? (
          <button type="button" onClick={() => onAdvanced(detail, next)}>
            Manual transition to {next}
          </button>
        ) : (
          <span>Manual transition unavailable for this stage.</span>
        )}
      </div>
      <div className="pipeline-detail-grid">
        <section>
          <h3>研究時間線 Research Timeline</h3>
          {detail.timeline.map((event) => (
            <article key={event.event_id}>
              <b>{event.new_status}</b>
              <span>{event.reason || "manual lifecycle event"}</span>
              <small>{event.created_at}</small>
            </article>
          ))}
        </section>
        <section>
          <h3>證據與工件 Evidence Audit</h3>
          {detail.links.map((link) => (
            <article key={link.link_id}>
              <b>{link.linked_type}</b>
              <span>{link.linked_id}</span>
              <small>{link.created_at}</small>
            </article>
          ))}
        </section>
      </div>
      <footer>
        <span>Scout Origin: {detail.case.source_type} / {detail.case.source_id}</span>
        <span>Lineage: {detail.case.lineage_checksum.slice(0, 16)}</span>
      </footer>
    </section>
  );
}

export default function ResearchPipelinePage({
  onThemeNavigate,
  onDecisionNavigate,
}: {
  onThemeNavigate?: (themeId: string) => void;
  onDecisionNavigate?: () => void;
}) {
  const [response, setResponse] = useState<ResearchPipelineResponse>(EMPTY_RESPONSE);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [registryThemes, setRegistryThemes] = useState<ThemeRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = () => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      fetchResearchPipeline(controller.signal),
      fetchThemeRegistry(controller.signal).catch(() => null),
    ])
      .then(([payload, registry]) => {
        setResponse(payload);
        setRegistryThemes(registry?.themes ?? []);
        setSelectedCaseId((current) => current || payload.details[0]?.case.case_id || "");
        setError("");
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Research Pipeline unavailable");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  };

  useEffect(() => refresh(), []);

  const board = useMemo(() => buildPipelineBoard(response.details), [response.details]);
  const selected = response.details.find((detail) => detail.case.case_id === selectedCaseId) ?? response.details[0];

  const advance = (detail: ResearchPipelineCaseDetail, next: ResearchPipelineStatus) => {
    transitionResearchPipelineCase(detail.case.case_id, {
      new_status: next,
      reason: `manual transition from ${detail.case.status}`,
    }).then((updated) => {
      setResponse((current) => ({
        ...current,
        details: current.details.map((row) => row.case.case_id === updated.case.case_id ? updated : row),
        cases: current.cases.map((row) => row.case_id === updated.case.case_id ? { ...updated.case, progress: updated.progress, linked_artifact_count: updated.links.length, event_count: updated.timeline.length } : row),
      }));
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Manual transition failed"));
  };

  return (
    <main className="research-pipeline-workspace">
      <header className="pipeline-page-header">
        <div><ClipboardList size={18} /><span><h1>研究管線 Research Pipeline</h1><small>Manual lifecycle management only</small></span></div>
        <button type="button" onClick={refresh}><RefreshCw size={13} /> Refresh</button>
      </header>
      {loading && <div className="pipeline-empty"><RefreshCw size={14} className="animate-spin" /> Loading Research Pipeline...</div>}
      {error && <div className="pipeline-error">{error}</div>}
      <section className="pipeline-board">
        {PIPELINE_BOARD_COLUMNS.map((status) => (
          <div key={status} className="pipeline-column">
            <header><StageLabel status={status} /><b>{board[status].length}</b></header>
            {board[status].length > 0 ? board[status].map((detail) => (
              <CaseCard
                key={detail.case.case_id}
                detail={detail}
                selected={selected?.case.case_id === detail.case.case_id}
                registryThemes={registryThemes}
                onSelect={() => setSelectedCaseId(detail.case.case_id)}
                onThemeNavigate={onThemeNavigate}
              />
            )) : <p>No cases in this stage.</p>}
          </div>
        ))}
      </section>
      <DetailPanel detail={selected} onAdvanced={advance} onDecisionNavigate={onDecisionNavigate} />
    </main>
  );
}
