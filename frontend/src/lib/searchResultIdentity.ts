import type { SearchResult } from "@/types/stock";

function compact(value: string | null | undefined): string {
  return value?.trim().replace(/\s+/g, " ").toUpperCase() ?? "";
}

export function searchResultIdentity(result: SearchResult): string {
  const action = result.workspaceAction ?? result;
  return [
    compact(result.group),
    compact(result.type),
    compact(result.symbol),
    compact(result.exchange),
    compact(action.actionType),
    compact(action.target_tab),
    compact(action.focusTarget),
    compact(action.contextPayload?.label),
  ].join("|");
}

export function uniqueSearchResults(results: SearchResult[] | readonly SearchResult[] | null | undefined): SearchResult[] {
  const seen = new Set<string>();
  return Array.isArray(results) ? results.filter((result) => {
    const key = searchResultIdentity(result);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }) : [];
}
