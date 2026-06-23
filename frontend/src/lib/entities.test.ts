import { classifyEntityQuery, entityFromSearchResult, routeForEntity, type MarketEntity } from "./entities";

export function entityContractTest() {
  const entities: MarketEntity[] = [
    entityFromSearchResult({ symbol: "NVDA", name: "NVIDIA", exchange: "NASDAQ", type: "Equity" }),
    entityFromSearchResult({ symbol: "HBM", name: "HBM", exchange: "Theme", type: "Theme" }),
    entityFromSearchResult({ symbol: "SEMICONDUCTOR", name: "Semiconductor", exchange: "Sector", type: "Sector" }),
    entityFromSearchResult({ symbol: "GLASS-SUBSTRATE", name: "Glass Substrate", exchange: "Supply Chain", type: "Supply Chain" }),
    entityFromSearchResult({ symbol: "SMH", name: "SMH", exchange: "ETF", type: "ETF" }),
    entityFromSearchResult({ symbol: "BUBBLE-RISK", name: "Bubble Risk", exchange: "Risk", type: "Risk" }),
  ];

  return {
    classifications: [
      classifyEntityQuery("NVDA"),
      classifyEntityQuery("HBM"),
      classifyEntityQuery("Semiconductor"),
      classifyEntityQuery("Glass Substrate"),
      classifyEntityQuery("SMH"),
      classifyEntityQuery("Bubble Risk"),
    ],
    entityTypes: entities.map((entity) => entity.type),
    routes: entities.map(routeForEntity),
    relatedEntities: entities.flatMap((entity) => entity.relatedEntities),
  };
}
