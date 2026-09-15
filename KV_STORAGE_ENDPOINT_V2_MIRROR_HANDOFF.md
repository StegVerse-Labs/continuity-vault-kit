# KV Storage Endpoint v2 Mirror Handoff

Status: SOURCE_IMPLEMENTED / README_RECONCILED / EXACT_HEAD_HOSTED_VALIDATION_PASS / PR_READY_FOR_REVIEW / RUNTIME_UNPROVEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Branch: `kv/storage-endpoint-v2`
Implementation PR: `#214`
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

Storage endpoint identity is distinct from access mechanism. The same Google Drive KnowledgeVault may be reached through an iOS File Provider adapter or a native Google Drive adapter without changing the KV instance identity or provenance.

## Implemented source

`runtime/kv_storage_provider_adapter.py` exposes additive `stegverse.kv.storage-endpoint-descriptor/v2` descriptors while retaining the existing `stegverse.kv.storage-provider-operation-request/v1` operation request shape.

The default registry includes `device-local` / DEVICE; iCloud Drive, Google Drive, OneDrive, and Dropbox / CLOUD; `nas` / NETWORK; and `removable-storage` / REMOVABLE. Each descriptor states locator kind, storage class, session requirement, credential requirement, and access-adapter class. Session and credential requirements are adapter-specific rather than globally cloud-assumed.

Existing operation verbs remain exactly:

```text
CONNECT VERIFY READ WRITE SYNC DISCONNECT
```

The request schema, canonical hash inputs, request ID derivation, governance state, no-runtime-effect sentinels, and authority/activation semantics remain v1-compatible. Device-local endpoints do not invent a SKAP credential requirement; cloud endpoints retain SKAP references; NAS/removable credential handling remains adapter-defined.

## Compatibility boundary

No existing Google Drive KV #2 request is regenerated, rehashed, renamed, or treated as executed by this change. Existing request `SITE-CLOUD-KV-4347408852127319cbda574f02e03edb` remains pending downstream provider/governance execution exactly as recorded by the canonical COSV handoff.

The storage-endpoint descriptor is additive metadata. It does not grant provider access, establish a session, move data, materialize a KV instance, mutate relationship state, synchronize state, or expose an AI corpus.

## README maintenance

Root `README.md` is reconciled on PR #214. It documents device/cloud/NAS/removable endpoint selection, storage-endpoint versus access-adapter separation, adapter-specific credential/session requirements, the unchanged six-operation vocabulary, and the non-authorizing runtime boundary.

## Validation evidence

Focused source validation is implemented in `tests/test_storage_endpoint_v2.py` using stdlib `unittest`, with `.github/workflows/kv-storage-endpoint-v2.yml` as a read-only hosted validation carrier.

README/handoff head `d51866a805c16912bda7bfc8176e9ac847d4f04a` produced all-green hosted evidence:

- KV Storage Endpoint v2 run `34941831677`: SUCCESS;
- Release integrity run `34941831612`: SUCCESS;
- Repository validation diagnostics run `34941831738`: SUCCESS;
- Security Baseline run `34941831533`: SUCCESS;
- KV Guardrails run `34941831561`: SUCCESS;
- KV Historical Corpus Import run `34941831715`: SUCCESS;
- KV Historical Provenance run `34941831633`: SUCCESS;
- Validate KV AI Persistence Classes run `34941831648`: SUCCESS.

The earlier Release integrity failure was remediated without weakening authority policy: adding the read-only validation workflow changed the repository workflow inventory from 52 to 53, so `tests/test_global_hosted_workflow_authority.py` was reconciled to the new exact count. All hosted-authority retirement checks themselves remained PASS.

This final handoff-only commit must also remain green before merge; no source or runtime semantics changed in it. Hosted CI proves source/control-plane conformance only and does not prove provider execution or KV materialization.

## Remaining sequence

1. Confirm checks on this final handoff-only head and keep PR #214 ready for review.
2. Do not merge provider-runtime claims into this source result; provider execution/materialization remains under the canonical runtime lane.
3. Site consumes the v2 storage-endpoint UI while preserving legacy v1 Google Drive KV #2 lineage.

## Manual work

None. Do not re-emit the existing Google Drive KV #2 request or authorize provider execution as part of this source change.
