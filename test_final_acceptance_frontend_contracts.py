from pathlib import Path


ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "frontend" / "src" / "components" / "Dashboard.tsx"
THEME_RESEARCH = ROOT / "frontend" / "src" / "components" / "ThemeResearchPage.tsx"
STOCK_API = ROOT / "frontend" / "src" / "services" / "stockApi.ts"
THEME_SCOUT = ROOT / "frontend" / "src" / "components" / "ThemeScoutPage.tsx"
SUPPLY_PROJECTION = ROOT / "frontend" / "src" / "lib" / "supplyChainIntelligence.ts"
THEME_WORKFLOW = ROOT / "frontend" / "src" / "components" / "theme-workspace" / "ThemeInvestmentWorkflow.tsx"
SUPPLY_WORKFLOW = ROOT / "frontend" / "src" / "components" / "theme-workspace" / "IndustrialDependencyWorkflow.tsx"
SCOUT_WORKFLOW = ROOT / "frontend" / "src" / "components" / "scout-workspace" / "ScoutDiscoveryWorkflow.tsx"
DEPENDENCY_GRAPH = ROOT / "frontend" / "src" / "components" / "theme-workspace" / "IndustrialDependencyGraph.tsx"


def test_context_dock_deduplicates_tags_before_rendering() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")

    assert "Array.from(new Set(values.filter(Boolean)))" in source


def test_theme_selection_has_one_aggregate_fetch_owner() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    theme_research = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "fetchThemeIntelligence(themeSubject" in dashboard
    assert "fetchThemeIntelligence(selectedThemeName" not in theme_research


def test_exact_search_routing_prioritizes_approved_theme_and_ticker_aliases() -> None:
    source = STOCK_API.read_text(encoding="utf-8")

    assert "OMNIBOX_THEMES" not in source
    assert "fetchThemeRegistry" in source
    assert "buildRegistrySearchItems" in source
    assert "matchesRegistryTheme" in source
    assert 'symbol: "TER", name: "Teradyne, Inc."' in source
    assert "exactKnownTicker" in source
    assert "exactThemeMatch" in source


def test_rotation_has_one_abortable_frontend_fetch_owner() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "fetchSectorRotation({ signal: controller.signal })" in source
    assert "const controller = new AbortController()" in source
    assert "controller.abort()" in source
    assert "rotationSnapshot:" in source


def test_rotation_normalizes_snapshot_without_silent_row_dropping() -> None:
    source = STOCK_API.read_text(encoding="utf-8")

    assert "export function normalizeRotationSnapshot" in source
    assert '"sector_ranking"' in source
    assert "rotationStatus" in source
    assert "filter((row) => row.sector)" in source
    assert "filter((row) => row.score)" not in source


def test_rotation_diagnostics_render_backend_owned_snapshot_fields() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "rotationSnapshot?.market_regime" in source
    assert "rotationSnapshot?.risk_appetite" in source
    assert "rotationSnapshot?.volatility_state" in source
    assert "rotationSnapshot?.rotation_bias" in source
    assert "rotationModel.diagnostics.map" not in source


def test_theme_research_uses_compact_evidence_grid() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    for label in (
        "Catalysts",
        "Constraints",
        "Beneficiaries",
        "Supply Chain",
        "Industrial Graph",
        "Controller",
        "Opportunity",
        "Decision Packet",
    ):
        assert label in source
    assert "theme-evidence-grid" in source
    assert "theme-evidence-gap-chip" in source
    assert "key={`${section.label}-${index}`}" in source
    assert "key={fact}" not in source
    assert ".theme-evidence-grid" in css
    assert ".theme-evidence-gap-chip" in css


def test_sparse_theme_visuals_are_conditional_not_large_blank_panels() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "hasSupplyChainVisual" in source
    assert "hasCatalystVisual" in source
    assert "CompactEvidenceGrid" in source
    assert 'className="ai-bars"' not in source


def test_canonical_theme_aliases_and_ticker_precedence() -> None:
    source = STOCK_API.read_text(encoding="utf-8")

    assert "CANONICAL_THEME_ALIASES" in source
    assert '"cpo": "cpo_photonics"' in source
    assert '"cpo_photonics": "cpo_photonics"' in source
    assert '"cowos": "cowos"' in source
    assert '"glass_substrate": "glass_substrate"' in source
    assert "OMNIBOX_THEMES" not in source
    assert "registryThemes.some((item) => matchesRegistryTheme(item, normalized))" in source
    assert source.index("exactKnownTicker(query)") < source.index("exactThemeMatch(query, registryThemes)")


def test_theme_intelligence_coalesces_duplicate_inflight_requests() -> None:
    source = STOCK_API.read_text(encoding="utf-8")

    assert "themeIntelligenceRequests" in source
    assert "themeIntelligenceRequests.get(normalized)" in source
    assert "themeIntelligenceRequests.set(normalized, request)" in source


def test_canonical_theme_identity_chain_is_preserved() -> None:
    api_source = STOCK_API.read_text(encoding="utf-8")
    dashboard_source = DASHBOARD.read_text(encoding="utf-8")
    research_source = THEME_RESEARCH.read_text(encoding="utf-8")

    for theme_id, display_name in (
        ("hbm", "HBM"),
        ("cowos", "CoWoS"),
        ("glass_substrate", "Glass Substrate"),
        ("cpo_photonics", "CPO"),
        ("ai_infrastructure", "AI Infrastructure"),
        ("data_center_cooling", "Data Center Cooling"),
    ):
        assert f'"{theme_id}": "{display_name}"' in api_source

    assert "result.workspaceAction ?? drilldown.action" in dashboard_source
    assert "selectedEntityTheme,\n    selectedTheme" in research_source
    assert "resolveCanonicalThemeIdentity" in dashboard_source
    assert "resolveCanonicalThemeSelection" in research_source
    assert "<strong>{selectedThemeName}</strong>" in research_source
    assert "selectedScore?.theme ?? selectedThemeName" not in research_source
    assert 'if (target.kind === "supply" || target.kind === "supply_chain") return target.name ?? target.subject ?? null;' in dashboard_source
    assert "const leavingThemeResearch = !isThemeResearchModule(activeTab);" in dashboard_source
    assert "if (leavingThemeResearch) abortContextThemeFetch();" in dashboard_source


def test_theme_identity_trace_logs_raw_normalized_and_request_id() -> None:
    api_source = STOCK_API.read_text(encoding="utf-8")
    dashboard_source = DASHBOARD.read_text(encoding="utf-8")
    research_source = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "traceThemeIdentity" in api_source
    assert 'console.info(`[theme-identity] ${JSON.stringify' in api_source
    assert '"aggregate_request"' in api_source
    assert '"search_navigation"' in dashboard_source
    assert '"theme_selection"' in research_source
    assert '"supply_chain_selection"' in research_source


def test_theme_command_view_replaces_legacy_ai_dashboard_surfaces() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")

    assert 'className="theme-research-surface"' in source
    assert "ThemeInvestmentWorkflow" in source
    assert 'className="theme-validation-surface"' in source
    assert source.index("Legacy Phase 10 command composition") < source.index('className="ai-panel ai-hero"')


def test_industrial_workspace_renders_connected_graph_and_supply_flow() -> None:
    source = DEPENDENCY_GRAPH.read_text(encoding="utf-8")
    workflow = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    projection = (ROOT / "frontend" / "src" / "lib" / "industrialGraphProjection.ts").read_text(encoding="utf-8")

    assert 'aria-label="Persisted industrial dependency graph"' in source
    assert "<svg" in source
    assert "industrial-inspection-rails" in workflow
    assert "Controllers" in workflow
    assert "Resolution Enabler" in projection
    assert "Direct Beneficiary" in projection
    assert "Indirect Beneficiary" in projection


def test_scout_is_evidence_first_not_gauge_first() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")

    assert "研究佇列" in source
    assert "Research Queue" in source
    assert "訊號" in source
    assert "訊號叢集" in source
    assert "<Gauge" not in source
    assert "CoverageRadar" not in source
    assert "Candidate Health" not in source


def test_independent_workflow_components_exist_and_are_routed_separately() -> None:
    research = THEME_RESEARCH.read_text(encoding="utf-8")
    scout_page = THEME_SCOUT.read_text(encoding="utf-8")

    for path in (THEME_WORKFLOW, SUPPLY_WORKFLOW, SCOUT_WORKFLOW, DEPENDENCY_GRAPH):
        assert path.exists()

    assert "ThemeInvestmentWorkflow" in research
    assert "IndustrialDependencyWorkflow" in research
    assert "ThemeIndustrialWorkspace" not in research
    assert "ScoutDiscoveryWorkflow" in scout_page


def test_theme_workflow_is_an_investment_dossier_not_a_supply_graph() -> None:
    source = THEME_WORKFLOW.read_text(encoding="utf-8")
    expected_stages = (
        "thesis",
        "why-now",
        "bottleneck",
        "controller",
        "beneficiary",
        "opportunity",
        "validation",
        "decision",
    )

    positions = [source.index(f'data-workflow-stage="{stage}"') for stage in expected_stages]
    assert positions == sorted(positions)
    assert "IndustrialDependencyGraph" not in source
    assert "industrial-graph-columns" not in source
    assert "主題論點" in source and source.index("主題論點") < source.index("Thesis")
    assert "決策" in source and source.index("決策") < source.index("Decision")


def test_supply_workflow_uses_persisted_svg_graph_as_primary_surface() -> None:
    workflow = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    graph = DEPENDENCY_GRAPH.read_text(encoding="utf-8")

    assert "IndustrialDependencyGraph" in workflow
    assert 'className="industrial-bottleneck-workspace"' in workflow
    assert "constraints" in workflow
    assert "controllers" in workflow
    assert "coverage" in workflow
    assert "<svg" in graph
    assert "projectIndustrialGraph" in graph
    assert "relationshipType" in graph
    assert "ThemeInvestmentWorkflow" not in workflow
    assert "Decision Packet" not in workflow


def test_scout_workflow_is_signals_first_and_selector_is_compact() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    expected_stages = (
        "signals",
        "clusters",
        "constraint-watch",
        "research-queue",
        "validation",
        "approval",
    )

    positions = [source.index(f'data-workflow-stage="{stage}"') for stage in expected_stages]
    assert positions == sorted(positions)
    assert 'className="scout-candidate-selector"' in source
    assert "scout-candidate-tape" not in source
    assert "CoverageRadar" not in source
    assert "Candidate Health" not in source
    assert "訊號" in source and source.index("訊號") < source.index("Signals")


def test_rotation_visual_contract_uses_five_distinct_non_olive_states() -> None:
    source = (ROOT / "frontend" / "src" / "lib" / "rotationWorkspace.ts").read_text(encoding="utf-8")
    treemap = (ROOT / "frontend" / "src" / "components" / "terminal" / "MarketTreemap.tsx").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "projectRotationVisual" in source
    assert "--rotation-fill" in treemap
    assert "--rotation-border" in treemap
    assert "--rotation-glow" in treemap
    for state in ("strong-leader", "improving", "neutral", "weakening", "laggard"):
        assert f'data-state="{state}"' in THEME_RESEARCH.read_text(encoding="utf-8")
    assert '#4c4421' not in css
    assert '#cab968' not in css


def test_phase1211g_rotation_uses_within_state_intensity_and_muted_neutral() -> None:
    source = (ROOT / "frontend" / "src" / "lib" / "rotationWorkspace.ts").read_text(encoding="utf-8")

    assert "normalizeRotationBandIntensity" in source
    neutral_start = source.index('neutral: { fillFamily: "graphite"')
    neutral_end = source.index("weakening:", neutral_start)
    neutral_palette = source[neutral_start:neutral_end].lower()
    assert "yellow" not in neutral_palette
    assert "olive" not in neutral_palette
    assert "#151a20" in neutral_palette


def test_phase1211g_theme_is_a_weighted_decision_spine() -> None:
    source = THEME_WORKFLOW.read_text(encoding="utf-8")

    assert 'className="theme-decision-spine"' in source
    assert 'className="theme-thesis-strip"' in source
    assert 'className="theme-bottleneck-anchor"' in source
    assert 'className="theme-decision-bridge"' in source
    assert "IndustrialDependencyGraph" not in source
    for zh, en in (
        ("主題論點", "Thesis"),
        ("為何現在", "Why Now"),
        ("關鍵瓶頸", "Bottleneck"),
        ("控制層", "Controller"),
        ("受益者", "Beneficiary"),
        ("機會", "Opportunity"),
        ("驗證", "Validation"),
        ("決策", "Decision"),
    ):
        assert source.index(zh) < source.index(en)


def test_phase1211g_supply_chain_is_bottleneck_centered_not_seven_columns() -> None:
    projection = (ROOT / "frontend" / "src" / "lib" / "industrialGraphProjection.ts").read_text(encoding="utf-8")
    graph = DEPENDENCY_GRAPH.read_text(encoding="utf-8")
    workflow = SUPPLY_WORKFLOW.read_text(encoding="utf-8")

    assert "constraintAnchor" in projection
    assert "upstreamNodes" in projection
    assert "companyGroups" in projection
    assert "focusPathId" in projection
    assert "selectedNodeKey" in graph
    assert "selectedEdgeKey" in graph
    assert "SUPPLY_WORKFLOW_STAGES.map" not in graph
    assert "industrial-graph-layer-labels" not in graph
    assert "<text" not in graph
    assert 'className="industrial-bottleneck-workspace"' in workflow


def test_phase1211g_scout_queue_precedes_compact_metrics() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")

    assert 'className="scout-research-queue-workspace"' in source
    assert 'className="scout-metadata-strip"' in source
    assert source.index('data-workflow-stage="research-queue"') < source.index(
        'className="scout-metadata-strip"'
    )
    assert source.index("研究佇列") < source.index("Research Queue")


def test_phase1211g_workspaces_keep_distinct_primary_compositions() -> None:
    theme = THEME_WORKFLOW.read_text(encoding="utf-8")
    supply = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    scout = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    treemap = (ROOT / "frontend" / "src" / "components" / "terminal" / "MarketTreemap.tsx").read_text(encoding="utf-8")

    assert "theme-decision-spine" in theme
    assert "industrial-bottleneck-workspace" in supply
    assert "scout-research-queue-workspace" in scout
    assert "rotation-workspace" in treemap
    assert "industrial-bottleneck-workspace" not in theme
    assert "theme-decision-spine" not in supply
    assert "theme-decision-spine" not in scout


def test_phase1211h_uses_shared_deterministic_narrative_projection() -> None:
    source = (ROOT / "frontend" / "src" / "lib" / "researchNarrative.ts").read_text(encoding="utf-8")

    assert "buildThemeNarrative" in source
    assert "buildDependencyStory" in source
    assert "buildScoutHypothesisNarrative" in source
    assert "buildRotationStory" in source
    assert "evidenceIds" in source
    assert "availabilityState" in source
    assert "sourceField" in source
    assert "recommendation" not in source.lower()
    assert "target price" not in source.lower()


def test_phase1211h_narrative_panels_are_wired_without_inline_logic() -> None:
    theme = THEME_WORKFLOW.read_text(encoding="utf-8")
    supply = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    scout = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    rotation = THEME_RESEARCH.read_text(encoding="utf-8")

    assert "ResearchNarrativePanel" in theme
    assert "buildThemeNarrative(" not in theme
    assert "DependencyStoryPanel" in supply
    assert "buildDependencyStory(" not in supply
    assert "ScoutHypothesisPanel" in scout
    assert "buildScoutHypothesisNarrative(" not in scout
    assert "CapitalFlowStory" in rotation
    assert "buildRotationStory(" not in rotation


def test_p0_supply_chain_renders_primary_bottleneck_projection() -> None:
    workflow = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    projection = SUPPLY_PROJECTION.read_text(encoding="utf-8")
    graph = DEPENDENCY_GRAPH.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "selectPrimaryBottleneck" in projection
    assert "primaryBottleneck" in workflow
    assert "Primary Bottleneck" in workflow
    assert "industrial-primary-bottleneck-panel" in workflow
    assert "industrial-secondary-bottleneck-list" in workflow
    assert "linkedControllers" in workflow
    assert "linkedOpportunities" in workflow
    assert "data-primary-bottleneck={projection.constraintAnchor" in graph
    assert ".industrial-graph-node[data-primary-bottleneck=\"true\"]" in css


def test_p0_rotation_treemap_label_density_and_raw_flow_area() -> None:
    treemap = (ROOT / "frontend" / "src" / "components" / "terminal" / "MarketTreemap.tsx").read_text(encoding="utf-8")
    rotation = THEME_RESEARCH.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "layoutTreemap(safeItems, 1000, 600)" in treemap
    assert "weight: sectorWeight(sector)" in rotation
    assert "capitalFlowWeight(finite(sector.flow))" in rotation
    assert 'data-label-density={size}' in treemap
    assert 'size !== "tiny" && <span className="market-treemap-score"' in treemap
    assert 'size === "medium" || size === "large"' in treemap
    assert 'className="market-treemap-flow"' in treemap
    assert 'size === "large" && <span className="market-treemap-momentum"' in treemap
    assert ".market-treemap-tile{overflow:hidden" in css.replace(" ", "")
    assert "white-space:nowrap" in css
    assert "text-overflow:ellipsis" in css


def test_p0_scout_summary_and_queue_precede_evidence() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "scout-top-candidate-summary" in source
    assert "AI Top Candidate" in source
    assert "Research priority" in source
    assert "keyBottleneck" in source
    assert "evidenceLinkedCompanies" in source
    assert "why-theme-matters" in source
    assert source.index("scout-top-candidate-summary") < source.index("scout-validation-stage")
    assert source.index('data-workflow-stage="research-queue"') < source.index('data-workflow-stage="validation"')
    assert ".scout-top-candidate-summary" in css
    assert ".why-theme-matters" in css


def test_p0_theme_core_reading_path_is_visually_primary() -> None:
    source = THEME_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "theme-core-reading-path" in source
    assert source.index('data-workflow-stage="bottleneck"') < source.index('data-workflow-stage="controller"')
    assert source.index('data-workflow-stage="controller"') < source.index('data-workflow-stage="beneficiary"')
    assert source.index('data-workflow-stage="beneficiary"') < source.index('data-workflow-stage="opportunity"')
    assert ".theme-core-reading-path" in css
    assert ".theme-core-reading-path .theme-bottleneck-anchor" in css


def test_phase1212a_supply_chain_hero_precedes_supporting_graph() -> None:
    workflow = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    graph = DEPENDENCY_GRAPH.read_text(encoding="utf-8")
    projection = (ROOT / "frontend" / "src" / "lib" / "industrialGraphProjection.ts").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "industrial-bottleneck-hero" in workflow
    assert "industrial-hero-stage" in workflow
    assert "mainController" in workflow
    assert "mainBeneficiary" in workflow
    assert workflow.index('className="industrial-bottleneck-hero"') < workflow.index("view.hasGraph")
    assert workflow.index("view.hasGraph") < workflow.index("<DependencyStoryPanel")
    assert 'data-hero-stage="bottleneck"' in workflow
    assert 'data-hero-stage="controller"' in workflow
    assert 'data-hero-stage="beneficiary"' in workflow
    assert "ANCHOR_Y" in projection
    assert 'data-primary-bottleneck={projection.constraintAnchor' in graph
    assert ".industrial-bottleneck-hero" in css
    assert ".industrial-graph-node[data-primary-bottleneck=\"true\"]" in css
    assert "transform:scale(1.12)" in css


def test_phase1212a_scout_company_names_are_primary_and_evidence_is_secondary() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    scout = (ROOT / "frontend" / "src" / "lib" / "themeScout.ts").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "companyDisplayLabel" in source
    assert "companyEvidenceMetadata" in source
    assert "Evidence metadata" in source
    assert "<details" in source
    assert "companyLabel(company.canonicalKey)" not in source
    assert "displayName" in scout
    assert "evidenceId" in scout
    assert ".scout-company-chip" in css
    assert ".scout-company-evidence-metadata" in css


def test_phase1212a_rotation_treemap_dominates_and_labels_do_not_overlap() -> None:
    treemap = (ROOT / "frontend" / "src" / "components" / "terminal" / "MarketTreemap.tsx").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert 'data-density="tiny"' in treemap
    assert 'data-density="small"' in treemap
    assert 'data-density="medium"' in treemap
    assert 'data-density="large"' in treemap
    assert 'className="market-treemap-primary-metric"' in treemap
    assert 'className="market-treemap-secondary-metric"' in treemap
    assert ".rotation-layout" in css
    assert "grid-template-columns:minmax(0,1fr)" in css
    compact_css = css.replace(" ", "")
    assert ".rotation-ranking-panel{grid-column:2;grid-row:2;opacity:.72" in compact_css
    assert ".rotation-treemap-panel{grid-column:1;grid-row:1/span3" in compact_css
    assert ".market-treemap-tile[data-label-density=\"large\"] .market-treemap-state" in css
    assert ".market-treemap-tile[data-label-density=\"medium\"] .market-treemap-momentum" in css
    assert "display:none" in css


def test_phase1212a_theme_decision_spine_dominates_narrative_context() -> None:
    source = THEME_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert "theme-narrative-context" in source
    assert "theme-directional-spine" in source
    assert source.index("theme-core-reading-path") < source.index("theme-narrative-context")
    assert 'data-flow-stage="controller"' in source
    assert 'data-flow-stage="beneficiary"' in source
    assert 'data-flow-stage="opportunity"' in source
    assert ".theme-narrative-context" in css
    assert ".theme-directional-spine" in css
    assert ".theme-directional-spine::before" in css


def test_phase1211h_chinese_first_narrative_labels() -> None:
    files = [
        ROOT / "frontend" / "src" / "lib" / "researchNarrative.ts",
        ROOT / "frontend" / "src" / "components" / "theme-workspace" / "ResearchNarrativePanel.tsx",
        ROOT / "frontend" / "src" / "components" / "theme-workspace" / "DependencyStoryPanel.tsx",
        ROOT / "frontend" / "src" / "components" / "scout-workspace" / "ScoutHypothesisPanel.tsx",
        ROOT / "frontend" / "src" / "components" / "terminal" / "CapitalFlowStory.tsx",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in files)

    for label in ("研究敘事", "目前驅動", "關鍵瓶頸", "控制層", "證據鏈", "研究假設", "資金流敘事", "證據不足"):
        assert label in source
    assert source.index("研究敘事") < source.index("Research Narrative")
    assert source.index("證據不足") < source.index("Insufficient evidence")


def test_phase1212b_research_pipeline_workspace_contracts() -> None:
    pipeline_page = ROOT / "frontend" / "src" / "components" / "ResearchPipelinePage.tsx"
    pipeline_lib = ROOT / "frontend" / "src" / "lib" / "researchPipeline.ts"
    modules = ROOT / "frontend" / "src" / "modules" / "terminalModules.ts"
    stock_api = ROOT / "frontend" / "src" / "services" / "stockApi.ts"
    types = ROOT / "frontend" / "src" / "types" / "stock.ts"
    scout_page = ROOT / "frontend" / "src" / "components" / "ThemeScoutPage.tsx"

    assert pipeline_page.exists()
    source = "\n".join(path.read_text(encoding="utf-8") for path in [pipeline_page, pipeline_lib, modules, stock_api, types, scout_page])

    for status in ("DISCOVERED", "OBSERVING", "RESEARCHING", "VALIDATING", "REVIEW_READY", "MONITORING"):
        assert status in source
    assert "Research Pipeline" in source
    assert "Create Research Case" in source
    assert "manual" in source.lower()
    assert "fetchResearchPipeline" in source
    assert "createResearchPipelineCase" in source
    assert "transitionResearchPipelineCase" in source
    assert "linkResearchPipelineArtifact" in source


def test_phase1212b_pipeline_has_no_recommendation_language() -> None:
    files = [
        ROOT / "frontend" / "src" / "components" / "ResearchPipelinePage.tsx",
        ROOT / "frontend" / "src" / "lib" / "researchPipeline.ts",
    ]
    source = "\n".join(path.read_text(encoding="utf-8").lower() for path in files if path.exists())
    forbidden = ("buy", "sell", "target price", "recommendation", "alpha score", "trading signal")
    for phrase in forbidden:
        assert phrase not in source


def test_phase1212c_rotation_is_capital_flow_only_primary_surface() -> None:
    source = THEME_RESEARCH.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")
    rotation_start = source.index('if (activeTab === "rotation")')
    rotation_end = source.index('if (activeTab === "supply-chain")')
    rotation = source[rotation_start:rotation_end]

    assert 'className="rotation-capital-flow-surface"' in rotation
    assert 'className="rotation-unified-intelligence-panel"' in rotation
    assert "rotation-ranking-panel" not in rotation
    assert "Sector Beneficiaries" not in rotation
    assert "rotation-sector-companies" not in rotation
    assert "controllers" not in rotation.lower()
    assert "opportunities" not in rotation.lower()
    assert ".rotation-capital-flow-surface" in css
    assert "max-width:60%" in css.replace(" ", "")


def test_phase1212c_scout_keeps_discovery_queue_primary_and_evidence_secondary() -> None:
    source = SCOUT_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert 'className="scout-emerging-radar"' in source
    assert 'className="scout-research-command-surface"' in source
    assert source.index("scout-top-candidate-summary") < source.index("scout-workflow-stage scout-signals-stage")
    assert source.index("scout-queue-stage") < source.index("scout-validation-stage")
    assert "IndustrialDependencyGraph" not in source
    assert "controller ranking" not in source.lower()
    assert "opportunity ranking" not in source.lower()
    assert "decision packet" not in source.lower()
    assert ".scout-company-evidence-metadata" in css


def test_phase1212c_theme_is_memo_with_selector_not_graph_or_queue() -> None:
    source = THEME_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert 'className="theme-selector-ribbon"' in source
    assert "WORKSPACE_THEME_RIBBON" not in source
    assert "registryThemes.map" in source
    assert "theme.theme_id" in source
    assert "theme.theme_name" in source
    assert "IndustrialDependencyGraph" not in source
    assert "IndustrialDependencyWorkflow" not in source
    assert "Research Queue" not in source
    assert "Candidate Themes" not in source
    assert 'className="theme-opportunity-scroll"' in source
    assert ".theme-opportunity-scroll" in css
    assert "scrollbar-width:none" in css.replace(" ", "")


def test_phase1212c_supply_chain_is_industrial_map_not_investment_memo() -> None:
    source = SUPPLY_WORKFLOW.read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")

    assert 'className="supply-theme-selector"' in source
    assert "WORKSPACE_THEME_RIBBON" not in source
    assert "registryThemes.map" in source
    assert "theme.theme_id" in source
    assert "theme.theme_name" in source
    assert 'className="industrial-dominant-path"' in source
    assert 'className="industrial-secondary-paths"' in source
    assert "<details" in source
    assert "Investment Thesis" not in source
    assert "Conviction" not in source
    assert "Decision Packet" not in source
    assert "Opportunity Ranking" not in source
    assert ".industrial-dominant-path" in css
    assert ".industrial-secondary-paths" in css


def test_phase1212c_pipeline_remains_lifecycle_only() -> None:
    source = (ROOT / "frontend" / "src" / "components" / "ResearchPipelinePage.tsx").read_text(encoding="utf-8")
    assert "pipeline-board" in source
    assert "Manual transition" in source
    forbidden = ("MarketTreemap", "ScoutDiscoveryWorkflow", "IndustrialDependencyGraph", "Capital Flow Treemap")
    for phrase in forbidden:
        assert phrase not in source
