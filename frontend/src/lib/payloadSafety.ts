export function safeArray<T>(value: T[] | readonly T[] | null | undefined): T[];
export function safeArray<T = never>(value: unknown): T[];
export function safeArray<T>(value: T[] | readonly T[] | null | undefined | unknown): T[] {
  return Array.isArray(value) ? [...value] : [];
}

export function compactArray<T>(value: Array<T | null | undefined> | readonly (T | null | undefined)[] | null | undefined): T[] {
  return safeArray(value).filter((item): item is T => item !== null && item !== undefined);
}

export function uniqueBy<T>(value: T[] | readonly T[] | null | undefined, keyFor: (item: T) => string | null | undefined): T[] {
  const seen = new Set<string>();
  return safeArray(value).filter((item) => {
    const key = keyFor(item)?.trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
