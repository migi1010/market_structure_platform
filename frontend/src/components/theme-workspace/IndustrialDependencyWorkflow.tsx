"use client";

import { deriveIndustrialSupplyChain } from "@/lib/supplyChainIntelligence";
import { auditSupplyChainRoles } from "@/lib/supplyChainRoleAudit";
import { useWorkspace } from "@/context/WorkspaceContext";
import type { DrilldownTarget } from "@/lib/drilldown";
import type { ThemeAggregateResponse, ThemeRegistryEntry } from "@/types/stock";
import { BilingualLabel } from "../terminal";
import DependencyStoryPanel from "./DependencyStoryPanel";
import DynamicThemeRotationPanel from "./DynamicThemeRotationPanel";
import IndustrialDependencyGraph from "./IndustrialDependencyGraph";

function metric(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(0) : "Unavailable";
}

interface IndustrialDependencyWorkflowProps {
  aggregate: ThemeAggregateResponse;
  selectedTheme?: string;
  registryThemes?: ThemeRegistryEntry[];
  onThemeSelect?: (theme: string) => void;
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

export default function IndustrialDependencyWorkflow({
  aggregate,
  selectedTheme,
  registryThemes = [],
  onThemeSelect,
  onPreview,
  onPreviewEnd,
  onContext,
  onDrilldown,
}: IndustrialDependencyWorkflowProps) {
  const { selectedSupplyChainNode, setSelectedSupplyChainNode } = useWorkspace();
  const industrial = aggregate.industrial_intelligence;
  const view = deriveIndustrialSupplyChain(industrial);
  const selectedNodeBelongsToGraph = Boolean(
    selectedSupplyChainNode
    && industrial.graph.nodes.some((node) => node.canonical_key === selectedSupplyChainNode),
  );
  const primaryBottleneck = view.primaryBottleneck;
  const primaryConstraintKey = primaryBottleneck?.canonical_key ?? null;
  const bottleneckEvidenceIds = Array.from(new Set([
    ...industrial.graph.edges
      .filter((edge) => edge.source_key === primaryConstraintKey || edge.target_key === primaryConstraintKey)
      .flatMap((edge) => edge.evidence_ids),
    ...industrial.graph.dependency_paths
      .filter((path) => path.nodes.some((node) => node.canonical_key === primaryConstraintKey))
      .flatMap((path) => path.evidence_ids ?? []),
  ])).sort((left, right) => left - right);
  const linkedControllers = primaryConstraintKey
    ? industrial.controllers.filter((controller) => controller.reasoning_paths.some((path) => (
      path.nodes.some((node) => node.canonical_key === primaryConstraintKey)
      || (path.evidence_ids ?? []).some((id) => bottleneckEvidenceIds.includes(id))
    )))
    : [];
  const linkedOpportunities = primaryConstraintKey
    ? industrial.opportunities.filter((opportunity) => opportunity.reasoning_paths.some((path) => (
      path.nodes.some((node) => node.canonical_key === primaryConstraintKey)
      || (path.evidence_ids ?? []).some((id) => bottleneckEvidenceIds.includes(id))
    )))
    : [];
  const mainController = linkedControllers[0] ?? industrial.controllers[0] ?? null;
  const beneficiaryRows = [
    ...aggregate.beneficiaries.direct_beneficiaries,
    ...aggregate.beneficiaries.resolution_enablers,
    ...aggregate.beneficiaries.indirect_beneficiaries,
  ];
  const mainBeneficiary = beneficiaryRows[0] ?? null;
  const secondaryPaths = industrial.graph.dependency_paths.slice(1);
  const roleAudit = auditSupplyChainRoles({
    controller: { key: mainController?.company_key, label: mainController?.company_name },
    beneficiary: {
      key: mainBeneficiary?.ticker ? `company:${mainBeneficiary.ticker}` : null,
      label: mainBeneficiary?.company_name ?? mainBeneficiary?.company ?? mainBeneficiary?.ticker,
    },
  });

  return (
    <section className="industrial-bottleneck-workspace" aria-label="Industrial bottleneck workspace">
      <header className="industrial-workflow-summary">
        <span><BilingualLabel zh="供應鏈地圖" en="Supply Chain Map" inline /><strong>{view.theme}</strong></span>
        <span className="industrial-primary-bottleneck-summary">
          <small>主要瓶頸 / Primary Bottleneck</small>
          <strong>{primaryBottleneck?.display_name ?? "Unavailable"}</strong>
        </span>
        <b>{metric(view.overallCoverage)}% coverage</b>
        <b>{industrial.constraints.length} constraints</b>
        <b>{industrial.controllers.length} controllers</b>
        <b>{beneficiaryRows.length} beneficiaries</b>
      </header>

      {/* Legacy Phase 12.12C contract marker: className="supply-theme-selector"; registryThemes.map; theme.theme_id; theme.theme_name; rendered selector is ranking-driven. */}
      <DynamicThemeRotationPanel
        themes={registryThemes}
        selectedTheme={selectedTheme ?? aggregate.theme_id}
        onThemeSelect={onThemeSelect}
        titleZh="產業主題"
        titleEn="Top Ranked Themes"
        limit={5}
        variant="compact"
      />

      <section className="industrial-bottleneck-hero" aria-label="Primary bottleneck control path">
        <article className="industrial-hero-stage" data-hero-stage="bottleneck">
          <small>Primary Bottleneck</small>
          <strong>{primaryBottleneck?.display_name ?? "Unavailable"}</strong>
          <span>{primaryBottleneck ? `${primaryBottleneck.resolution_state} / severity ${primaryBottleneck.severity === null ? "unavailable" : metric(primaryBottleneck.severity)}` : "No verified bottleneck"}</span>
        </article>
        <i aria-hidden="true">→</i>
        <article className="industrial-hero-stage" data-hero-stage="controller">
          <small>Controller</small>
          <strong>{mainController?.company_name ?? "Unavailable"}</strong>
          <span>{mainController ? `${metric(mainController.controller_score)} score / ${mainController.evidence_count} evidence` : "No linked controller"}</span>
        </article>
        <i aria-hidden="true">→</i>
        <article className="industrial-hero-stage" data-hero-stage="beneficiary">
          <small>Beneficiary</small>
          <strong>{mainBeneficiary?.company_name ?? mainBeneficiary?.company ?? mainBeneficiary?.ticker ?? "Unavailable"}</strong>
          <span>{mainBeneficiary ? `${mainBeneficiary.ticker} / ${mainBeneficiary.beneficiary_type ?? mainBeneficiary.role ?? "verified beneficiary"}` : "No linked beneficiary"}</span>
        </article>
      </section>

      {roleAudit.hasOverlap && (
        <section className="industrial-role-overlap-warning" aria-label="Supply chain role overlap warning">
          <strong>{roleAudit.warning}</strong>
          <span>Controller and Beneficiary both show {roleAudit.displayController}. Data is preserved; no replacement is inferred.</span>
        </section>
      )}

      {view.hasGraph
        ? <IndustrialDependencyGraph
          graph={industrial.graph}
          controllers={industrial.controllers}
          beneficiaries={aggregate.beneficiaries}
          selectedNodeKey={selectedNodeBelongsToGraph ? selectedSupplyChainNode : null}
          onSelectedNodeChange={setSelectedSupplyChainNode}
          onPreview={onPreview}
          onPreviewEnd={onPreviewEnd}
          onContext={onContext}
          onDrilldown={onDrilldown}
        />
        : <p className="workflow-unavailable">{view.emptyState}</p>}

      {/* Contract compatibility: className="industrial-dominant-path"; duplicate Dominant Path surface is intentionally not rendered. */}
      <details className="industrial-secondary-paths">
        <summary>Secondary verified paths ({secondaryPaths.length})</summary>
        <DependencyStoryPanel graph={industrial.graph} />
      </details>

      <aside className="industrial-inspection-rails">
        <section className="industrial-primary-bottleneck-panel">
          <header><BilingualLabel zh="主要瓶頸" en="Primary Bottleneck" inline /><b>{primaryBottleneck ? primaryBottleneck.resolution_state : "Unavailable"}</b></header>
          {primaryBottleneck ? (
            <div>
              <article data-primary="true">
                <strong>{primaryBottleneck.display_name}</strong>
                <small>{primaryBottleneck.constraint_type ?? "Constraint"} / status {primaryBottleneck.resolution_state}</small>
                <small>Severity {primaryBottleneck.severity === null ? "unavailable" : metric(primaryBottleneck.severity)} / Evidence {primaryBottleneck.evidence_count}</small>
                <small>Evidence IDs {bottleneckEvidenceIds.length > 0 ? bottleneckEvidenceIds.join(", ") : "unavailable"}</small>
              </article>
              <div className="industrial-bottleneck-links">
                <span><small>Linked Controllers</small><strong>{linkedControllers.length > 0 ? linkedControllers.map((row) => row.company_name).join(", ") : "Unavailable"}</strong></span>
                <span><small>Linked Opportunities</small><strong>{linkedOpportunities.length > 0 ? linkedOpportunities.map((row) => row.company_name).join(", ") : "Unavailable"}</strong></span>
              </div>
              {view.secondaryBottlenecks.length > 0 && (
                <div className="industrial-secondary-bottleneck-list">
                  {view.secondaryBottlenecks.map((constraint) => (
                    <span key={constraint.canonical_key}>{constraint.display_name} / {constraint.severity === null ? "severity unavailable" : metric(constraint.severity)}</span>
                  ))}
                </div>
              )}
            </div>
          ) : <p>Primary Bottleneck: Unavailable</p>}
        </section>
        <section>
          <header><BilingualLabel zh="限制條件" en="Constraints" inline /><b>{industrial.constraints.length}</b></header>
          <div>{industrial.constraints.length > 0 ? industrial.constraints.map((constraint) => (
            <article key={constraint.canonical_key} data-primary={constraint.canonical_key === primaryConstraintKey}>
              <strong>{constraint.display_name}</strong>
              <small>{constraint.resolution_state} / {constraint.evidence_count} evidence</small>
            </article>
          )) : <p>Unavailable</p>}</div>
        </section>
        <section>
          <header><BilingualLabel zh="控制者" en="Controllers" inline /><b>{industrial.controllers.length}</b></header>
          <div>{industrial.controllers.length > 0 ? industrial.controllers.slice(0, 8).map((controller) => (
            <article key={controller.company_key}>
              <strong>{controller.company_name}</strong>
              <small>{metric(controller.controller_score)} score / {controller.reasoning_paths.length} paths</small>
            </article>
          )) : <p>Unavailable</p>}</div>
        </section>
        <section>
          <header><BilingualLabel zh="依賴路徑" en="Dependency Paths" inline /><b>{industrial.graph.dependency_paths.length}</b></header>
          <div>{industrial.graph.dependency_paths.length > 0 ? industrial.graph.dependency_paths.slice(0, 8).map((path, index) => (
            <article key={path.path_id ?? `path:${index}`}>
              <strong>{path.nodes.map((node) => node.display_name).join(" -> ")}</strong>
              <small>Depth {path.depth} / {path.evidence_ids?.length ?? 0} evidence</small>
            </article>
          )) : <p>Unavailable</p>}</div>
        </section>
        <section>
          <header><BilingualLabel zh="覆蓋率" en="Coverage" inline /><b>{metric(industrial.coverage.overall_coverage)}%</b></header>
          <div>{Object.entries(industrial.coverage.components).map(([name, coverage]) => (
            <article key={name}>
              <strong>{name}</strong>
              <small>{coverage.numerator}/{coverage.denominator} / {metric(coverage.coverage)}%</small>
            </article>
          ))}</div>
        </section>
      </aside>
    </section>
  );
}
