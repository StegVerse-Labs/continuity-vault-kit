# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_IMPLEMENTATION_IN_PROGRESS / CANONICAL_COSV_BOUND / RUNTIME_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `kv-multi-instance-roots`
Pull request: `#196`
Updated: 2026-09-08
Authority effect: NONE
Activation effect: false

## Canonical task binding

This file does **not** create a new StegVerse task.

The KV #1 / KV #2 / KV #n multi-instance and relationship-tier work is a capability slice of the existing canonical KV connection/revalidation task:

```text
GOAL TASK ID: KV-CONNECTION-REVALIDATION-WORKER-001
COSV ID: 50000000102000
CANONICAL COSV HANDOFF: StegVerse-Labs/.github/KV_CONNECTION_REVALIDATION_COSV_MIRROR_HANDOFF.md
CANONICAL OWNER REPOSITORY: StegVerse-Labs/continuity-vault-kit
REPOSITORY HANDOFF: CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md
```

The organization-level COSV handoff remains authoritative for the task vector. This repository handoff records how PR #196 participates in that already-existing task.

## Capability slice

PR #196 extends the canonical KV connection/revalidation surface with provider-neutral multi-instance identity and explicit inter-instance relationship semantics:

```text
KV #1 -> storage medium A
KV #2 -> storage medium A or B
...
KV #n -> any admitted owner-controlled storage medium
```

Each instance has an isolated root, unique `instance_id`, shared or distinct `kv_set_id` as selected, storage-medium metadata, and its own installation receipt.

Instance ordinal is identity only. It does not grant priority, authority, freshness, trust, primary status, replication rank, or inheritance.

## Canonical relationship tiers

The inter-instance relationship has four cumulative capability tiers:

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

New instances begin `NOT_CONNECTED` even when they share the same owner, `kv_set_id`, or storage provider.

`AI_INTERACTION` means participating KVs are exposed to an admitted AI interaction as one logical corpus. Physical roots remain distinct, provenance remains instance-specific, contradictory records are not silently collapsed, and AI does not become canonical authority over the data.

## Relationship transition boundary

Source code may represent or request relationship changes before Interlock/InTr runtime activation, but source state must not claim that a governed transition occurred.

The source layer may therefore produce transition requests such as:

```text
NOT_CONNECTED -> CONNECTED
CONNECTED -> SYNCED
SYNCED -> AI_INTERACTION
AI_INTERACTION -> SYNCED
SYNCED -> CONNECTED
CONNECTED -> NOT_CONNECTED
```

Actual transition admission, data movement, replication, or unified AI exposure remains a governed runtime action and must be supported by authentic Interlock/InTr/provider/private-KV evidence.

## Current PR #196 artifacts

- `tools/init_vault.py`
- `runtime/kv_instance_relationships.py`
- relationship transition request/runtime source added on the branch
- `tests/test_multi_instance_vaults.py`
- `docs/KV_MULTI_INSTANCE_RELATIONSHIPS.md`
- `README.md`
- `tools/test_clean_room_user_kv.py`

## Acceptance conditions for this capability slice

Source completion requires:

1. KV #2 can be created beside KV #1 without overwrite.
2. KV #n can use any described owner-controlled storage medium without changing instance semantics.
3. every instance has isolated identity and receipt binding.
4. new instances default to `NOT_CONNECTED`.
5. the four relationship tiers are encoded as machine-readable cumulative capabilities.
6. transition requests are representable without claiming runtime authority.
7. tests prove same-provider coexistence and relationship semantics.
8. PR #196 is validated and merged.

Runtime completion remains separate and requires authentic evidence for admitted provider/inter-instance operations.

## Remaining work

- obtain repository validation for the current PR #196 head;
- remediate any failing checks;
- merge PR #196 when validation and review gates permit;
- materialize a real KV #2 instance without altering KV #1;
- later bind CONNECTED/SYNCED/AI_INTERACTION runtime transitions to actual Interlock/InTr execution and evidence;
- project the instance list and relationship tiers into MyKV add/remove/manage-drive UX.

## Manual work

None required for source implementation or task binding at this point. Any provider login, account authorization, or user-controlled cloud installation step remains outside source-only proof until explicitly performed through an admitted runtime/user flow.
