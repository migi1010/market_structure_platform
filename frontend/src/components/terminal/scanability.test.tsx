import {
  BilingualLabel,
  ConfidenceMeter,
  FlowIndicator,
  HeatStrip,
  SectorIcon,
  SparklineMini,
  StatusDot,
  ThemeIcon,
  TickerLogo,
} from "./index";

export function ScanabilityPrimitiveUsageTest() {
  return (
    <div>
      <StatusDot state="accumulation" label="Accumulation" />
      <HeatStrip value={72} />
      <ConfidenceMeter value={64} label="Confidence" />
      <TickerLogo ticker="NVDA" name="NVIDIA" />
      <SectorIcon sector="Semiconductors" />
      <ThemeIcon theme="AI Infrastructure" />
      <FlowIndicator value={18} />
      <SparklineMini values={[42, 48, 46, 55, 61]} />
      <BilingualLabel zh="資金輪動" en="Capital Rotation" />
    </div>
  );
}
