# KnowledgeVault Persistent Session Reconstruction Mirror Handoff

Status: SOURCE_IMPLEMENTATION_IN_PROGRESS
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #142
Branch: feature/kv-persistent-session-reconstruction-142
Updated: 2026-08-30
Authority effect: NONE
Runtime activation claimed: false

## Goal

Make conversation/client loss operationally unremarkable by preserving a bounded semantic work-state head in KnowledgeVault and reconstructing from that head plus independently verified live repository/runtime state.

The transcript is not the durable authority.

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
- provenance and predecessor hash.

A session head is not:

- a transcript dump;
- a credential store;
- an execution mandate;
- a replacement for live repository/runtime verification;
- proof that a task is deployed, activated, observed, reconstructed, released, or complete.

## Reconstruction sequence

```text
authorized client
  -> DEVICE_KV_INTR
  -> KV-INTERLOCK-v1 REQUEST
  -> bounded session head
  -> verify head hash + predecessor/generation continuity
  -> independently inspect live repository/runtime state
  -> reconcile stale claims
  -> continue highest-priority admitted work
  -> generate successor candidate
  -> governed commit/readback
  -> receipt + new head
```

No direct COMMIT is introduced. Existing KV-INTERLOCK-v1 COMMIT_CANDIDATE semantics remain candidate-only.

## Fail-closed invariants

- unknown or malformed schema: reject;
- duplicate/stale generation: reject;
- prior-head hash mismatch: reject;
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
4. a real bounded session head is written through governed commit/readback;
5. a new client/session reads it through Interlock/InTr;
6. live repo/runtime state is independently reconciled;
7. the exact prior task is resumed without duplicate side effects;
8. a successor head is committed and read back;
9. reconstruction receipts prove predecessor/successor continuity.

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

No second transport protocol, credential path, runtime owner, or hosted GitHub production authority may be introduced.
