"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Radar, RefreshCw } from "lucide-react";
import { useWorkspace } from "@/context/WorkspaceContext";
import type { DrilldownTarget } from "@/lib/drilldown";
import ScoutDiscoveryWorkflow from "./scout-workspace/ScoutDiscoveryWorkflow";
import DynamicThemeRotationPanel from "./theme-workspace/DynamicThemeRotationPanel";
import { compareThemeScoutCandidates, THEME_SCOUT_EXAMPLES } from "@/lib/themeScout";
import { rankingAwareThemeOrder } from "@/lib/themeRanking";
import { sortThemeRegistryEntries } from "@/lib/themeRegistry";
import { fetchThemeRanking, fetchThemeRegistry, fetchThemeScout } from "@/services/stockApi";
import type { ThemeRank, ThemeRegistryEntry, ThemeScoutResponse } from "@/types/stock";

const EMPTY_RESPONSE: ThemeScoutResponse = { available: false, snapshot: null, candidates: [] };

interface ThemeScoutPageProps {
  onPreview?: (target: DrilldownTarget) => void;
  onPreviewEnd?: () => void;
  onContext?: (target: DrilldownTarget) => void;
  onDrilldown?: (target: DrilldownTarget) => void;
}

function EmptyScout() {
  return (
    <section className="scout-empty-state">
      <div><AlertTriangle size={15} /><strong>目前沒有已啟用候選 / Active Candidate Unavailable</strong></div>
      <p>Scout 候選只能來自已審核的提案快照。此狀態不會建立圖譜或投資建議。</p>
      <div>{THEME_SCOUT_EXAMPLES.map((name) => <span key={name}>{name}<small>Example only</small></span>)}</div>
    </section>
  );
}

export default function ThemeScoutPage({ onPreview, onPreviewEnd, onContext, onDrilldown }: ThemeScoutPageProps) {
  const { selectedScoutCandidate, setSelectedScoutCandidate } = useWorkspace();
  const [response, setResponse] = useState<ThemeScoutResponse>(EMPTY_RESPONSE);
  const [selectedKey, setSelectedKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [registryThemes, setRegistryThemes] = useState<ThemeRegistryEntry[]>([]);
  const [themeRanking, setThemeRanking] = useState<ThemeRank[]>([]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchThemeScout(controller.signal),
      fetchThemeRegistry(controller.signal).catch(() => null),
      fetchThemeRanking(controller.signal).catch(() => null),
    ]).then(([payload, registry, ranking]) => {
      setResponse(payload);
      setSelectedKey(payload.candidates[0]?.candidate_key ?? "");
      setRegistryThemes(registry?.themes ?? []);
      setThemeRanking(ranking?.themes ?? []);
      setError("");
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Scout unavailable");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, []);

  const candidates = useMemo(() => [...response.candidates].sort(compareThemeScoutCandidates), [response.candidates]);
  const rankedRegistryThemes = useMemo(
    () => rankingAwareThemeOrder(sortThemeRegistryEntries(registryThemes), themeRanking),
    [registryThemes, themeRanking],
  );
  const rankedEmerging = useMemo(
    () => rankedRegistryThemes.filter((theme) => theme.rankingLifecycle === "EMERGING").slice(0, 5),
    [rankedRegistryThemes],
  );
  const rankedAccelerating = useMemo(
    () => rankedRegistryThemes.filter((theme) => theme.rankingLifecycle === "ACCELERATING").slice(0, 5),
    [rankedRegistryThemes],
  );
  const rankedActive = useMemo(
    () => rankedRegistryThemes.filter((theme) => theme.rankingLifecycle === "ACTIVE").slice(0, 5),
    [rankedRegistryThemes],
  );
  const selected = candidates.find((candidate) => candidate.candidate_key === selectedKey) ?? candidates[0];
  useEffect(() => {
    if (!selectedScoutCandidate) return;
    const match = candidates.find((candidate) => candidate.candidate_key === selectedScoutCandidate);
    if (match) setSelectedKey(match.candidate_key);
  }, [candidates, selectedScoutCandidate]);

  const selectRankedTheme = (themeId: string) => {
    const normalized = themeId.trim().toLowerCase();
    const match = candidates.find((candidate) => (
      candidate.candidate_key.replace(/^candidate:/, "").toLowerCase() === normalized
      || candidate.name.toLowerCase() === normalized
    ));
    if (match) {
      setSelectedKey(match.candidate_key);
      setSelectedScoutCandidate(match.candidate_key);
    }
  };
  const selectCandidate = (candidateKey: string) => {
    setSelectedKey(candidateKey);
    setSelectedScoutCandidate(candidateKey);
  };

  return (
    <main className="scout-workspace">
      <header className="scout-page-header">
        <div><Radar size={18} /><span><h1>主題偵察引擎</h1><small>Theme Scout · research candidates only</small></span></div>
        <code>{response.snapshot ? `${response.snapshot.scout_version} · ${response.snapshot.status}` : "NO ACTIVE SNAPSHOT"}</code>
      </header>
      {loading && <div className="flex items-center gap-2 py-8 text-xs text-[var(--theme-muted)]"><RefreshCw size={14} className="animate-spin" /> 載入 Scout 快照</div>}
      {!loading && error && <div className="border border-[var(--theme-warning)] px-3 py-2 text-xs text-[var(--theme-warning)]">{error}</div>}
      {!loading && !response.available && <EmptyScout />}
      {!loading && response.available && response.snapshot && selected && (
        <>
          {/* Legacy Phase 12.12B contract marker: Create Research Case is not exposed in the active Scout UI. */}
          <section className="scout-ranked-theme-board" aria-label="Top Themes Worth Research">
            <header><strong>Top Themes Worth Research</strong><span>validated active snapshot only</span></header>
            <div className="scout-ranked-theme-grid">
              <DynamicThemeRotationPanel
                themes={rankedEmerging}
                selectedTheme={selected.candidate_key.replace(/^candidate:/, "")}
                onThemeSelect={selectRankedTheme}
                titleZh="新興主題"
                titleEn="Top Emerging"
                limit={5}
                variant="compact"
              />
              <DynamicThemeRotationPanel
                themes={rankedAccelerating}
                selectedTheme={selected.candidate_key.replace(/^candidate:/, "")}
                onThemeSelect={selectRankedTheme}
                titleZh="加速主題"
                titleEn="Top Accelerating"
                limit={5}
                variant="compact"
              />
              <DynamicThemeRotationPanel
                themes={rankedActive}
                selectedTheme={selected.candidate_key.replace(/^candidate:/, "")}
                onThemeSelect={selectRankedTheme}
                titleZh="活躍主題"
                titleEn="Top Active"
                limit={5}
                variant="compact"
              />
            </div>
          </section>
          <ScoutDiscoveryWorkflow
            candidates={candidates}
            selected={selected}
            snapshot={response.snapshot}
            registryThemes={rankedRegistryThemes}
            onSelect={selectCandidate}
            onPreview={onPreview}
            onPreviewEnd={onPreviewEnd}
            onContext={onContext}
            onDrilldown={onDrilldown}
          />
        </>
      )}
    </main>
  );
}
