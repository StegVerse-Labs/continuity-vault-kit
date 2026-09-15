# KV Storage Endpoint v2 Mirror Handoff

Status: SOURCE_IMPLEMENTED / VALIDATION_PENDING / RUNTIME_UNPROVEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `kv/storage-endpoint-v2`
Updated: 2026-09-15
Goal Task ID: `KV-CONNECTION-REVALIDATION-WORKER-001`
COSV ID: `50000000102000`
Canonical COSV handoff: `StegVerse-Labs/.github/KV_CONNECTION_REVALIDATION_COSV_MIRROR_HANDOFF.md`
Authority effect: `NONE`
Activation effect: `false`

## Purpose

Generalize the already-provider-neutral KnowledgeVault storage model from a cloud-only default adapter registry into one storage-endpoint abstraction without changing KV identity, provenance, relationship tiers, Interlock/InTr governance, or the exact existing Google Drive KV #2 request lineage.

Canonical model:

```text
KV instance -> storage endpoint -> access adapter -> location
```

Storage endpoint identity is distinct from access mechanism. For example, the same Google Drive KnowledgeVault may be reached through an iOS File Provider adapter or a native Google Drive adapter without changing the KV instance identity or provenance.

## Implemented source

`runtime/kv_storage_provider_adapter.py` now exposes `stegverse.kv.storage-endpoint-descriptor/v2` descriptors while retaining the existing `stegverse.kv.storage-provider-operation-request/v1` operation request shape.

The default registry now includes:

- `device-local` / DEVICE;
- `icloud-drive`, `google-drive`, `onedrive`, `dropbox` / CLOUD;
- `nas` / NETWORK;
- `removable-storage` / REMOVABLE.

Each descriptor states locator kind, storage class, session requirement, credential requirement, and access-adapter class. Session and credential requirements are adapter-specific rather than globally cloud-assumed.

Existing operation verbs remain exactly:

```text
CONNECT VERIFY READ WRITE SYNC DISCONNECT
```

The request schema, canonical hash inputs, request ID derivation, governance state, no-runtime-effect sentinels, and authority/activation semantics remain v1-compatible. Device-local endpoints explicitly do not invent a SKAP credential requirement; cloud endpoints continue to require SKAP references; NAS/removable credential handling remains adapter-defined.

## Compatibility boundary

No existing Google Drive KV #2 request is regenerated, rehashed, renamed, or treated as executed by this change. Existing request `SITE-CLOUD-KV-4347408852127319cbda574f02e03edb` remains pending downstream provider/governance execution exactly as recorded by the canonical COSV handoff.

The storage-endpoint descriptor is additive metadata. It does not grant provider access, establish a session, move data, materialize a KV instance, mutate relationship state, synchronize state, or expose an AI corpus.

## Validation

Added `tests/test_storage_endpoint_v2.py` covering:

- device/cloud/network/removable registry coverage;
- adapter-specific session and credential requirements;
- preservation of legacy v1 cloud operation request semantics;
- device-local request behavior without fabricated provider credentials;
- no authority or activation effect.

Hosted CI evidence remains pending until the implementation PR runs.

## README maintenance

The existing root README already states that `--storage-medium` may identify any owner-controlled storage medium including local/removable media, and that KV identity is provider-neutral. The implementation PR must update the storage-adapter paragraph before merge to reflect the expanded default endpoint registry and adapter-specific credential/session requirements. Do not merge without that README reconciliation.

## Remaining sequence

1. Run repository validation on the exact implementation head.
2. Update the root README storage-adapter paragraph on the PR branch without weakening existing authority boundaries.
3. Merge only after required checks pass.
4. Site consumer must use its v2 storage-endpoint UI while preserving legacy v1 Google Drive KV #2 lineage.
5. Do not promote source/CI success to provider runtime evidence.

## Manual work

None. Do not re-emit the existing Google Drive KV #2 request or authorize provider execution as part of this source change.
