# KnowledgeVault AI Memory Substrate

Goal: `SV-KV-AI-PERSISTENCE-001`

KnowledgeVault is the durable continuity substrate; the AI/model/runtime is replaceable. This module defines how a bounded, provenance-preserving subset of KV may be projected to an AI consumer without granting that model authority over the vault, and how an AI may return a memory write proposal without directly mutating KV.

## Personal Assistant / Auri path

```text
PERSONAL_KV
  -> bounded context request
  -> deterministic context selection
  -> context packet with per-entry hashes + provenance
  -> Interlock/InTr admission
  -> PERSONAL_ASSISTANT_AI (Auri / external model)
  -> optional memory write proposal
  -> Interlock/InTr admission
  -> target PERSONAL_KV materialization
```

The repository source implements the request, deterministic selection, packet construction, and non-authorizing write proposal. It does not perform provider authentication, resolve credentials, execute Interlock/InTr admission, send data to an AI provider, or write data into a private KV.

## Why this is a memory substrate rather than model memory

The persistent identity of remembered state is the KV object and its provenance, not the model session. A different AI can consume the same admitted packet later and reconstruct the same bounded continuity state. Model-provider memory may exist as a convenience layer, but it is not the canonical StegVerse continuity source.

The following remain false by contract:

```text
model_is_authority = false
provider_is_authority = false
context_transfers_authority = false
implicit_writeback_allowed = false
cross_authority_context_allowed = false
secret_material_allowed = false
```

## Context request

Schema: `schemas/kv-ai-memory-context-request.schema.json`

A request binds:

- one KV class and its matching authority domain;
- one AI role;
- an explicit allowlist of KV instance IDs;
- a bounded purpose and lexical query terms;
- maximum item and byte budgets;
- mandatory Interlock/InTr admission semantics;
- `authority_effect = NONE_CONTEXT_REQUEST_ONLY`.

The first concrete profile is:

```text
PERSONAL_KV / PERSON / PERSONAL_ASSISTANT_AI
```

The same machinery can later be instantiated for Organizational, StegVerse, and Machine KV without collapsing authority domains.

## Deterministic selection

Implementation: `runtime/kv_ai_memory_substrate.py`

Selection deliberately claims only lexical bounded retrieval. It does not pretend to provide semantic/vector retrieval.

An entry from an allowed source instance is eligible only when:

- `ai_context_allowed = true`;
- `secret_material = false`;
- KV class matches the request;
- authority domain matches the request;
- at least one query term matches title, content, or tags.

Eligible entries are deterministically ordered by priority, entry ID, and relative path. Byte and item budgets are enforced. Oversized entries are skipped rather than silently truncated.

If an AI-eligible entry from an allowed instance contains secret material or crosses the requested class/authority domain, selection fails closed.

## Context packet

Schema: `schemas/kv-ai-memory-context-packet.schema.json`

Every selected entry carries:

- source KV instance ID;
- relative path;
- content;
- SHA-256 of exact content bytes;
- tags and retention class;
- provenance reference.

The packet also binds the canonical request hash and selected-entry-set hash. Packet IDs are deterministic for the same request and selected content.

The packet fixes:

```text
secret_material_included = false
cross_authority_content_included = false
intr_admission_required = true
model_is_authority = false
context_transfers_authority = false
authority_effect = NONE_CONTEXT_ONLY
```

## Memory write proposal

Schema: `schemas/kv-ai-memory-write-proposal.schema.json`

The AI-side result is intentionally only a proposal. It binds the source context packet, target KV class/domain/instance, target relative path, content hash, and retention class.

It fixes:

```text
intr_admission_required = true
execution_authorized = false
model_is_authority = false
authority_effect = NONE_PROPOSAL_ONLY
```

A write proposal is not a KV write receipt. The target KV must independently admit and materialize it through the governed runtime before persistence can be claimed.

## Validation

- `scripts/validate_kv_ai_memory_substrate.py`
- `tests/test_kv_ai_memory_substrate.py`
- `.github/workflows/validate-kv-ai-persistence-classes.yml`

Tests cover deterministic retrieval, provenance retention, secret-material rejection, cross-authority rejection, role mismatch rejection, non-authorizing write proposals, and byte-budget behavior without truncation.

Hosted CI proves repository source behavior only. It cannot prove a live KV read, AI-provider delivery, live model consumption, InTr admission, or KV writeback.

## Runtime completion condition

Source completion and live activation are separate.

A live Auri/KV memory claim requires authentic evidence for the adjacent chain:

```text
KV readable object(s)
-> admitted context request
-> admitted context packet
-> AI delivery/consumption observation
-> optional write proposal
-> target-KV admission
-> KV write/readback receipt
```

No stage may be inferred from source code, CI, repository merge, provider availability, or a model response alone.
