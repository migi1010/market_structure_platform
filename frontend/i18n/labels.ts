import { enUS } from "./en-US";
import { zhTW } from "./zh-TW";

type Locale = "en-US" | "zh-TW";

export const dictionaries = {
  "en-US": enUS,
  "zh-TW": zhTW,
} as const;

export function bilingual(en: string, zh: string): string {
  return `${en} / ${zh}`;
}

export function label(path: keyof typeof enUS.labels, locale: Locale = "en-US"): string {
  return dictionaries[locale].labels[path];
}

export const institutionalLabels = {
  alphaScore: bilingual(enUS.labels.alphaScore, zhTW.labels.alphaScore),
  bubbleRisk: bilingual(enUS.labels.bubbleRisk, zhTW.labels.bubbleRisk),
  smartMoney: bilingual(enUS.labels.smartMoney, zhTW.labels.smartMoney),
  earningsQuality: bilingual(enUS.labels.earningsQuality, zhTW.labels.earningsQuality),
  sectorRotation: bilingual(enUS.labels.sectorRotation, zhTW.labels.sectorRotation),
  capitalFlow: bilingual(enUS.labels.capitalFlow, zhTW.labels.capitalFlow),
  institutionalConsensus: bilingual(enUS.labels.institutionalConsensus, zhTW.labels.institutionalConsensus),
  confidence: bilingual(enUS.labels.confidence, zhTW.labels.confidence),
  partialData: bilingual(enUS.labels.partialData, zhTW.labels.partialData),
} as const;

export const institutionalTooltips = {
  bubbleRisk: `${enUS.tooltips.bubbleRisk} ${zhTW.tooltips.bubbleRisk}`,
  alphaScore: `${enUS.tooltips.alphaScore} ${zhTW.tooltips.alphaScore}`,
  smartMoney: `${enUS.tooltips.smartMoney} ${zhTW.tooltips.smartMoney}`,
  earningsQuality: `${enUS.tooltips.earningsQuality} ${zhTW.tooltips.earningsQuality}`,
  themeScore: `${enUS.tooltips.themeScore} ${zhTW.tooltips.themeScore}`,
} as const;
