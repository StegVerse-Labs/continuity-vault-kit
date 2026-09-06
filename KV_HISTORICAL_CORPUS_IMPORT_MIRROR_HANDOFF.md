# KV Historical Corpus Import Mirror Handoff

Status: ACTIVE_IMPLEMENTATION / SOURCE_FIRST  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#191`  
Branch: `feature/kv-historical-corpus-import-191`  
Updated: 2026-09-05  
Authority effect: NONE  
Activation effect: false

## Purpose

Implement the first owner-authorized historical-corpus import/receipt path using the merged provider-neutral historical provenance contract without modifying historical source bytes, migrating an existing vault, or turning storage location or custody into authority.

## Canonical dependency reuse

This work consumes rather than replaces:

- `docs/CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md` — repository-local continuation source of truth;
- `KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md` — exact-byte historical artifact identity and lineage;
- `runtime/historical_provenance.py` — canonical historical artifact record builder/validator;
- `KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md` and `runtime/direct_source_ingress.py` — provider/source provenance and SKAP-bounded direct-source semantics;
- `KV_PROVIDER_SURFACE_CAPABILITIES_MIRROR_HANDOFF.md` — generic provider/device capability facts;
- existing Interlock/InTr boundaries for governed ingress/egress;
- Master Records destination custody semantics, which remain independently validating and non-authorizing.

No parallel provider ingress, historical identity, credential authority, task authority, or Master Records authority is introduced.

## Machine preflight — 2026-09-05

Preflight state: `PASS_FOR_BOUNDED_SOURCE_IMPLEMENTATION`.

Resolved before functional mutation:

1. The repository-wide canonical handoff remains `docs/CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`.
2. The immediate predecessor handoff is `KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md`; issue #188 is source-complete and names this task as its next integration candidate.
3. Canonical ecosystem task registry generation 15 preserves the authority split: Task Registry = work intent/coordination; WorkerCoordinator = execution claim/fence authority; Master Records = observed-reality/reconstruction authority; Interlock/InTr = governed task ingress/egress. This issue does not mint execution authority from repository state.
4. `master-records/core-lite/MASTER_RECORDS_MIRROR_HANDOFF.md` remains the current Master Records repository-wide handoff. Its custody pattern requires independent validation before destination acknowledgement and explicitly separates custody from runtime, execution, publication, and continuity authority.
5. No existing `KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md` or implementation for `KV-HISTORICAL-CORPUS-IMPORT-001` exists on `main`; creating this handoff is therefore the first required task action.
6. Existing `CVK-LEGACY-KV-UPGRADE-174` remains a separate migration/reinstall lane. This task may not modify or overwrite either the legacy iCloud KnowledgeVault or the current Google Drive KnowledgeVault.
7. Open PR #161 owns portable direct-source canonical-raw persistence paths. This task will not modify `runtime/portable_direct_source_ingress.py`, its tests, or its mirror handoffs; it will consume merged/public contracts only.
8. Open PR #186 changes only governed connector capability documentation and does not overlap the source paths claimed here.

## README completeness predicate

README change required: **YES**.

Reason: this task advances capability meaning from passive historical-provenance records to an explicit owner-authorized import receipt, custody-request projection, and bounded downstream status model. The README must state that import/custody proves receipt and lineage only, does not certify truth, and does not grant publication, governance, execution, migration, provider-write, or Master Records destination-acknowledgement authority.

The README update must be part of the same implementation change set.

## Source implementation boundary

The bounded source implementation will:

1. accept caller-supplied exact bytes plus owner-authorization evidence reference and source metadata;
2. reuse `build_artifact_record()` / `assert_artifact_record()` for exact-byte identity;
3. emit a deterministic historical import receipt bound to the artifact record SHA-256 and owner-authorization reference;
4. emit a Master Records custody-request candidate that explicitly has `destination_acknowledgement_minted=false` and `destination_custody_accepted=false`;
5. preserve ORIGINAL/COPY/MIRROR/DERIVED lineage and contradiction state without silent merge;
6. emit a bounded Site/MyKV status projection that contains identifiers/state only and no source bytes or private content;
7. fail closed on byte/hash mismatch, missing owner authorization, authority escalation, or invalid custody state.

The source helper will perform no provider login, network access, private-vault discovery, publication, vault migration, or Master Records write.

## Governing invariants

```text
owner_authorization_ref != reusable_secret
import_receipt != truth_certification
import_receipt != publication_authority
custody_request != destination_custody_acceptance
custody_request != master_records_acknowledgement
historical_evidence != current_doctrine
site_status_projection != private_content
source_merge != live_provider_observation
```

## Claimed source paths

- `KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md`
- `schemas/kv-historical-import-receipt.schema.json`
- `schemas/kv-historical-custody-request.schema.json`
- `schemas/kv-historical-status-projection.schema.json`
- `runtime/historical_corpus_import.py`
- `tests/test_historical_corpus_import.py`
- `tools/check_kv_historical_corpus_import.py`
- `.github/workflows/kv-historical-corpus-import.yml`
- `data/session-work-claims.d/cvk-historical-corpus-import-191-20260905.json`
- `README.md`

## Completion boundary

Source completion requires all claimed schemas/helpers/tests/validator/workflow and README semantics to be installed, exact-head applicable validation to pass, and the source PR to merge.

Live corpus activation remains separate. It requires an owner-selected artifact and explicit owner authorization at runtime. A repository merge must not be represented as evidence that iCloud, Google Drive, or any private historical artifact was accessed.

Master Records custody is also a separate destination action. This repository may construct a custody-request candidate, but only Master Records may independently validate and mint its destination acknowledgement/custody record.

## Next integration after source completion

After source completion, the next admissible integration is an authentic owner-authorized corpus-import execution through the existing provider/SKAP/InTr path, followed by independent Master Records custody validation and a bounded Site/MyKV status projection. No source bytes are to be exposed to Site merely because import/custody metadata exists.
