# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MATERIALIZATION_IN_PROGRESS / CANONICAL_COSV_BOUND / RUNTIME_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Current branch: `kv-relationship-state-materialization`
Merged source PR: `#196`
Merged source commit: `2a2a5273a684fedfaf10f6c4ea93d195d9d9ae6f`
Updated: 2026-09-08
Authority effect: NONE
Activation effect: false

## Canonical task binding

This file does **not** create a new StegVerse task.

```text
GOAL TASK ID: KV-CONNECTION-REVALIDATION-WORKER-001
COSV ID: 50000000102000
CANONICAL COSV HANDOFF: StegVerse-Labs/.github/KV_CONNECTION_REVALIDATION_COSV_MIRROR_HANDOFF.md
CANONICAL OWNER REPOSITORY: StegVerse-Labs/continuity-vault-kit
REPOSITORY HANDOFF: CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md
```

The organization-level COSV handoff remains authoritative for the task vector. This repository handoff records the multi-instance capability slice and its source/runtime boundary.

## Merged capability baseline

PR #196 is validated and merged. The repository now defines:

- isolated `KV #1`, `KV #2`, and `KV #n` roots;
- unique per-instance identity and installation receipt binding;
- provider-neutral storage metadata;
- ordinal identity with no implied authority hierarchy;
- four cumulative relationship tiers: `NOT_CONNECTED`, `CONNECTED`, `SYNCED`, `AI_INTERACTION`;
- default `NOT_CONNECTED` state for every new instance;
- non-authorizing governed transition requests.

## Relationship-state materialization slice

The current machine-executable source slice adds durable private-KV relationship state:

```text
_System/Instances/Relationships/
  relationship-state.json
  Requests/<request_id>.json
  Receipts/<request_id>.json
```

Source invariants:

1. initialization is fail-closed at `NOT_CONNECTED`;
2. persisting a transition request does not change current relationship state;
3. pending requests must remain `PENDING_INTERLOCK_INTR` with no claimed data movement, replication, AI exposure, authority, or activation;
4. a relationship state change may be materialized only from `ADMITTED` runtime evidence bound to the same request;
5. both Interlock and InTr receipt references are required before state materialization;
6. current-tier and `kv_set_id` bindings must match persisted state;
7. source materialization never creates credential/provider authority and retains `authority_effect: NONE` / `activation_effect: false`.

Current source artifacts include:

- `runtime/kv_relationship_state_store.py`
- `schemas/kv-relationship-state.schema.json`
- `tests/test_kv_relationship_state_store.py`
- existing `runtime/kv_instance_relationships.py`
- existing `schemas/kv-relationship-transition-request.schema.json`
- `README.md` relationship-state documentation

## Canonical relationship tiers

```text
NOT_CONNECTED
  inter-comms: false
  data movement: false
  replication: false
  unified AI corpus: false

CONNECTED
  inter-comms: true
  data movement: true
  replication: false
  unified AI corpus: false

SYNCED
  inter-comms: true
  data movement: true
  replication: true
  unified AI corpus: false

AI_INTERACTION
  inter-comms: true
  data movement: true
  replication: true
  unified AI corpus: true
```

`AI_INTERACTION` is a unified logical corpus for an admitted AI interaction; it does not physically merge roots, erase provenance, collapse contradictions, or make AI canonical authority.

## Remaining work

- validate and merge the relationship-state materialization source slice;
- materialize a real KV #2 instance without altering KV #1 when an admissible storage/user flow is available;
- bind actual CONNECTED/SYNCED/AI_INTERACTION transitions to authentic Interlock/InTr runtime evidence;
- project instance list, storage bindings, health, and four-tier relationship state into MyKV add/remove/manage-drive UX.

## Manual work

None required for this source slice. Provider login/account authorization or installation into user-controlled cloud storage remains a separate admitted user/runtime action.
