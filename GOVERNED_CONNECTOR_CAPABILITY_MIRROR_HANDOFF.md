# Governed Connector Capability Mirror Handoff

Status: SOURCE_CONTRACT_PROPOSED / RUNTIME_EVIDENCE_NOT_CLAIMED
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `docs/governed-connector-capability-contract`
Updated: 2026-09-04
Authority effect: NONE
Activation effect: false
Credential authority: TV/TVC

## Purpose

Make connector visibility, connection, authorization, scope, identity, communication, integrity, freshness, and consequence admissibility explicit independent predicates rather than allowing provider integration or credential possession to collapse into an operational capability claim.

Canonical source contract: `GOVERNED_CONNECTOR_CAPABILITY_CONTRACT.md`.

This lane specializes the existing connection assembly described by `KV_CONNECTION_ASSEMBLY_SOURCE_MIRROR_HANDOFF.md` and preserves its provider-neutral reconstruction model.

## Core rule

```text
visible connector != operational capability
```

A connector is a discoverable route. Operational capability exists only for the exact current governed transition whose required predicates have independently passed.

## State model

```text
AVAILABLE
 -> CONNECTED
 -> AUTHORIZED
 -> SCOPED
 -> IDENTIFIED
 -> COMMUNICABLE
 -> VERIFIED
 -> CURRENTLY_AUTHORIZED
 -> CONSEQUENCE_ADMISSIBLE
```

Each state establishes only itself. No state silently proves the next.

`VERIFIED` is historical evidence unless freshness and current authority are re-established. Yesterday's proof must not silently become today's permission.

## Component boundaries

```text
KV
  durable non-secret intent/policy/resource identity/provenance/freshness/lineage

TV/TVC
  sole credential authority

SKAP Vault
  bounded credential/session custody and exercise boundary; does not manufacture authority

Interlock
  evaluates exact transition predicates and fails closed on missing/stale/indeterminate evidence

InTr
  carries the exact admitted governed transition; transport does not grant independent authority

external connector/provider
  factual source/transport endpoint; connector existence does not grant authority
```

## Current source work

Added:

- `GOVERNED_CONNECTOR_CAPABILITY_CONTRACT.md`
- `GOVERNED_CONNECTOR_CAPABILITY_MIRROR_HANDOFF.md`

The contract defines:

- a nine-state governed connector progression;
- explicit freshness/current-authority semantics;
- separate consequence admissibility;
- KV / SKAP / TV-TVC / Interlock / InTr responsibility boundaries;
- provider-neutral capability reconstruction at time of use;
- StegIndex projection semantics;
- non-authority invariants preventing connector/token possession from becoming capability or transition authority.

## Machine-execution boundary

No runtime implementation, connector activation, provider login, credential resolution, live retrieval, write capability, current authorization, consequence admission, or canonical transition is claimed by this documentation change.

The next machine-execution work should be performed only after reconciling this source contract against existing connection assembly schemas/runtime and active ownership. It should extend existing code rather than create a duplicate connector state machine.

Potential implementation destinations after reconciliation:

- `schemas/kv-connection-assembly.schema.json` — represent explicit epistemic/capability states or compatible references;
- `runtime/connection_assembly.py` — enforce non-transitive state advancement and freshness invalidation;
- `schemas/kv-connection-health-receipt.schema.json` — preserve exact state and evidence basis;
- `tests/test_connection_assembly.py` — add negatives proving `AVAILABLE` cannot imply `CONNECTED`, credential possession cannot imply authorization, prior verification cannot imply current authorization, and read authority cannot imply write/delete/send consequence authority;
- StegIndex consumer projection — expose candidate/discovered vs exact active capabilities without collapsing them.

## Cross-repository integration candidates

Once the source/runtime contract is accepted, verify pertinent semantics are propagated to:

- `StegVerse-Labs/StegOS` Universal Interlock/InTr documentation and implementations;
- `StegVerse-Labs/StegIndex` capability/predicate projection;
- `StegVerse-Labs/Site` My KV connector presentation so UI visibility never presents as operational authority;
- TV/TVC credential/session references without creating a new credential path;
- `StegVerse-Labs/Sit`, `GCAT-BCAT-Engine/Publisher`, `admissibility-wiki`, and `stegguardian-wiki` when the contract reaches canonical/release state.

## Remaining work

1. Reconcile against current `main` source schemas/runtime before mutation.
2. Determine whether the nine-state progression should be encoded directly in the existing assembly schema or referenced through a dedicated capability-state object.
3. Add machine-enforced negatives and freshness invalidation to the existing runtime lane.
4. Project the resulting exact capability state into StegIndex and Site/My KV.
5. Obtain authentic runtime evidence only through the live authority-owned path; do not infer it from source, merge, CI, or documentation.

## Current completion claim

Documentation/source contract: COMPLETE for this insight capture.
Machine implementation: NOT YET CLAIMED.
Runtime activation/evidence: NOT CLAIMED.
