# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_MERGED / STORAGE_PROVIDER_ADAPTERS_MERGED / PROVIDER_OPERATION_STATE_MERGED / MYKV_PROVIDER_STATUS_MERGED / SITE_DEVICE_KV_TRANSPORT_MERGED / SITE_PREPUBLICATION_UI_MERGED / SITE_PROVIDER_SHAPE_MERGED / EXISTING_KV1_ADOPTION_SOURCE_MERGED / PHYSICAL_KV1_ADOPTION_VERIFIED / SITE_PROJECTION_ADMISSION_MERGED_DEPLOYED / CURRENT_DEVICE_READBACK_PENDING / KV2_PROVIDER_ACTIVATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Updated: 2026-09-08
Authority effect: NONE
Activation effect: false

## Canonical task binding

```text
GOAL TASK ID: KV-CONNECTION-REVALIDATION-WORKER-001
COSV ID: 50000000102000
CANONICAL COSV HANDOFF: StegVerse-Labs/.github/KV_CONNECTION_REVALIDATION_COSV_MIRROR_HANDOFF.md
CANONICAL OWNER REPOSITORY: StegVerse-Labs/continuity-vault-kit
REPOSITORY HANDOFF: CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md
```

## Merged capability baseline

- PR #196: isolated `KV #1`, `KV #2`, and `KV #n` identity roots and four relationship tiers.
- PR #197: durable governed relationship state.
- PR #198: bounded multi-instance MyKV projection.
- PR #199: provider-neutral iCloud Drive / Google Drive / OneDrive / Dropbox intent adapters.
- PR #200: durable provider-operation state requiring admitted Interlock/InTr + SKAP reference + provider-result evidence.
- PR #201: bounded plural provider status projection with private content/credentials/governance receipt references excluded.
- Site PR #1109: registered-Node/HB-derived-carrier resident DEVICE_KV transport.
- Site PR #1110: unlinked prepublication MyKV #1/#2/#n UI candidate.
- Site PR #1113: canonical plural `instance.providers.items` / `pending_requests` validation and rendering.
- continuity-vault-kit PR #203: non-destructive existing-KV adoption source, merged at `4f2f47120ab162273abba6eae3e2155a46db2c16`.
- Site PR #1114: owner-mediated exact-byte KV-set projection admission into resident DEVICE_KV, merged at `f928ca203a89566c6862c7b93b9f204ab36ba6c6`; push validation and Pages deployment succeeded.

## Authentic physical Google Drive KV #1

The existing owner-controlled Google Drive KnowledgeVault was observed with a schema-1.1 installation receipt but no pre-existing multi-instance identity/projection records. The adoption preflight therefore satisfied the no-overwrite predicates.

The original installation receipt was bound before mutation at:

```text
sha256:f00378cd1f68e08a39c837f2a80e7e105e822a321c0eea17a91318b4b6e5ea19
```

The adoption bundle was written in completion-safe order and raw-read back exactly:

```text
_System/Instances/instance.json
sha256:8bf5ba7d911a52506a582f064315c9831a84c0c5fbb6ec7a031c325a79af090a

_System/my-kv-set-projection.json
sha256:187ab43f0bb09d88da154af26d57e1bfe7199fd90affd2dd81af5532f0e34cf4

_System/Instances/adoption.receipt.json
sha256:64a3af27be0bd6ae36b05b35e52894581413fff048cea237d370d0ec6248b552
```

The original installation receipt was raw-read again after all writes and retained the identical 3,179-byte SHA-256. Private source does not need to be copied into this repository; only non-secret evidence hashes are retained here.

The physical vault is now a single-member `personal` set representing authentic KV #1. Its relationship is `NOT_CONNECTED`; provider status is unobserved/empty; provider and relationship mutation authority are false; no provider operation executed; no data moved or replicated; no AI corpus was exposed; activation remains false.

## Resident DEVICE_KV admission

Physical cloud materialization does not prove the current browser's resident DEVICE_KV contains the projection. Site PR #1114 adds a separate admission path that requires the owner to select the canonical raw `_System/my-kv-set-projection.json` file. The raw bytes are canonical-schema validated, SHA-256 bound, transported through the registered Node + generated InTr + HB-derived carrier, written only to the resident `_System/my-kv-set-projection.json` key, and read back exactly before success can be reported.

The status projection is replaceable so later authentic KV #2/#n state can refresh it, but every replacement remains owner-mediated, validated, exact-byte-bound, path-restricted, and non-authorizing. Provider execution, relationship mutation, credential authority, data movement, replication, AI-corpus exposure, and activation remain false.

## Canonical relationship tiers

```text
NOT_CONNECTED  -> no inter-comms, movement, replication, or unified AI corpus
CONNECTED      -> inter-comms + admitted movement; no replication/unified AI corpus
SYNCED         -> inter-comms + movement + replication; no unified AI corpus
AI_INTERACTION -> inter-comms + movement + replication + admitted logical unified AI corpus
```

`AI_INTERACTION` does not physically merge roots, erase provenance, collapse contradictions, or make AI canonical authority.

## Remaining sequence

1. On the current iPhone, admit the already-existing physical `_System/my-kv-set-projection.json` through the deployed Site MyKV instances surface.
2. Require `PROJECTION_ADMITTED`, exact source hash binding, `exact_readback_verified=true`, then resident `MY_KV_INSTANCE_SET_PROJECTION` readback showing one authentic KV #1 instance.
3. Integrate the validated instances surface into ordinary MyKV navigation and README/public capability semantics.
4. Materialize real KV #2 without altering KV #1.
5. Resolve provider authorization through SKAP without copying credential material into ordinary KV/Site state.
6. Prove provider `CONNECT`, `VERIFY`, `READ`, `WRITE`, `SYNC`, `DISCONNECT` with admitted provider-result evidence.
7. Prove relationship upgrades/downgrades across `NOT_CONNECTED`, `CONNECTED`, `SYNCED`, and `AI_INTERACTION`, plus disconnect/recovery/reconnect/revalidation and independent-root/provenance preservation.
8. Complete end-to-end current-iPhone readback evidence before claiming full capability activation.

## Manual work

The next action is now owner/current-device work, not source development: on the current iPhone open the deployed MyKV instances surface and select the existing canonical `KnowledgeVault/_System/my-kv-set-projection.json` from Files/Google Drive. Do not edit the file and do not enter provider credentials. Return the page's projection-admission/readback result before KV #2 authorization begins.
