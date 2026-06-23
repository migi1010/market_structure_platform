import { layoutTreemap, type TreemapInput } from "./treemap";

export function treemapContractTest() {
  const items: TreemapInput[] = [
    { id: "technology", weight: 55 },
    { id: "energy", weight: 24 },
    { id: "utilities", weight: 12 },
    { id: "materials", weight: 0 },
  ];
  const layout = layoutTreemap(items, 1000, 600);
  const area = layout.reduce((sum, item) => sum + item.width * item.height, 0);
  const bounded = layout.every((item) => item.x >= 0 && item.y >= 0 && item.x + item.width <= 1000.001 && item.y + item.height <= 600.001);
  const nonOverlapping = layout.every((left, index) => layout.slice(index + 1).every((right) => (
    left.x + left.width <= right.x
    || right.x + right.width <= left.x
    || left.y + left.height <= right.y
    || right.y + right.height <= left.y
  )));
  return {
    count: layout.length,
    bounded,
    nonOverlapping,
    fillsSurface: Math.abs(area - 600000) < 1,
    largestLeads: layout.find((item) => item.id === "technology")!.width * layout.find((item) => item.id === "technology")!.height
      > layout.find((item) => item.id === "energy")!.width * layout.find((item) => item.id === "energy")!.height,
    fallbackVisible: layout.find((item) => item.id === "materials")!.width > 0,
  };
}
