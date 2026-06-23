import {
  ContextDock,
  DrilldownTrigger,
  FlowNode,
  HoverPreview,
  InteractiveTile,
  RiskOverlay,
  SignalPulse,
  TreemapSurface,
  MarketTreemap,
  CapitalFlowSurface,
  BeneficiaryMatrix,
  FlowRanking,
} from "./index";

export function InteractionPrimitiveUsageTest() {
  return (
    <div>
      <ContextDock title="Context" open collapsed onToggle={() => undefined} onClose={() => undefined}>
        Detail
      </ContextDock>
      <TreemapSurface>
        <InteractiveTile label="Theme" value={72} selected onClick={() => undefined} onDoubleClick={() => undefined} onPreview={() => undefined} onPreviewEnd={() => undefined} />
      </TreemapSurface>
      <FlowNode label="Supplier" value={66} active onClick={() => undefined} onDoubleClick={() => undefined} onPreview={() => undefined} onPreviewEnd={() => undefined} />
      <RiskOverlay label="Crowding" value={82} onClick={() => undefined} onDoubleClick={() => undefined} onPreview={() => undefined} onPreviewEnd={() => undefined} />
      <DrilldownTrigger label="Open stock" onClick={() => undefined} />
      <HoverPreview label="Preview">Context preview</HoverPreview>
      <SignalPulse tone="positive" />
      <MarketTreemap
        items={[{ id: "technology", label: "Technology", weight: 80, score: 82, momentum: 76 }]}
        selectedId="technology"
        depth="institutional"
        onPreviewEnd={() => undefined}
      />
      <CapitalFlowSurface
        source={{ id: "hbm", label: "HBM", strength: 84, flow: 79, risk: 41 }}
        lanes={[{ id: "memory", label: "Memory", strength: 88, beneficiaries: ["MU"] }]}
        selectedId="memory"
        depth="institutional"
        onPreviewEnd={() => undefined}
      />
      <BeneficiaryMatrix rows={[{ ticker: "NVDA", company: "NVIDIA", alpha: 91, risk: 44, flow: 87, relativeStrength: 92, exposure: 94 }]} contextLabel="AI Infrastructure" density="terminal" onPreviewEnd={() => undefined} />
      <FlowRanking rows={[{ id: "hbm", rank: 1, theme: "HBM", score: 94, flow: 98, momentum: 88, beneficiaries: [{ ticker: "MU" }], active: true }]} />
    </div>
  );
}
