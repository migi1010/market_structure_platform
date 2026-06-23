# Phase 12.11B Scout Proposal Provider Design

## Purpose

Phase 12.11B activates Theme Scout through a deterministic manual/offline
proposal boundary. A proposal is a frozen research hypothesis payload. It is
not evidence and cannot create or mutate Industrial Graph, Company,
Controller, Opportunity, Decision Packet, or recommendation records.

## Approved Flow

```text
active graph snapshot
  -> frozen evidence manifest
    -> reviewed proposal JSON
      -> strict validation
        -> deterministic Scout build
          -> transactional Scout activation
            -> downstream isolation verification
```

The local workflow is:

```text
export-evidence
validate-proposal
build
activate
verify-isolation
```

## Evidence Manifest

The manifest is scoped to exactly one active graph snapshot. It contains:

- schema version;
- graph build version and checksum;
- export watermark;
- canonical evidence bundle checksum;
- deterministic evidence rows attached to that graph version.

Each evidence row retains its persisted identity, source metadata, citation,
timestamp, content hash, attached relationship types, and endpoint context.
The Scout domain is derived deterministically from graph endpoint types using
the precedence:

```text
Constraint
Equipment
Material
Process
Technology
Company
Other
```

The manifest is read-only and does not become new graph evidence.

## Proposal Contract

`theme-scout-proposal-v1` is strict JSON. Unknown fields are rejected at every
level. The document contains:

- `schema_version`;
- `mode`, either `production` or `dry_run`;
- provider name, model, and prompt version;
- active graph build version;
- evidence bundle checksum;
- review metadata;
- structured candidates.

Production proposals require a non-empty reviewer, review timestamp, review
reason, and at least one candidate. Dry-run proposals may be empty.

Candidates:

- always start at `DISCOVERED`;
- reference manifest evidence IDs only;
- may define clusters, paths, influence hypotheses, bottleneck references, and
  generated candidate context;
- may not contain inline evidence, graph mutations, companies, downstream
  engine outputs, recommendations, targets, or allocations.

## Providers

`ManualThemeScoutProposalProvider` accepts an already parsed immutable proposal.

`OfflineFileThemeScoutProposalProvider` freezes the proposal file bytes,
computes the file checksum, parses once, and returns the same immutable
proposal for the build. It performs no network or provider calls.

No live LLM adapter is implemented.

## Activation

Validation occurs before any Scout write. Production activation additionally
requires:

- `mode=production`;
- reviewed non-empty proposal;
- matching active graph version;
- matching evidence bundle checksum;
- every candidate in `DISCOVERED`;
- all evidence references present and cited.

Scout staging and activation retain the existing transactional behavior.
Before activation, the CLI records deterministic counts and checksums for
Graph, Controller, Opportunity, and Decision Packet tables. It verifies that
the same fingerprints remain after activation. A mismatch fails the command
and rolls the Scout activation back to the prior active Scout snapshot.

## CLI

The internal module is invoked from `backend`:

```powershell
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli export-evidence --output <path>
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli validate-proposal --proposal <path> --manifest <path>
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli build --proposal <path> --manifest <path>
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli dry-run --proposal <path> --manifest <path>
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli activate --proposal <path> --manifest <path>
.\.venv\Scripts\python.exe -m theme_intelligence.industrial_graph.theme_scout_cli verify-isolation
```

`build` validates and prints the deterministic build audit without persistence.
`dry-run` is an alias with explicit dry-run policy enforcement. `activate`
requires production review metadata and a non-empty candidate set.

## UI

The existing read-only Scout workspace may display:

- provider name and model;
- prompt version;
- evidence bundle checksum prefix;
- proposal checksum prefix.

It does not expose activation controls.

## Testing

Tests cover:

- strict JSON and unsupported-field rejection;
- inline evidence rejection;
- dry-run empty proposal acceptance;
- first-production empty proposal rejection;
- active-graph manifest scoping;
- deterministic domain derivation and manifest checksum;
- unknown evidence and empty citation rejection;
- checksum and graph-version mismatch rejection;
- manual and offline provider determinism;
- CLI dry-run/build/activation behavior;
- no downstream table mutations;
- activation rollback after isolation failure;
- existing Scout snapshot and read API behavior.

## Non-Goals

- live LLM calls;
- startup activation;
- public mutation APIs;
- graph or company writes;
- Controller, Opportunity, or Decision Packet creation;
- recommendations, targets, signals, or portfolio behavior.

