# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_MERGED / STORAGE_PROVIDER_ADAPTERS_MERGED / PROVIDER_OPERATION_STATE_MERGED / MYKV_PROVIDER_STATUS_MERGED / SITE_CONSUMER_BINDING_NEXT / CANONICAL_COSV_BOUND / RUNTIME_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Merged source PRs: `#196`, `#197`, `#198`, `#199`, `#200`, `#201`
Merged commits: `2a2a5273a684fedfaf10f6c4ea93d195d9d9ae6f`, `ea4da1e58e74c7f2690d26e82cb9c6a6e30aca03`, `4ee4232aec19f2bbc469bf712403185ab799ab0d`, `18067f09d16f8573797b837f5997297bc278e952`, `009bcc2d77f65b70c9aaa890b586addf3fc4dc2e`, `36bdcd26e64b081857fd3028da225060b15818e6`
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

The organization-level COSV handoff remains authoritative for the task vector. This repository handoff records the KV #1 / KV #2 / KV #n capability slice and its source/runtime boundary.

## Merged capability baseline

PR #196: isolated `KV #1`, `KV #2`, and `KV #n` roots; unique per-instance identity and installation receipt binding; provider-neutral storage metadata; four cumulative relationship tiers (`NOT_CONNECTED`, `CONNECTED`, `SYNCED`, `AI_INTERACTION`); default `NOT_CONNECTED`; non-authorizing governed transition requests.

PR #197: durable relationship state under `_System/Instances/Relationships/`, with state materialization gated by exact set/current-tier binding and admitted Interlock/InTr evidence.

PR #198: bounded MyKV multi-instance status projection carrying identity/storage/relationship metadata and pending relationship requests while private content, credentials, provider mutation authority, relationship mutation authority, and activation remain false.

PR #199: provider-neutral adapters for iCloud Drive, Google Drive, Microsoft OneDrive, and Dropbox representing deterministic `CONNECT`, `VERIFY`, `READ`, `WRITE`, `SYNC`, and `DISCONNECT` intents without authenticating providers or claiming provider execution.

PR #200: durable provider-operation state under `_System/Instances/Providers/`; admitted result materialization requires exact KV/request binding, Interlock receipt, InTr receipt, SKAP credential reference, provider-result evidence, and no raw credential material. Existing read-only direct-source connection assembly semantics remain unchanged.

PR #201: bounded MyKV projection now includes provider connection/verification status, last provider operation/result references, and pending provider request identifiers/operations. It explicitly excludes raw credentials, SKAP credential references, Interlock/InTr receipt references, provider tokens/session secrets, and private KV content. Provider and relationship mutation authority remain false.

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

`AI_INTERACTION` means the admitted participating KVs are treated as one logical corpus for an authorized AI interaction. It does not physically merge roots, erase provenance, collapse contradictions, or make AI canonical authority.

## Next machine-executable work

1. Bind the Site/MyKV consumer to the merged bounded instance/provider projection.
2. Add Site request surfaces that emit governed provider-operation and relationship-transition requests rather than invoking provider authority directly.
3. Extend the device-local DEVICE_KV query/return path to transport the bounded KV-set projection without exposing private content or credentials.
4. Preserve all existing direct-source and connection-health security boundaries; do not weaken those contracts to fit multi-provider operations.
5. After source validation, exercise a real KV #2 installation and provider path through admitted owner/runtime flow.

## Runtime activation still required for full capability

- materialize a real KV #2 without altering KV #1;
- resolve provider credentials through SKAP without copying credential material into ordinary KV or Site state;
- execute provider `CONNECT`, `VERIFY`, `READ`, `WRITE`, `SYNC`, and `DISCONNECT` through authentic Interlock/InTr admission and provider-result evidence;
- prove `NOT_CONNECTED -> CONNECTED -> SYNCED -> AI_INTERACTION` and downgrade transitions with authentic receipts;
- prove data movement, replication, unified logical AI corpus behavior, disconnect/recovery, reconnect/revalidation, and independent-root/provenance preservation;
- complete end-to-end iPhone/MyKV observation and readback proof.

## Manual work

No manual work is required for the current Site/source integration slice. A later owner-controlled provider authorization/install action is expected for real iCloud-backed KV #2 and live provider proof.
