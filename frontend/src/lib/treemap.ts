export interface TreemapInput {
  id: string;
  weight?: number | null;
}

export interface TreemapRect extends TreemapInput {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface AreaItem extends TreemapInput {
  area: number;
}

interface Bounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

function positiveWeight(value: number | null | undefined): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : 1;
}

function worstRatio(row: AreaItem[], side: number): number {
  if (row.length === 0 || side <= 0) return Number.POSITIVE_INFINITY;
  const total = row.reduce((sum, item) => sum + item.area, 0);
  const min = Math.min(...row.map((item) => item.area));
  const max = Math.max(...row.map((item) => item.area));
  const sideSquared = side * side;
  return Math.max((sideSquared * max) / (total * total), (total * total) / (sideSquared * min));
}

function placeRow(row: AreaItem[], bounds: Bounds, output: TreemapRect[]): Bounds {
  const rowArea = row.reduce((sum, item) => sum + item.area, 0);
  if (bounds.width >= bounds.height) {
    const rowWidth = bounds.height > 0 ? rowArea / bounds.height : 0;
    let y = bounds.y;
    row.forEach((item, index) => {
      const height = index === row.length - 1 ? bounds.y + bounds.height - y : item.area / rowWidth;
      output.push({ ...item, x: bounds.x, y, width: rowWidth, height });
      y += height;
    });
    return { x: bounds.x + rowWidth, y: bounds.y, width: Math.max(0, bounds.width - rowWidth), height: bounds.height };
  }
  const rowHeight = bounds.width > 0 ? rowArea / bounds.width : 0;
  let x = bounds.x;
  row.forEach((item, index) => {
    const width = index === row.length - 1 ? bounds.x + bounds.width - x : item.area / rowHeight;
    output.push({ ...item, x, y: bounds.y, width, height: rowHeight });
    x += width;
  });
  return { x: bounds.x, y: bounds.y + rowHeight, width: bounds.width, height: Math.max(0, bounds.height - rowHeight) };
}

export function layoutTreemap(items: TreemapInput[], width: number, height: number): TreemapRect[] {
  if (items.length === 0 || width <= 0 || height <= 0) return [];
  const totalWeight = items.reduce((sum, item) => sum + positiveWeight(item.weight), 0);
  const totalArea = width * height;
  const remaining = items
    .map((item) => ({ ...item, area: totalArea * positiveWeight(item.weight) / totalWeight }))
    .sort((left, right) => right.area - left.area);
  const output: TreemapRect[] = [];
  let bounds: Bounds = { x: 0, y: 0, width, height };
  let row: AreaItem[] = [];

  while (remaining.length > 0) {
    const next = remaining[0];
    const side = Math.min(bounds.width, bounds.height);
    if (row.length === 0 || worstRatio([...row, next], side) <= worstRatio(row, side)) {
      row.push(remaining.shift()!);
      continue;
    }
    bounds = placeRow(row, bounds, output);
    row = [];
  }
  if (row.length > 0) placeRow(row, bounds, output);
  return output;
}
