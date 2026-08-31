# Portable Direct-Source Canonical Admission Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: `#162`
Branch: `feat/portable-canonical-admission-159`
State: ACTIVE_IMPLEMENTATION
Updated: 2026-08-31T11:37:00-05:00
Credential authority: TV/TVC
Authority effect: NONE

## Goal

Complete the owner-controlled credential-free direct-source lane after exact staging by deterministically promoting the staged batch into its requested canonical private KnowledgeVault directory with provenance, exact readback, and a canonical admission receipt.

## Scope

Only:

```text
source_class = OWNER_CONTROLLED_FILE
credential_requirement = NONE
staging receipt = STAGED_UNTRUSTED + exact_readback_verified
```

Credentialed mailbox/provider/account sources remain on their SKAP/TVC provider-session lanes.

## Canonical path

```text
00_Inbox/DirectSource/<directory>/<materialization_id>
 -> verify immutable manifest + exact file hashes + staging receipt
 -> <requested_canonical_path>/<materialization_id>/files/*
 -> provenance.json
 -> admission-receipt.json
 -> exact canonical readback
```

The materialization subdirectory prevents cross-batch filename collision and preserves reconstructable provenance.

## Required admission evidence

- request/staging receipt binding;
- exact staged-file SHA-256;
- canonical destination path;
- write-once persistence;
- exact canonical readback;
- provenance binding to materialization/request/payload/ingress receipt;
- no credential material;
- no provider session required;
- no authority transfer;
- idempotent retry.

## Claimed surfaces

- `runtime/portable_direct_source_ingress.py`
- `tests/test_portable_direct_source_ingress.py`
- `schemas/kv-portable-direct-source-canonical-admission-receipt.schema.json`
- `tools/check_portable_direct_source_ingress.py`
- `PORTABLE_DIRECT_SOURCE_CANONICAL_ADMISSION_MIRROR_HANDOFF.md`

## Completion boundary

Source completion requires exact deterministic promotion/readback tests, repository validation, and merge. Resident execution then becomes a bounded call from the existing DEVICE_KV consumer after staging.
