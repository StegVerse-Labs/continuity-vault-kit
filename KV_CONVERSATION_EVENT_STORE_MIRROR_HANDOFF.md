# KnowledgeVault Conversation Event Store Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / PRIVATE_KV_DEPLOYMENT_OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #146
Merged PR: #147
Merge: adab132653febd872158f28a6774d32d150ac41e
Updated: 2026-08-30
Authority effect: NONE
Runtime activation claimed: false

## Goal

Materialize the canonical append-only conversation continuity event chain used by persistent-session reconstruction inside the private KnowledgeVault without creating a second history model.

## Canonical upstream

- `schemas/conversation-event.schema.json`
- `continuity/recall.py`
- `docs/AUTOMATED_CONVERSATION_RECALL.md`
- `KV_PERSISTENT_SESSION_RECONSTRUCTION_MIRROR_HANDOFF.md`

The existing event model and `continuity.recall.validate_chain` semantics remain canonical.

## Canonical private-KV path

```text
KnowledgeVault/
  _System/
    Continuity/
      Events/
        README.md
        events.jsonl
```

Public source contains only runtime, tests, and guidance. Real event contents remain private KV state.

## Store contract

The event store:

1. reads the exact current JSONL bytes from injected private storage;
2. parses non-empty lines as canonical event objects;
3. validates the complete existing chain;
4. rejects secret/transcript-bearing content;
5. binds the new event's `previous_event_hash` to the exact canonical hash of the current terminal event;
6. validates the candidate full chain before persistence;
7. writes the complete successor JSONL through an injected compare-and-swap writer bound to the exact prior verification root;
8. reads the committed bytes back;
9. revalidates the complete chain and exact terminal event;
10. returns the new event hash, verification root, event count, and opaque storage reference.

The store does not infer authority from storage access and cannot execute a downstream task.

## Fail-closed invariants

- duplicate event id: reject;
- malformed JSONL: reject;
- broken previous-event hash: reject;
- timestamp rollback: reject;
- content hash mismatch: reject;
- recoverable-fidelity claim without retained content: reject;
- password/token/cookie/private-key/seed/mnemonic/recovery material fields: reject;
- transcript/raw-message/conversation-dump fields: reject;
- ambiguous compare-and-swap result: reject;
- write without exact readback: reject;
- authority transfer: none;
- execution authority: none;
- credential authority: TV/TVC.

## Relationship to persistent-session heads

The event chain is canonical continuity history. A persistent-session head is a disposable bounded checkpoint derived from that history plus live repository/runtime evidence.

The head binds to:

```text
conversation_event_chain_ref=_System/Continuity/Events/events.jsonl
conversation_event_verification_root=<terminal event hash>
```

## Activation boundary

Source implementation, CI, merge, or private folder materialization does not prove DEVICE_KV_INTR, a cross-session read, cold reconstruction, duplicate-safe task continuation, governed session-head writeback, or activation.

## Current lifecycle

```text
IMPLEMENTED: true
VALIDATED: true
MERGED: true
DEPLOYED_PRIVATE_KV_SURFACE: false
EVENT_CHAIN_OBSERVED: false
ACTIVATED: false
RECONSTRUCTED: false
RELEASED: false
COMPLETE: false
```


## Merge and validation evidence

```text
issue: #146 CLOSED_BY_MERGE
PR: #147 MERGED
merge: adab132653febd872158f28a6774d32d150ac41e
validated head: 2d58d9343030c66fff706a434f77b03a2ba17b43
Repository validation diagnostics: 33347382483 SUCCESS
Security Baseline: 33347382436 SUCCESS
Release integrity: 33347382437 SUCCESS
KV Guardrails: 33347382451 SUCCESS
```

The canonical event-store source is merged and validated. Remaining work is private-KV Events materialization, first authentic project event-chain append/readback, persistent-session head derivation from that root, and the still-separate DEVICE_KV_INTR/cold-reconstruction runtime gates.
