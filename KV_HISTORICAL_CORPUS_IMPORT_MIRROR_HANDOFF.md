# KV Historical Corpus Import Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_OWNER_AUTHORIZED_EXECUTION_PENDING  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#191`  
Implementation PR: `#193`  
Merge commit: `7b84542d814ff18c132cfc4e6962f5a37d38c830`  
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

No parallel provider ingress, historical identity, credential authority, task authority, or Master Records authority was introduced.

## Machine preflight — 2026-09-05

Preflight state: `PASS_FOR_BOUNDED_SOURCE_IMPLEMENTATION`.

Resolved before functional mutation:

1. The repository-wide canonical handoff remained `docs/CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`.
2. The predecessor `KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md` was source-complete and named this task as its next integration candidate.
3. Canonical ecosystem task registry generation 15 preserved the authority split: Task Registry = work intent/coordination; WorkerCoordinator = execution claim/fence authority; Master Records = observed-reality/reconstruction authority; Interlock/InTr = governed task ingress/egress.
4. `master-records/core-lite/MASTER_RECORDS_MIRROR_HANDOFF.md` remained the current Master Records repository-wide handoff and required independent destination validation before acknowledgement/custody acceptance.
5. No duplicate historical-corpus import handoff/implementation existed on `main` before this task.
6. `CVK-LEGACY-KV-UPGRADE-174` remained a separate migration/reinstall lane and neither physical KV was modified.
7. Open PR #161 owned portable direct-source canonical-raw persistence paths; this task did not modify those paths.
8. Open PR #186 changed only governed connector capability documentation and did not overlap this task's source paths.

## README completeness predicate

README change required: **YES**, and satisfied in PR #193.

The README now documents owner-authorized historical import receipts, source-only Master Records custody requests, bounded Site/MyKV status projection, and the non-authority boundaries around truth, publication, governance, execution, migration, provider write, and destination custody acknowledgement.

## Implemented source behavior

The merged implementation:

1. requires caller-supplied exact bytes plus owner-authorization, InTr admission, and persistence evidence references;
2. reuses `assert_artifact_record()` for exact-byte historical identity;
3. emits a deterministic historical import receipt whose canonical hash binds artifact identity, relationship/contradiction state, authorization reference, admission/persistence evidence, and time;
4. emits a Master Records custody-request candidate with destination acceptance/acknowledgement and independent validation fixed false;
5. preserves ORIGINAL/COPY/MIRROR/DERIVED lineage and contradiction state without silent merge;
6. emits a bounded Site/MyKV status projection with identifiers/state only and `private_content_included=false`;
7. fails closed on byte/hash mismatch, missing or secret-bearing authorization references, authority escalation, receipt tamper, invalid destination custody assertions, and custody/import mismatch;
8. advances the exact read-only hosted workflow census from 49 to 50 for the added validation workflow.

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

## Implemented source surfaces

- `KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md`
- `schemas/kv-historical-import-receipt.schema.json`
- `schemas/kv-historical-custody-request.schema.json`
- `schemas/kv-historical-status-projection.schema.json`
- `runtime/historical_corpus_import.py`
- `tests/test_historical_corpus_import.py`
- `tests/test_global_hosted_workflow_authority.py`
- `tools/check_kv_historical_corpus_import.py`
- `.github/workflows/kv-historical-corpus-import.yml`
- `data/session-work-claims.d/cvk-historical-corpus-import-191-20260905.json`
- `README.md`

## Validation evidence

Initial PR head `ff434e4317ca1b17a89911a2aa356035b6685551` exposed one task-local validator packaging defect: direct execution of `tools/check_kv_historical_corpus_import.py` could not resolve the repository `runtime` package. Focused unit tests had already passed. The validator was corrected to place the repository root on `sys.path`; no capability or authority semantics were weakened.

Final validated head: `ed18b0f0a62669247b38642eb00ce3e4d07f3acf`.

Exact-head validation:

- `KV Historical Corpus Import` run `34009779451`: PASS;
- `Repository validation diagnostics` run `34009779449`: PASS;
- `Security Baseline` run `34009779452`: PASS;
- `Release integrity` run `34009779448`: PASS;
- `KV Historical Provenance` run `34009779465`: PASS;
- `KV Guardrails` run `34009779487`: PASS.

PR #193 merged as `7b84542d814ff18c132cfc4e6962f5a37d38c830`.

## Source completion

```text
mirror handoff: COMPLETE
schemas: 3 / 3 COMPLETE
runtime helper: COMPLETE
focused tests: COMPLETE
source validator: COMPLETE
read-only workflow: COMPLETE
README predicate: SATISFIED
workflow census: 50 / 50
exact-head applicable validation: PASS
merge: COMPLETE
source stubs: 0
```

## Separate live/destination boundaries

No live iCloud or Google Drive access is claimed from source completion.
No private historical artifact was accessed by this source build.
No authentic owner-authorized corpus import has yet executed.
No Master Records destination custody acknowledgement has yet been minted.
No Site/MyKV live projection has yet been observed.

Authentic execution requires an owner-selected historical artifact plus explicit owner authorization through the existing provider/SKAP/InTr path. Master Records must then independently validate any source custody request before minting destination custody/acknowledgement.

## Next integration goal

The next machine-executable integration is the destination/runtime preparation for authentic custody and bounded projection:

1. install/verify the Master Records historical-corpus custody validator/contract without minting a live custody record;
2. verify Site/MyKV can consume only the bounded status projection without private source content;
3. keep authentic provider/artifact execution blocked until owner authorization and exact source bytes are actually supplied through the admitted runtime path.

The existing propagation-verification task is `StegVerse-Labs/continuity-vault-kit#192`.
