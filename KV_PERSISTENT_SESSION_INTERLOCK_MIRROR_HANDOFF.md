# KnowledgeVault Persistent Session Interlock Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / PRIVATE_KV_DEPLOYMENT_OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #144
Merged PR: #145\nMerge: 7088a1888e45654d92f889623c32e6264c4c8729
Updated: 2026-08-30
Authority effect: NONE
Runtime activation claimed: false

## Goal

Bind the merged persistent-session reconstruction model to the existing KV-INTERLOCK-v1 runtime without creating a second transport, direct canonical write authority, or transcript authority.

## Upstream source of truth

- `KV_PERSISTENT_SESSION_RECONSTRUCTION_MIRROR_HANDOFF.md`
- `runtime/persistent_session_reconstruction.py`
- `schemas/kv-persistent-session-head.schema.json`
- `runtime/kv_interlock_endpoint.py`
- `docs/KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md`
- `continuity/recall.py`
- `docs/AUTOMATED_CONVERSATION_RECALL.md`

## Read path

```text
DEVICE
  -> verified DEVICE->KV InTr envelope
  -> KVInterlockRuntime
  -> persistent-session policy adapter
  -> current private-KV session head
  -> validate head + conversation recall-chain binding
  -> bounded reconstruction projection
  -> receipt
  -> KV->DEVICE response
```

Only `REQUEST` with record class `persistent-session-head:<session_id>`, scope `session_head`, and `BOUNDED_CONTEXT` may receive the reconstruction projection.

## Candidate path

```text
COMMIT_CANDIDATE
  -> existing KVInterlockRuntime candidate boundary
  -> resolve opaque payload_ref
  -> validate successor head
  -> verify same session_id
  -> verify generation +1
  -> verify exact prior-head hash
  -> verify no timestamp rollback
  -> preserve conversation recall-chain binding
  -> stage candidate only
  -> no canonical KV mutation
```

The adapter must bind the staged candidate to current-head SHA-256, successor SHA-256, conversation-event verification root, request id, and source InTr receipt reference.

## Fail-closed invariants

- malformed/missing session identifier: reject;
- missing current head: reject;
- secret/transcript-bearing head: reject;
- stale/replayed/wrong-head successor: reject;
- recall-root drift within one direct successor: reject unless a future explicitly admitted event-chain advance contract exists;
- requested destination mismatch: reject;
- candidate store ambiguity: reject;
- canonical_state_changed must remain false;
- execution_authority remains NONE;
- credential_authority remains TV/TVC;
- authority_effect remains NONE.

## Non-claims

Source implementation does not prove private-KV deployment, DEVICE_KV_INTR runtime observation, live owner/session authority, canonical writeback, cold-session reconstruction, activation, or release.

## Current lifecycle

```text
IMPLEMENTED: IN_PROGRESS
VALIDATED: false
MERGED: false
DEPLOYED: false
ACTIVATED: false
OBSERVED: false
RECONSTRUCTED: false
RELEASED: false
COMPLETE: false
```


## Merge and validation evidence

```text
issue: #144 CLOSED_BY_MERGE
PR: #145 MERGED
merge: 7088a1888e45654d92f889623c32e6264c4c8729
validated head: fb02764af1e21b46ab76ef8f65d5bc738abe6c00
Repository validation diagnostics: 33346696652 SUCCESS
Security Baseline: 33346696651 SUCCESS
Release integrity: 33346696647 SUCCESS
KV Guardrails: 33346696656 SUCCESS
```

The KV-INTERLOCK-v1 source seam is now merged. Remaining work is runtime/private-KV materialization and authentic DEVICE_KV_INTR delivery, followed by governed canonical write/readback and cold-session reconstruction proof.
