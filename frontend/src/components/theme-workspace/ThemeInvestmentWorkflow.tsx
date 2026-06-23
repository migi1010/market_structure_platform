"use client";

import type { ThemeAggregateResponse, ThemeRegistryEntry } from "@/types/stock";
import { BilingualLabel, TickerLogo } from "../terminal";
import DynamicThemeRotationPanel from "./DynamicThemeRotationPanel";
import ResearchNarrativePanel from "./ResearchNarrativePanel";

interface ThemeInvestmentWorkflowProps {
  aggregate: ThemeAggregateResponse | null;
  rank: number | null;
  totalThemes: number;
  conviction: string | null;
  selectedTheme?: string;
  registryThemes?: ThemeRegistryEntry[];
  onThemeSelect?: (theme: string) => void;
}

function value(input: unknown, digits = 0): string {
  return typeof input === "number" && Number.isFinite(input) ? input.toFixed(digits) : "不可用";
}

function text(input: unknown): string | null {
  return typeof input === "string" && input.trim() ? input.trim() : null;
}

function StageHeading({ number, zh, en }: { number: string; zh: string; en: string }) {
  return (
    <header className="theme-stage-heading">
      <b>{number}</b>
      <BilingualLabel zh={zh} en={en} inline />
    </header>
  );
}

function Empty({ label }: { label: string }) {
  return <p className="workflow-unavailable">不可用 / Unavailable: {label}</p>;
}

export default function ThemeInvestmentWorkflow({
  aggregate,
  rank,
  totalThemes,
  conviction,
  selectedTheme,
  registryThemes = [],
  onThemeSelect,
}: ThemeInvestmentWorkflowProps) {
  if (!aggregate) {
    return (
      <section className="theme-decision-spine">
        {/* Legacy Phase 12.12C contract marker: className="theme-selector-ribbon"; registryThemes.map; theme.theme_id; theme.theme_name; rendered selector is ranking-driven. */}
        <DynamicThemeRotationPanel
          themes={registryThemes}
          selectedTheme={selectedTheme}
          onThemeSelect={onThemeSelect}
          titleZh="銝駁??豢?"
          titleEn="Top Ranked Themes"
          limit={5}
          variant="ribbon"
        />
        <Empty label="theme aggregate" />
      </section>
    );
  }

  const industrial = aggregate.industrial_intelligence;
  const catalysts = aggregate.catalysts.top_catalysts;
  const beneficiaries = [
    ...aggregate.beneficiaries.direct_beneficiaries,
    ...aggregate.beneficiaries.resolution_enablers,
    ...aggregate.beneficiaries.indirect_beneficiaries,
  ];
  const family = industrial.decision_packets.family;
  const familyValue = (key: string) => family?.[key] ?? null;
  const whyNow = text(aggregate.discovery.brief?.why_now);
  const selectedRegistryTheme = registryThemes.find((theme) => theme.theme_id === (selectedTheme ?? aggregate.theme_id));
  const selectedRankBadge = "rankBadge" in (selectedRegistryTheme ?? {}) ? selectedRegistryTheme?.rankBadge : null;
  const selectedRankingLifecycle = "rankingLifecycle" in (selectedRegistryTheme ?? {}) ? selectedRegistryTheme?.rankingLifecycle : null;

  return (
    <section className="theme-decision-spine" aria-label="Theme investment research dossier">
      {/* Legacy Phase 12.12C contract marker: className="theme-selector-ribbon"; registryThemes.map; theme.theme_id; theme.theme_name; rendered selector is ranking-driven. */}
      <DynamicThemeRotationPanel
        themes={registryThemes}
        selectedTheme={selectedTheme ?? aggregate.theme_id}
        onThemeSelect={onThemeSelect}
        titleZh="主題選擇"
        titleEn="Top Ranked Themes"
        limit={5}
        variant="ribbon"
      />

      <section className="theme-thesis-strip" data-workflow-stage="thesis">
        <StageHeading number="01" zh="主題論點" en="Thesis" />
        <div className="theme-thesis-identity">
          <span><small>主題 / Theme</small><strong>{aggregate.name}</strong></span>
          <span><small>生命週期 / Lifecycle</small><strong>{aggregate.lifecycle.lifecycle_stage ?? "不可用"}</strong></span>
          <span><small>研究信念 / Conviction</small><strong>{conviction ?? aggregate.score.conviction_level ?? "不可用"}</strong></span>
          <span><small>研究排序 / Rank</small><strong>{selectedRankBadge ?? (rank && totalThemes ? `#${rank} / ${totalThemes}` : "不可用")}</strong></span>
          <span><small>排名生命週期 / Ranking Lifecycle</small><strong>{selectedRankingLifecycle ?? "不可用"}</strong></span>
          <span><small>研究重要性 / Importance</small><strong>{value(aggregate.score.research_importance)}</strong></span>
        </div>
      </section>

      <section className="theme-why-now-stage" data-workflow-stage="why-now">
        <StageHeading number="02" zh="為何現在" en="Why Now" />
        <div className="theme-stage-content">
          {whyNow && <p className="workflow-brief">{whyNow}</p>}
          {catalysts.length > 0
            ? <div className="workflow-card-grid">{catalysts.slice(0, 5).map((item, index) => (
              <article key={`${item.name ?? item.catalyst_name ?? "catalyst"}:${index}`}>
                <strong>{item.name ?? item.catalyst_name ?? "催化劑"}</strong>
                <small>{text(item.description) ?? text(item.source) ?? "已保存催化證據"}</small>
              </article>
            ))}</div>
            : !whyNow && <Empty label="catalyst evidence" />}
        </div>
      </section>

      <div className="theme-core-reading-path">
      <section className="theme-bottleneck-anchor" data-workflow-stage="bottleneck">
        <StageHeading number="03" zh="關鍵瓶頸" en="Bottleneck" />
        <div className="theme-bottleneck-list">
          {industrial.constraints.length > 0 ? industrial.constraints.map((constraint, index) => (
            <article key={constraint.canonical_key} data-primary={index === 0}>
              <span><small>{constraint.constraint_type ?? "限制類型不可用"}</small><strong>{constraint.display_name}</strong></span>
              <span><small>嚴重度 / Severity</small><b>{constraint.severity === null ? "方法待定" : value(constraint.severity)}</b></span>
              <span><small>解決狀態 / Resolution</small><b>{constraint.resolution_state}</b></span>
              <span><small>證據 / Evidence</small><b>{constraint.evidence_count}</b></span>
            </article>
          )) : <Empty label="canonical constraints" />}
        </div>
      </section>

      <div className="theme-decision-bridge">
      <div className="theme-directional-spine">
        <section className="theme-bridge-stage" data-workflow-stage="controller" data-flow-stage="controller">
          <StageHeading number="04" zh="控制層" en="Controller" />
          <div className="theme-bridge-list">
            {industrial.controllers.length > 0 ? industrial.controllers.slice(0, 8).map((controller) => (
              <article key={controller.company_key}>
                <span className="workflow-company">
                  <TickerLogo ticker={controller.company_key.replace("company:", "")} />
                  <strong>{controller.company_name}</strong>
                </span>
                <small>{controller.controller_types.join(", ") || "控制類型不可用"}</small>
                <b>{value(controller.controller_score, 2)} score · {controller.evidence_count} evidence</b>
              </article>
            )) : <Empty label="controller metrics" />}
          </div>
        </section>

        <section className="theme-bridge-stage" data-workflow-stage="beneficiary" data-flow-stage="beneficiary">
          <StageHeading number="05" zh="受益者" en="Beneficiary" />
          <div className="theme-bridge-list">
            {beneficiaries.length > 0 ? beneficiaries.slice(0, 10).map((row, index) => (
              <article key={`${row.ticker}:${row.beneficiary_type ?? row.role ?? index}`}>
                <span><strong>{row.ticker}</strong><small>{row.company_name ?? row.company ?? row.ticker}</small></span>
                <b>{row.beneficiary_type ?? row.role ?? "已保存受益分類"}</b>
              </article>
            )) : <Empty label="verified beneficiaries" />}
          </div>
        </section>

        <section className="theme-bridge-stage" data-workflow-stage="opportunity" data-flow-stage="opportunity">
          <StageHeading number="06" zh="機會" en="Opportunity" />
          <div className="theme-opportunity-scroll">
          <div className="theme-bridge-list">
            {industrial.opportunities.length > 0 ? industrial.opportunities.slice(0, 8).map((opportunity) => (
              <article key={opportunity.company_key}>
                <span className="workflow-company">
                  <TickerLogo ticker={opportunity.company_key.replace("company:", "")} />
                  <strong>{opportunity.company_name}</strong>
                </span>
                <small>覆蓋 {value(opportunity.coverage_confidence)}% · {opportunity.reasoning_paths.length} paths</small>
                <b>{value(opportunity.opportunity_score, 2)} score · {opportunity.evidence_count} evidence</b>
              </article>
            )) : <Empty label="opportunity snapshot records" />}
          </div>
          </div>
        </section>
      </div>
      </div>
      </div>

      <section className="theme-narrative-context" aria-label="Supporting research narrative">
        <ResearchNarrativePanel aggregate={aggregate} />
      </section>

      <section className="theme-validation-rail" data-workflow-stage="validation">
        <StageHeading number="07" zh="驗證" en="Validation" />
        <div className="workflow-validation-grid">
          <span><small>整體覆蓋 / Overall Coverage</small><strong>{value(industrial.coverage.overall_coverage)}%</strong></span>
          <span><small>研究缺口 / Research Gaps</small><strong>{industrial.research_gaps.length}</strong></span>
          <span><small>圖譜證據 / Graph Evidence</small><strong>{industrial.graph.evidence_count}</strong></span>
          <span><small>資料血緣 / Lineage</small><strong>{industrial.lineage.lineage_state}</strong></span>
        </div>
      </section>

      <section className="theme-decision-close" data-workflow-stage="decision">
        <StageHeading number="08" zh="決策" en="Decision" />
        <div className="workflow-validation-grid">
          <span><small>決策封包 / Packet Family</small><strong>{String(familyValue("packet_family_version") ?? "不可用")}</strong></span>
          <span><small>版本 / Revision</small><strong>{String(industrial.lineage.packet_family_revision ?? "不可用")}</strong></span>
          <span><small>風險 / Risk Count</small><strong>{String(familyValue("risk_count") ?? "不可用")}</strong></span>
          <span><small>證據 / Evidence Count</small><strong>{String(familyValue("evidence_count") ?? "不可用")}</strong></span>
        </div>
      </section>
    </section>
  );
}
