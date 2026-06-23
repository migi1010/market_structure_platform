import { compactArray, safeArray, uniqueBy } from "./payloadSafety";

export function payloadSafetyContractTest() {
  const malformed = safeArray<string>(undefined);
  const objectPayload = safeArray<string>({ rows: ["NVDA"] });
  const compact = compactArray(["NVDA", null, undefined, "AMD"]);
  const unique = uniqueBy(
    [{ ticker: "NVDA" }, { ticker: "NVDA" }, { ticker: "AMD" }, { ticker: "" }],
    (row) => row.ticker,
  );

  return {
    undefinedSafe: malformed.length === 0,
    objectSafe: objectPayload.length === 0,
    compactSafe: compact.join(",") === "NVDA,AMD",
    uniqueSafe: unique.map((row) => row.ticker).join(",") === "NVDA,AMD",
    immutableCopy: safeArray(compact) !== compact,
  };
}
