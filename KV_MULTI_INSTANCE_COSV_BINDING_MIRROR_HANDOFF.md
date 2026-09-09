# KV Multi-Instance COSV Binding Mirror Handoff

Status: SOURCE_MULTI_INSTANCE_MERGED / RELATIONSHIP_STATE_MERGED / MYKV_PROJECTION_MERGED / STORAGE_PROVIDER_ADAPTERS_MERGED / PROVIDER_OPERATION_STATE_MERGED / MYKV_PROVIDER_STATUS_MERGED / DEVICE_LOCAL_KV_OWNER_OBSERVED / GOOGLE_DRIVE_EXISTING_PEER_EXACT_EVIDENCE_RECOVERED / GOOGLE_DRIVE_KV2_OWNER_REQUEST_INGRESS_OBSERVED / KV2_ADOPTION_PROVIDER_BINDING_IMPLEMENTED / HOSTED_VALIDATION_PENDING / GOOGLE_DRIVE_CONNECT_VERIFY_EXECUTION_PENDING / KV2_MATERIALIZATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `kv2-adoption-provider-binding-20260908`
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

- PR #196: KV #1/#2/#n identity roots and four relationship tiers.
- PR #197: durable governed relationship state.
- PR #198: bounded MyKV multi-instance projection.
- PR #199: provider-neutral iCloud Drive / Google Drive / OneDrive / Dropbox request adapters.
- PR #200: durable provider-operation state gated by admitted Interlock/InTr evidence, SKAP credential reference, and provider-result evidence.
- PR #201: plural provider status projection.
- PR #203: non-destructive existing-KV adoption source.
- PR #204: exact physical Google Drive adoption evidence.
- Site PRs #1115/#1116: first-class device-local resident KV plus cloud-peer request surfaces.
- Site PR #1122: prepared Google Drive KV #2 resident adoption transport.
- Site PR #1124: legacy current-device Node compatibility repair.
- Site PR #1127: authentic owner retry reconciliation.
- `.github` PR #1209: canonical COSV reconciliation of authentic resident ingress.

## Authentic current-device resident KV

Owner-visible deployed Site evidence:

```text
resident instance: KV #1
instance_id: kvi_0d5d4cfd531db51bbcf7fdfc0311f5dc
kv_set_id: personal
storage: device-local-browser-indexeddb
relationship: NOT_CONNECTED
exact_readback: true
durability: BEST_EFFORT_BROWSER_ORIGIN
```

## Existing Google Drive cloud KV evidence

```text
existing cloud instance_id: kvi_a31335d2cc3745fa987b635432cfed2c
historical cloud ordinal: KV #1
requested peer ordinal: KV #2
relationship: NOT_CONNECTED
installation receipt: sha256:f00378cd1f68e08a39c837f2a80e7e105e822a321c0eea17a91318b4b6e5ea19
instance record: sha256:8bf5ba7d911a52506a582f064315c9831a84c0c5fbb6ec7a031c325a79af090a
adoption receipt: sha256:64a3af27be0bd6ae36b05b35e52894581413fff048cea237d370d0ec6248b552
set projection: sha256:187ab43f0bb09d88da154af26d57e1bfe7199fd90affd2dd81af5532f0e34cf4
```

The cloud instance identity and private content must be preserved; KV #2 is a set-membership ordinal binding, not a destructive cloud identity rewrite.

## Authentic Google Drive KV #2 adoption request ingress

The current iPhone emitted:

```text
request_id: SITE-CLOUD-KV-4347408852127319cbda574f02e03edb
governance_state: PENDING_INTERLOCK_INTR
resident_ingress_observed: true
requested: KV #2
instance_materialized: false
provider_operation_authorized: false
```

No provider execution, relationship mutation, data movement, replication, AI-corpus exposure, credential material, authority effect, or activation is inferred from that ingress result.

## Current source slice — adoption to provider execution binding

`runtime/cloud_peer_adoption_provider_binding.py` converts the authentic resident adoption request into canonical Google Drive `CONNECT` and `VERIFY` requests through the existing storage-provider adapter. It requires a private runtime storage locator but does not publish that locator or raw credential material.

The resulting provider requests remain:

```text
governance_state=PENDING_INTERLOCK_INTR
skap_credential_ref_required=true
provider_operation_executed=false
data_moved=false
replication_started=false
authority_effect=NONE
activation_effect=false
```

Materialization readiness remains false until both Google Drive `CONNECT` and `VERIFY` receipts prove all of:

```text
governance_state=ADMITTED
provider_operation_executed=true
interlock_receipt_ref=<non-empty>
intr_receipt_ref=<non-empty>
skap_credential_ref=<non-empty reference only>
provider_result_ref=<non-empty>
credential_material_present=false
authority_effect=NONE
```

When those two admitted results exist, readiness may become true using:

```text
materialization_mode=SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY
requested_instance_number=2
cloud_identity_rewrite_required=false
private_content_rewrite_authorized=false
relationship_tier_after_materialization=NOT_CONNECTED
```

The readiness function does not itself materialize KV #2.

## Canonical relationship tiers

```text
NOT_CONNECTED  -> no inter-comms, movement, replication, or unified AI corpus
CONNECTED      -> inter-comms + admitted movement; no replication/unified AI corpus
SYNCED         -> inter-comms + movement + replication; no unified AI corpus
AI_INTERACTION -> inter-comms + movement + replication + admitted logical unified AI corpus
```

## Remaining sequence

1. Run exact-head validation for this adoption→provider binding slice and repair failures.
2. Merge source only after all required checks pass.
3. Resolve the Google Drive credential through SKAP as a reference; never copy credential material into Site/ordinary KV/evidence.
4. Submit canonical Google Drive `CONNECT` through authentic Interlock/InTr and retain its receipts/provider result.
5. Submit canonical Google Drive `VERIFY` through authentic Interlock/InTr and retain its receipts/provider result.
6. Apply those already-admitted results to the provider-operation store.
7. Re-evaluate materialization readiness; only if true, materialize the existing cloud instance into the `personal` set as KV #2 without rewriting its cloud identity/private content.
8. Refresh MyKV projection/readback and then test CONNECTED/SYNCED/AI_INTERACTION progression and recovery separately.
9. Add iCloud/new cloud KV #3/#n only after the existing Google Drive peer path is proven.

## Manual work

None required while this source slice validates. Do not tap the adoption button again, authorize Google Drive, clear Safari data, reinstall the resident KV, or create KV #3 yet.
