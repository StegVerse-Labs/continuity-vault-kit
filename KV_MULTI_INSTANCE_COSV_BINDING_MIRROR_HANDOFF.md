# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_MERGED / STORAGE_PROVIDER_ADAPTERS_MERGED / PROVIDER_OPERATION_STATE_MERGED / MYKV_PROVIDER_STATUS_MERGED / SITE_DEVICE_KV_TRANSPORT_MERGED / SITE_PREPUBLICATION_UI_MERGED / EXISTING_KV1_ADOPTION_SOURCE_IMPLEMENTED / PHYSICAL_KV1_ADOPTION_PENDING / PROVIDER_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Merged source PRs: `#196`, `#197`, `#198`, `#199`, `#200`, `#201`
Merged commits: `2a2a5273a684fedfaf10f6c4ea93d195d9d9ae6f`, `ea4da1e58e74c7f2690d26e82cb9c6a6e30aca03`, `4ee4232aec19f2bbc469bf712403185ab799ab0d`, `18067f09d16f8573797b837f5997297bc278e952`, `009bcc2d77f65b70c9aaa890b586addf3fc4dc2e`, `36bdcd26e64b081857fd3028da225060b15818e6`
Site continuation merged: PR `#1109` at `1c5396d186b2a8674f265733d91c542d472d20fd`; prepublication UI PR `#1110` at `5977b53c8ac43099b4d2cecf27cdc4c78e4c4882`
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

Site PR #1109 binds the bounded set/provider/relationship surfaces through a registered-Node generated-InTr/HB-derived-carrier DEVICE_KV client and a dedicated fail-closed resident receiver. The receiver can return a set projection only from an already-admitted `_System/my-kv-set-projection.json` and keeps provider/relationship requests pending with zero runtime effects.

Site PR #1110 adds an intentionally unlinked prepublication MyKV #1/#2/#n UI candidate over that merged transport. It does not infer missing KV #2/provider state and does not activate ordinary public MyKV navigation.

## Existing Google Drive KV #1 observation

Connected Drive observation on 2026-09-08 found the existing `KnowledgeVault` root and `_System/installation.receipt.json`, but no `_System/Instances` folder. Therefore the current physical KV predates the multi-instance identity layout. It must be adopted as KV #1 before an authentic multi-instance projection can exist; no identity or provider state may be invented from Site.

## Existing-KV adoption source — current branch

`tools/adopt_existing_kv_instance.py` provides a non-destructive migration/materialization path for an existing KnowledgeVault.

Plan mode:

- requires an existing vault root and schema-1.1 installation receipt;
- computes the exact receipt SHA-256;
- reports only the three generated paths;
- performs no mutation.

Apply mode additionally requires the caller-supplied expected installation-receipt SHA-256 to match exactly. It refuses to overwrite any existing:

```text
_System/Instances/instance.json
_System/Instances/adoption.receipt.json
_System/my-kv-set-projection.json
```

On exact match it creates canonical `stegverse.kv.instance/v1` identity metadata for the chosen instance number/set/storage medium, defaults relationship to `NOT_CONNECTED`, then calls the merged `runtime.kv_my_kv_projection.build_set_projection()` implementation and emits `stegverse.kv.my-kv-set-projection/v1`.

The adoption receipt records that private content and the original installation receipt were not modified, provider execution did not occur, credentials are absent, and provider/relationship mutation authority remain false. Any projection-generation failure removes the generated adoption artifacts rather than leaving a partial identity/projection state.

Validation is in `tools/test_adopt_existing_kv_instance.py` and `.github/workflows/kv-existing-instance-adoption.yml`.

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

`AI_INTERACTION` means admitted participating KVs are treated as one logical corpus for an authorized AI interaction. It does not physically merge roots, erase provenance, collapse contradictions, or make AI canonical authority.

## Next machine-executable work

1. Validate and merge the existing-KV adoption source.
2. Correct Site provider rendering to consume the canonical plural `instance.providers.items` / `pending_requests` projection emitted by PR #201 rather than a singular placeholder provider shape.
3. Perform owner-controlled adoption of the existing Google Drive KnowledgeVault as KV #1, exact-bound to its current installation receipt.
4. Admit the emitted `_System/my-kv-set-projection.json` through the bounded DEVICE_KV path and verify exact Site readback.
5. Integrate the validated MyKV #n candidate into public MyKV navigation/README without changing authority semantics.
6. Only then create/authenticate a real KV #2 provider path.

## Runtime activation still required for full capability

- physical adoption of the existing Google Drive vault as KV #1;
- exact DEVICE_KV admission/readback of the resulting bounded set projection;
- materialize a real KV #2 without altering KV #1;
- resolve provider credentials through SKAP without copying credential material into ordinary KV or Site state;
- execute provider `CONNECT`, `VERIFY`, `READ`, `WRITE`, `SYNC`, and `DISCONNECT` through authentic Interlock/InTr admission and provider-result evidence;
- prove `NOT_CONNECTED -> CONNECTED -> SYNCED -> AI_INTERACTION` and downgrade transitions with authentic receipts;
- prove data movement, replication, unified logical AI corpus behavior, disconnect/recovery, reconnect/revalidation, and independent-root/provenance preservation;
- complete end-to-end iPhone/MyKV observation and readback proof.

## Manual work

No user action yet. Do not manually create `_System/Instances`, do not manually author `_System/my-kv-set-projection.json`, and do not authorize KV #2 yet. After this source branch merges and the Site plural-provider consumer is corrected, the next manual action will be the exact owner-controlled KV #1 adoption procedure bound to the observed Google Drive installation receipt; that procedure must identify the exact files to create and preserve the existing installation receipt/private content unchanged.
