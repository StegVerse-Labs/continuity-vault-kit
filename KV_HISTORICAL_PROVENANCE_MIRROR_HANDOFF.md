# KV Historical Provenance Mirror Handoff

Status: ACTIVE_IMPLEMENTATION / SOURCE_ONLY  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#188`  
Branch: `feature/kv-historical-provenance-188`  
Updated: 2026-09-05  
Authority effect: NONE  
Activation effect: false

## Purpose

Define a provider-neutral historical-evidence ingestion capability for KnowledgeVault/MyKV so legacy StegVerse artifacts can remain in their original owner-controlled storage while KV preserves exact-byte identity, source provenance, chronology, copy/mirror lineage, interpretation lineage, contradiction state, and import receipts.

This task does not migrate, upgrade, or mutate the owner's existing iCloud or Google Drive vaults.

## Canonical dependency reuse

This work consumes rather than replaces:

- `docs/CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`;
- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`;
- `KV_PROVIDER_SURFACE_CAPABILITIES_MIRROR_HANDOFF.md`;
- `LEGACY_KV_UPGRADE_MIRROR_HANDOFF.md` only as a collision boundary;
- SKAP credential-custody semantics;
- existing KV receipt/provenance conventions.

No parallel provider-ingress authority is introduced.

## Machine preflight — 2026-09-05

Preflight state: `PASS_FOR_BOUNDED_SOURCE_IMPLEMENTATION`.

Resolved state before functional mutation:

1. Repository-local canonical handoff is `docs/CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`.
2. Canonical ecosystem task coordination separates work intent from WorkerCoordinator execution authority and Master Records observed-reality authority.
3. `master-records/core-lite/MASTER_RECORDS_MIRROR_HANDOFF.md` remains the current Master Records repository-wide handoff; this task does not mint Master Records custody.
4. Existing claim `CVK-LEGACY-KV-UPGRADE-174` owns migration/upgrade paths for the older iCloud KV. Issue #188 uses distinct historical-provenance paths and must not modify either existing vault.
5. `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md` already defines direct-source provenance and SKAP-bounded provider access. Historical provenance must reuse that ingress model.
6. `KV_PROVIDER_SURFACE_CAPABILITIES_MIRROR_HANDOFF.md` already owns generic provider/device capability facts. This task must not duplicate that registry.

### README completeness predicate

README change required: **YES**.

Reason: issue #188 materially expands documented KnowledgeVault capability meaning by defining multi-provider historical evidence references, exact-byte historical identity, and lineage semantics. The repository README must explain that KV may index evidence across owner-controlled providers without treating storage location, copies, or imported historical artifacts as current authority.

The README update must be part of the same source change set as the capability implementation.

## Governing invariants

```text
storage_location != authority
copy != original
historical_evidence != current_doctrine
import_receipt != truth_certification
semantic_interpretation != source_bytes
source_merge != live_provider_observation
```

A historical artifact record must preserve the original artifact identity separately from every later copy, normalized projection, interpretation, derived claim, or canonical present-day doctrine.

## Required artifact identity

Every admitted historical artifact record must include at minimum:

- stable artifact record ID;
- exact-byte SHA-256;
- original file name when available;
- MIME/media type when known;
- byte size;
- source provider/storage class;
- source locator represented without reusable credential material;
- first-observed timestamp;
- source-observed timestamp when available and separately labeled;
- ingest/receipt timestamp;
- source relationship (`ORIGINAL`, `COPY`, `MIRROR`, `DERIVED`, or `UNKNOWN`);
- parent/source artifact references for non-original material;
- current authority posture;
- contradiction/uncertainty state;
- receipt identity.

## Authority boundaries

Historical provenance ingestion grants none of the following:

- present execution authority;
- governance authority;
- publication authority;
- doctrinal authority;
- provider write authority;
- migration authority;
- permission to inspect private content without owner authorization.

Provider credentials remain behind SKAP.

## Initial source implementation

Planned bounded files:

- `schemas/kv-historical-artifact-record.schema.json`
- `runtime/historical_provenance.py`
- `tests/test_historical_provenance.py`
- `README.md`
- this handoff

The runtime helper is pure/local and accepts caller-supplied metadata plus exact bytes. It does not connect to iCloud, Google Drive, or any network provider.

## Completion boundary

Source completion requires:

1. schema installed;
2. deterministic artifact-record builder installed;
3. validation covering exact-byte hashing, source/copy relationships, authority posture, and fail-closed invalid lineage;
4. README updated in the same change set;
5. source review/validation and merge.

Live activation remains separate and requires owner-authorized provider access plus authentic observation of source artifacts. No live iCloud/Google Drive access may be inferred from source completion.
