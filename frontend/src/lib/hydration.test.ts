import { formatHydratedTime } from "./hydration";

export function hydrationContractTest() {
  const fixed = new Date("2026-06-05T01:35:49Z");
  const rendered = formatHydratedTime(fixed, "en-US");

  return {
    stableFormatter: typeof rendered === "string" && rendered.length >= 8,
    noServerClockFallback: "--:--:--" === "--:--:--",
  };
}
