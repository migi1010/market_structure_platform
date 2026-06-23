import { deriveFlowRanking } from "./flowRanking";
import type { ThemeScore } from "@/types/stock";

export function flowRankingContractTest() {
  const themes = [
    { theme: "HBM", theme_capital_flow_score: 98, momentum: 82, score: 91, leaders: [{ ticker: "MU" }] },
    { theme: "Networking", theme_capital_flow_score: 75, momentum: 94, score: 88, leaders: [{ ticker: "ANET" }] },
  ] as ThemeScore[];
  const byFlow = deriveFlowRanking(themes, { kind: "theme", name: "HBM" }, "flow");
  const byMomentum = deriveFlowRanking(themes, { kind: "theme", name: "HBM" }, "momentum");
  if (byFlow[0]?.theme !== "HBM" || byFlow[0]?.rank !== 1) throw new Error("Flow ranking must order strongest flow first.");
  if (byMomentum[0]?.theme !== "Networking") throw new Error("Momentum sorting must order strongest momentum first.");
  if (!byFlow[0]?.active || byFlow[0]?.beneficiaries[0]?.ticker !== "MU") throw new Error("Ranking must expose active selection and beneficiaries.");
  return true;
}
