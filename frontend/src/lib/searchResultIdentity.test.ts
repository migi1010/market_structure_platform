import { searchResultIdentity, uniqueSearchResults } from "./searchResultIdentity";
import type { SearchResult } from "@/types/stock";

function command(symbol: string, label: string): SearchResult {
  return {
    symbol,
    name: label,
    label,
    exchange: "Command",
    type: "Command",
    group: "Commands",
    target_tab: "theme-supply-chain",
    actionType: "open_module",
    focusTarget: "theme-supply-chain",
    contextPayload: { label },
  };
}

export function searchResultIdentityContractTest() {
  const first = command("OPEN-SUPPLY-CHAIN", "Open Supply Chain");
  const duplicate = { ...first };
  const distinct = command("OPEN-GLASS-SUBSTRATE", "Open Glass Substrate");

  return {
    duplicateStable: searchResultIdentity(first) === searchResultIdentity(duplicate),
    distinctCommands: searchResultIdentity(first) !== searchResultIdentity(distinct),
    duplicatesRemoved: uniqueSearchResults([first, duplicate, distinct]).length === 2,
  };
}
