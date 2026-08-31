# KnowledgeVault Persistent Session Reconstruction Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / RUNTIME_INTEGRATION_OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #142
Merged PR: #143\nMerge: d533ffdb7b39e5965a4d8d7b209bfd9363c96b1a
Updated: 2026-08-30
Authority effect: NONE
Runtime activation claimed: false

## Goal

Make conversation/client loss operationally unremarkable by preserving a bounded semantic work-state head in KnowledgeVault and reconstructing from that head plus independently verified live repository/runtime state.

The transcript is not the durable authority.

## Existing canonical recall substrate

This lane extends rather than replaces the existing conversation-continuity implementation:

- `schemas/conversation-event.schema.json`;
- `continuity/recall.py`;
- `docs/AUTOMATED_CONVERSATION_RECALL.md`;
- append-only `events.jsonl` semantics with previous-event chaining, content hashes, resulting-state hashes, fidelity classification, and archive-readiness evaluation.

The event chain remains the canonical continuity history. The new session head is a **derived, bounded semantic checkpoint** optimized for cold reconstruction. It must bind to the exact recall event-chain reference and verification root used to derive it.

A session head may be discarded and rebuilt from canonical events plus durable repo/runtime evidence. It is not a second canonical history.

## Canonical KV surface

```text
KnowledgeVault/
  _System/
    Continuity/
      Sessions/
        README.md
        <session_id>/
          head.json
          history/
          receipts/
```

Public source provides schemas, validation, and guidance only. User-specific session heads belong only in the connected private KnowledgeVault.

## Canonical state model

A session head may preserve only bounded semantic continuity:

- active goals and lifecycle standing;
- authoritative repositories and applicable *_MIRROR_HANDOFF.md paths;
- blockers and unresolved gates;
- machine-owned task references;
- durable evidence/receipt references;
- last verified repository/runtime observations;
- authorization and authority boundaries;
- next executable action;
- provenance and predecessor hash;
- canonical conversation-event chain reference and verification root.

A session head is not:

- a transcript dump;
- a credential store;
- an execution mandate;
- a replacement for canonical `events.jsonl`;
- a replacement for live repository/runtime verification;
- proof that a task is deployed, activated, observed, reconstructed, released, or complete.

## Reconstruction sequence

```text
authorized client
  -> DEVICE_KV_INTR
  -> KV-INTERLOCK-v1 REQUEST
  -> bounded session head
  -> verify head hash + predecessor/generation continuity
  -> verify bound recall-chain root / event source reference
  -> independently inspect live repository/runtime state
  -> reconcile stale claims
  -> continue highest-priority admitted work
  -> append canonical continuity events as applicable
  -> generate successor checkpoint candidate
  -> governed commit/readback
  -> receipt + new head
```

No direct COMMIT is introduced. Existing KV-INTERLOCK-v1 COMMIT_CANDIDATE semantics remain candidate-only.

## Fail-closed invariants

- unknown or malformed schema: reject;
- duplicate/stale generation: reject;
- prior-head hash mismatch: reject;
- missing or malformed canonical recall-chain binding: reject;
- secret-like field names anywhere in bounded state: reject;
- transcript/raw-message storage: reject;
- authority expansion: reject;
- canonical completion inferred solely from the stored head: prohibited;
- reconstructed state must set requires_live_verification=true;
- no credential/provider/execution authority is transferred.

## Activation gates

Source completion is not activation.

Persistent-session reconstruction reaches goal activation only after:

1. source schema/runtime/tests are merged;
2. the private KV Sessions surface is materialized;
3. authentic DEVICE_KV_INTR is observed;
4. a real canonical conversation-event chain exists for the active session/work scope;
5. a real bounded session head is derived from and bound to that chain;
6. the head is written through governed commit/readback;
7. a new client/session reads it through Interlock/InTr;
8. recall-chain integrity and live repo/runtime state are independently reconciled;
9. the exact prior task is resumed without duplicate side effects;
10. a successor head is committed and read back;
11. reconstruction receipts prove predecessor/successor and recall-root continuity.

## Current lifecycle

```text
IMPLEMENTED: IN_PROGRESS
VALIDATED: false
MERGED: false
DEPLOYED_PRIVATE_KV_SURFACE: false
ACTIVATED: false
OBSERVED: false
RECONSTRUCTED: false
RELEASED: false
COMPLETE: false
```

## Known external/runtime dependencies

- StegVerse-Labs/.github: authentic DEVICE_KV_INTR observation and WorkerCoordinator runtime evidence.
- StegVerse-Labs/StegOS: canonical Universal InTr backbone / device consumer.
- StegVerse-Labs/Site: eventual user-facing projection and recovery intent surface.
- StegVerse-Labs/master-records or canonical evidence custody owner where reconstruction evidence requires durable cross-runtime custody.

No second transport protocol, credential path, runtime owner, conversation-history authority, or hosted GitHub production authority may be introduced.


## Source merge evidence

```text
issue: #142 CLOSED_BY_MERGE
PR: #143 MERGED
merge: d533ffdb7b39e5965a4d8d7b209bfd9363c96b1a
validated head: a5d4c81c95eae981f50d26e66eec639977cd6abb
KV Guardrails: 33346462804 SUCCESS
KnowledgeVault Execution Recovery: 33346462753 SUCCESS
Repository validation diagnostics: 33346462754 SUCCESS
Security Baseline: 33346462776 SUCCESS
Release integrity: 33346462740 SUCCESS
```

The source layer is now merged and validated. The next implementation boundary is the KV-INTERLOCK-v1 adapter that reads/writes bounded session-head candidates without bypassing governed canonical writeback, followed by a StegOS device consumer over the existing `device-kv` Universal InTr connector.

No private-KV materialization, live DEVICE_KV_INTR delivery, cold-session reconstruction, activation, release, or completion is claimed.


## KV-INTERLOCK-v1 integration lane — issue #144

Issue #144 implements the next source seam:

- `runtime/persistent_session_interlock.py`;
- `tests/test_persistent_session_interlock.py`;
- `KV_PERSISTENT_SESSION_INTERLOCK_MIRROR_HANDOFF.md`.

The adapter is injected behind the existing `KVInterlockRuntime`; it does not create a second endpoint or transport. `REQUEST` may expose only the bounded reconstruction projection. `COMMIT_CANDIDATE` resolves an opaque payload reference, verifies exact successor continuity against the current head, and stages a candidate-only record with current/successor hashes and recall-root binding.

Canonical KV mutation remains separately governed and unimplemented in this lane. Private-KV deployment and live DEVICE_KV_INTR remain runtime gates.
