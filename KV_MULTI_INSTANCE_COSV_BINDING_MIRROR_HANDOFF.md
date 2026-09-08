# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_IN_PROGRESS / CANONICAL_COSV_BOUND / RUNTIME_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Current branch: `kv-my-kv-instance-projection`
Merged source PRs: `#196`, `#197`
Merged commits: `2a2a5273a684fedfaf10f6c4ea93d195d9d9ae6f`, `ea4da1e58e74c7f2690d26e82cb9c6a6e30aca03`
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

PR #196 is validated and merged. The repository defines isolated `KV #1`, `KV #2`, and `KV #n` roots; unique per-instance identity and receipt binding; provider-neutral storage metadata; four cumulative relationship tiers (`NOT_CONNECTED`, `CONNECTED`, `SYNCED`, `AI_INTERACTION`); default `NOT_CONNECTED`; and non-authorizing governed transition requests.

PR #197 is validated and merged. Relationship state is durably represented under:

```text
_System/Instances/Relationships/
  relationship-state.json
  Requests/<request_id>.json
  Receipts/<request_id>.json
```

State transitions remain fail-closed and require matching `kv_set_id`, current-tier binding, `ADMITTED` evidence, and both Interlock and InTr receipt references before source materialization.

## Current MyKV projection slice

The current source slice gives MyKV a bounded multi-instance status surface without exposing private KV content or granting provider/runtime authority.

Current artifacts:

- `runtime/kv_my_kv_projection.py`
- `schemas/kv-my-kv-instance-projection.schema.json`
- `tests/test_kv_my_kv_projection.py`
- `README.md`

The projection exposes only:

- `instance_id`, `instance_number`, logical KV name, and `kv_set_id`;
- storage medium and explicitly non-secret locator metadata already present in the instance record;
- current relationship tier and relationship governance state;
- last admitted relationship request ID and pending relationship request IDs;
- request-surface capability flags for connect, disconnect, and relationship-tier-change requests.

The projection fixes these boundaries:

```text
private_content_included: false
credential_material_included: false
provider_mutation_authorized: false
relationship_mutation_authorized: false
authority_effect: NONE_STATUS_ONLY
activation_effect: false
```

MyKV may render these fields and initiate governed requests. The projection itself cannot connect/disconnect storage, change tiers, move data, replicate content, expose a unified AI corpus, authenticate a provider, or create execution/governance authority.

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

- validate and merge the MyKV projection source slice;
- coordinate the Site/MyKV consumer against this bounded projection contract without inventing a parallel provider/relationship authority;
- materialize a real KV #2 instance without altering KV #1 when an admissible storage/user flow is available;
- bind actual CONNECTED/SYNCED/AI_INTERACTION transitions to authentic Interlock/InTr runtime evidence;
- add real provider adapters and MyKV add/remove-drive request execution only when the corresponding admitted runtime paths exist.

## Manual work

None required for this source slice. Provider login/account authorization or installation into user-controlled cloud storage remains a separate admitted user/runtime action.
