"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, GitBranch, Layers, Loader2, ShieldCheck, Target } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import type { DrilldownTarget } from "@/lib/drilldown";
import { formatTickerCompanyLabel } from "@/lib/sanitize";
import { orderThemeExposureByRank, projectPrimaryRole, stockResearchCoverageLabel } from "@/lib/stockResearch";
import { fetchStockResearch } from "@/services/stockApi";
import type { StockResearchResponse } from "@/types/stock";
import { BilingualLabel, StatusDot, TickerLogo } from "./terminal";

const DEFAULT_STOCK_TICKER = "NVDA";

interface StockAnalysisWorkspaceProps {
  activeSelection?: DrilldownTarget | null;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

function normalizeTicker(ticker: string | null | undefined): string {
  return ticker?.trim().toUpperCase() || DEFAULT_STOCK_TICKER;
}

function emptyStockResearch(ticker: string): StockResearchResponse {
  return {
    available: false,
    ticker,
    generated_at: "",
    company_header: {
      company_name: ticker,
      ticker,
      theme_rank: null,
      theme_lifecycle: "Unavailable",
      research_coverage: 0,
      primary_theme: "Unavailable",
    },
    supply_chain_roles: [],
    theme_exposure: [],
    investment_thesis: {
      why_it_matters: [],
      current_drivers: [],
      catalysts: [],
      risks: [],
      research_gaps: [],
    },
    evidence_chain: [],
    research_completeness: {
      coverage: 0,
      evidence_strength: 0,
      validation_status: "Research Incomplete",
      open_questions: [],
      research_gaps: ["No persisted stock research projection is available."],
    },
    decision_support: {
      research_state: "Research Incomplete",
      bull_case: [],
      bear_case: [],
      monitoring_triggers: [],
      research_gaps: [],
    },
    related_companies: {
      same_theme: [],
      same_bottleneck: [],
      same_controller: [],
      same_opportunity: [],
    },
  };
}

function textFromRow(row: Record<string, unknown> | string): string {
  if (typeof row === "string") return row;
  const value = row.value ?? row.label ?? row.question ?? row.condition ?? row.state;
  return typeof value === "string" || typeof value === "number" ? String(value) : "Evidence row";
}

function evidenceLabel(ids: number[] | undefined): string {
  return ids && ids.length ? `Evidence ${ids.join(", ")}` : "Evidence unavailable";
}

function MemoPanel({ zh, en, children, emphasis = false }: { zh: string; en: string; children: React.ReactNode; emphasis?: boolean }) {
  return (
    <section className={`stock-memo-panel ${emphasis ? "is-primary" : ""}`}>
      <div className="stock-memo-panel-head">
        <BilingualLabel zh={zh} en={en} inline />
      </div>
      {children}
    </section>
  );
}

export default function StockAnalysisWorkspace({ activeSelection, onPreview, onPreviewEnd, onContext, onDrilldown }: StockAnalysisWorkspaceProps) {
  const { selectedTicker, setSelectedTicker } = useWorkspace();
  const ticker = normalizeTicker(selectedTicker);
  const [research, setResearch] = useState<StockResearchResponse>(() => emptyStockResearch(ticker));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTicker?.trim()) setSelectedTicker(DEFAULT_STOCK_TICKER);
  }, [selectedTicker, setSelectedTicker]);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const payload = await fetchStockResearch(ticker, { signal: controller.signal });
        if (!controller.signal.aborted) setResearch(payload);
      } catch (err) {
        if (!controller.signal.aborted) {
          setResearch(emptyStockResearch(ticker));
          setError(err instanceof Error ? err.message : "Stock research projection failed");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [ticker]);

  const exposures = useMemo(() => orderThemeExposureByRank(research.theme_exposure), [research.theme_exposure]);
  const primaryRole = useMemo(() => projectPrimaryRole(research.supply_chain_roles), [research.supply_chain_roles]);
  const target = {
    kind: "stock",
    symbol: research.ticker,
    label: research.company_header.company_name,
    name: research.ticker,
    value: research.research_completeness.coverage,
    meta: research.company_header.primary_theme,
  } satisfies DrilldownTarget;

  const relatedRows = [
    ...research.related_companies.same_theme,
    ...research.related_companies.same_bottleneck,
    ...research.related_companies.same_controller,
    ...research.related_companies.same_opportunity,
  ].slice(0, 8);

  return (
    <main className="stock-research-workspace stock-memo-workspace text-[var(--theme-text)]">
      <header className="stock-memo-header">
        <div className="stock-memo-company">
          <TickerLogo ticker={research.ticker} name={research.company_header.company_name} />
          <div>
            <BilingualLabel zh="公司研究" en="Company Research" inline />
            <strong>{formatTickerCompanyLabel(research.ticker, research.company_header.company_name)}</strong>
          </div>
        </div>
        <div className="stock-memo-header-grid">
          <span><small>Theme Rank</small><b>{research.company_header.theme_rank ? `#${research.company_header.theme_rank}` : "Unavailable"}</b></span>
          <span><small>Lifecycle</small><b>{research.company_header.theme_lifecycle}</b></span>
          <span><small>Coverage</small><b>{stockResearchCoverageLabel(research.company_header.research_coverage)}</b></span>
          <span><small>Primary Theme</small><b>{research.company_header.primary_theme}</b></span>
        </div>
        {loading && <div className="stock-memo-loading"><Loader2 size={14} className="animate-spin" /> Updating</div>}
      </header>

      {error && <div className="stock-error">{error}</div>}

      <section className="stock-memo-role-hero">
        <div>
          <BilingualLabel zh="供應鏈角色" en="Supply Chain Role" inline />
          <strong>{primaryRole.role_type}</strong>
          <p>{primaryRole.role_description}</p>
        </div>
        <div className="stock-role-stats">
          <span><small>Importance</small><b>{Math.round(primaryRole.role_importance)}</b></span>
          <span><small>Role Evidence</small><b>{primaryRole.evidence_count}</b></span>
          <span><small>Status</small><b>{research.research_completeness.validation_status}</b></span>
        </div>
      </section>

      <div className="stock-memo-grid">
        <div className="stock-memo-main">
          <MemoPanel zh="主題曝險" en="Theme Exposure" emphasis>
            <div className="stock-theme-exposure-list">
              {exposures.length ? exposures.map((row) => (
                <button
                  key={row.theme_id}
                  type="button"
                  onMouseEnter={() => onPreview?.({ kind: "theme", name: row.theme_id, label: row.theme_name, subject: row.theme_id })}
                  onMouseLeave={onPreviewEnd}
                  onClick={() => onContext?.({ kind: "theme", name: row.theme_id, label: row.theme_name, subject: row.theme_id })}
                  onDoubleClick={() => onDrilldown?.({ kind: "theme", name: row.theme_id, label: row.theme_name, subject: row.theme_id })}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") return;
                    event.preventDefault();
                    onDrilldown?.({ kind: "theme", name: row.theme_id, label: row.theme_name, subject: row.theme_id });
                  }}
                >
                  <span><b>{row.rank ? `#${row.rank}` : "--"}</b>{row.theme_name}</span>
                  <em>{row.lifecycle}</em>
                  <small>Importance {Math.round(row.importance)}</small>
                  <small>Coverage {stockResearchCoverageLabel(row.coverage)}</small>
                  <small>Evidence {row.evidence_count}</small>
                </button>
              )) : <p className="stock-empty-copy">No persisted theme exposure path for this ticker.</p>}
            </div>
          </MemoPanel>

          <MemoPanel zh="投資論點" en="Investment Thesis">
            <div className="stock-thesis-grid">
              <article><h4>Why It Matters</h4>{renderLines(research.investment_thesis.why_it_matters)}</article>
              <article><h4>Current Drivers</h4>{renderLines(research.investment_thesis.current_drivers)}</article>
              <article><h4>Catalysts</h4>{renderLines(research.investment_thesis.catalysts)}</article>
              <article><h4>Risks</h4>{renderLines(research.investment_thesis.risks)}</article>
              <article><h4>Research Gaps</h4>{renderLines(research.investment_thesis.research_gaps)}</article>
            </div>
          </MemoPanel>

          <MemoPanel zh="證據鏈" en="Evidence Chain" emphasis>
            <div className="stock-evidence-chain">
              {research.evidence_chain.length ? research.evidence_chain.map((step, index) => (
                <div key={`${step.step_type}-${step.label}-${index}`}>
                  <span>{step.step_type}</span>
                  <strong>{step.label}</strong>
                  <small>{evidenceLabel(step.evidence_ids)}</small>
                </div>
              )) : <p className="stock-empty-copy">No persisted evidence chain is available.</p>}
            </div>
          </MemoPanel>
        </div>

        <aside className="stock-memo-side">
          <MemoPanel zh="研究完整度" en="Research Completeness">
            <div className="stock-completeness">
              <span><ShieldCheck size={15} /> Coverage <b>{stockResearchCoverageLabel(research.research_completeness.coverage)}</b></span>
              <span><Layers size={15} /> Evidence Strength <b>{stockResearchCoverageLabel(research.research_completeness.evidence_strength)}</b></span>
              <span><AlertCircle size={15} /> Validation <b>{research.research_completeness.validation_status}</b></span>
              {renderLines([...research.research_completeness.open_questions, ...research.research_completeness.research_gaps])}
            </div>
          </MemoPanel>

          <MemoPanel zh="決策支持" en="Decision Support">
            <div className="stock-decision-support">
              <StatusDot state={research.decision_support.research_state === "Evidence Available" ? "live" : "neutral"} label={research.decision_support.research_state} />
              <h4>Bull Case</h4>
              {renderRows(research.decision_support.bull_case)}
              <h4>Bear Case</h4>
              {renderRows(research.decision_support.bear_case)}
              <h4>Monitoring Triggers</h4>
              {renderRows(research.decision_support.monitoring_triggers)}
              <h4>Research Gaps</h4>
              {renderRows(research.decision_support.research_gaps)}
            </div>
          </MemoPanel>

          <MemoPanel zh="相關公司" en="Related Companies">
            <div className="stock-related-memo-list">
              {relatedRows.length ? relatedRows.map((row) => (
                <button
                  key={`${row.relationship}-${row.ticker}`}
                  type="button"
                  onMouseEnter={() => onPreview?.({ kind: "stock", symbol: row.ticker, label: row.company_name })}
                  onMouseLeave={onPreviewEnd}
                  onClick={() => onContext?.({ kind: "stock", symbol: row.ticker, label: row.company_name })}
                  onDoubleClick={() => onDrilldown?.({ kind: "stock", symbol: row.ticker, label: row.company_name })}
                  onKeyDown={(event) => {
                    if (event.key !== "Enter") return;
                    event.preventDefault();
                    onDrilldown?.({ kind: "stock", symbol: row.ticker, label: row.company_name });
                  }}
                >
                  <strong>{row.ticker}</strong>
                  <span>{row.company_name}</span>
                  <small>{row.relationship}</small>
                  <em>{row.evidence_count} evidence</em>
                </button>
              )) : <p className="stock-empty-copy">No related companies from persisted paths.</p>}
            </div>
          </MemoPanel>

          <button className="stock-memo-context-button" type="button" onClick={() => onContext?.(target)}>
            <Target size={15} />
            <span>Open Context</span>
            <small>{activeSelection?.label ?? research.ticker}</small>
          </button>
          <button className="stock-memo-context-button" type="button" onClick={() => onDrilldown?.(target)}>
            <GitBranch size={15} />
            <span>Trace Evidence</span>
            <small>{research.evidence_chain.length} steps</small>
          </button>
        </aside>
      </div>
    </main>
  );
}

function renderLines(rows: string[]) {
  if (!rows.length) return <p className="stock-empty-copy">Unavailable from persisted evidence.</p>;
  return <ul>{rows.map((row) => <li key={row}>{row}</li>)}</ul>;
}

function renderRows(rows: Array<Record<string, unknown> | string>) {
  if (!rows.length) return <p className="stock-empty-copy">Unavailable from persisted evidence.</p>;
  return <ul>{rows.slice(0, 5).map((row, index) => <li key={`${textFromRow(row)}-${index}`}>{textFromRow(row)}</li>)}</ul>;
}
