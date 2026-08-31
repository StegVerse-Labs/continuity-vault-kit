# KnowledgeVault Governed Document Export Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / CONNECTED_KV_OWNER_RUN_PARTIAL
Repository: StegVerse-Labs/continuity-vault-kit
Destination: GCAT-BCAT-Engine/Publisher
Updated: 2026-08-30

## Goal

Give a KnowledgeVault owner a governed path to create portable documents from
selected KV evidence without turning Publisher, a renderer, a model, transport,
or a stored credential into source or publication authority.

## Implemented source

```text
schemas/kv-document-export-request.schema.json
runtime/document_export.py
tools/prepare_document_export.py
fixtures/document-export/admitted.json
tests/test_document_export.py
.github/workflows/kv-document-export.yml
vault_template/KnowledgeVault/_System/Exports/**
```

The source distinguishes raw excerpts, owner-authored text, and AI-derived text;
binds every non-owner-authored section to admitted evidence; preserves fidelity,
retention, supersession, and content hashes; rejects restricted/policy/SKAP paths;
requires owner-approved redaction; prevents format expansion; and produces a
hash-bound Publisher bundle plus a deterministic preparation receipt.

## Lifecycle boundary

```text
KV request != prepared export
prepared export != transmitted bundle
transmitted bundle != Publisher admission
Publisher admission != rendered artifact
rendered artifact != publication
publication != release
revocation != deletion or public retraction authority
```

Current state:

```text
PLANNED: complete
IMPLEMENTED: source complete
VALIDATED: local validation and all seven exact-head pull-request workflows pass
MERGED: PR #127 at 9c98016b9698297110956baab744a1e77e4bc84b
DEPLOYED: yes — four `_System/Exports/` template files installed in the connected KV
ACTIVATED: no — verified DEVICE→KV InTr transport envelope/receipt remains unobserved
OBSERVED: yes — owner request, retained bundle, preparation/admission/render receipts, manifest, and Markdown/PDF/JSON artifacts were read back exactly from the connected KV
RECONSTRUCTED: yes for the retained owner-authorized bundle and selected Markdown/PDF/JSON renderers; byte-identical replay PASS
RELEASED: no
COMPLETE: no
```

## Remaining gates

1. Establish and observe the authentic verified DEVICE→KV InTr transport envelope and receipt required by `KV-INTERLOCK-v1`.
2. Repeat the already-proven retained-bundle Publisher admission/render path through that admitted InTr transport without changing the owner-authorized scope.
3. Preserve the exact returned artifact/receipt hashes and reconstruction proof as the activation evidence.
4. Keep publication/release as separate explicit transitions.

## Merge evidence

```text
pull_request: #127
validated_head: fbb134fadab466e7564dd459c54f1dad3244daa6
merge_commit: 9c98016b9698297110956baab744a1e77e4bc84b
Validate governed KV document export: 33290502575 SUCCESS
KV Guardrails: 33290502566 SUCCESS
Security Baseline: 33290502567 SUCCESS
Repository validation diagnostics: 33290502591 SUCCESS
Release integrity: 33290502568 SUCCESS
Reconstructive Memory Validation: 33290502579 SUCCESS
KnowledgeVault Execution Recovery: 33290502565 SUCCESS
```

## Local validation

```text
python -m unittest tests.test_document_export -v: 9/9 PASS
python tools/prepare_document_export.py ...: PASS
python -m unittest tests.test_global_hosted_workflow_authority -v: PASS
python -m compileall -q runtime tools tests: PASS
schema JSON parsing: PASS
repository-wide unittest discovery: 375 runnable tests PASS; 4 stale
provider-workflow assertions were reconciled to validation-only authority; 2
pytest-only modules are not runnable under the dependency-light unittest environment
```

## Authority

KV remains source-selection, authorization, redaction, fidelity, provenance, and
revocation authority. Publisher owns bounded composition and rendering only.
TV/TVC and SKAP credential authority are unchanged. GitHub Actions validates and
transports evidence only and cannot mutate canonical repository or runtime state.

🔒 Layer: Framework | KV


## Connected KnowledgeVault template installation — 2026-08-30

The governed destination surface is now deployed into the connected Google Drive-backed KnowledgeVault and exact-readback observed.

```text
KnowledgeVault root: 1c8OdhJeLD6E4ALmi-aR7dXvG8PjDLSfi
Exports:             1dDb6AIsSz-_F1qi_2FAkmPnp-YKuVYBI
Requests:            1R5Or1-YboebcHFLXaT4IdjzTgmw3fVk9
Receipts:            17KIqcMXhwRceEv5Xh0cUDmq38-VZgmNg
Artifacts:           1K12ZtW8rBISHTYyE3-62nglDz97escs8
installation receipt: 1nFcrBB-vvIc9Tyz6eGXbILb4NVWzrSBK
receipt sha256: b1f77fdc208be4bf132921f3df66cdd548c7bc549cc515bd66561c2a77fb8c3d
```

All four installed README files remain unconverted `text/plain` and were read back exactly. The installation receipt records `source_content_exact_match=true`, `activation_effect=false`, `owner_export_request_created=false`, and `intr_transport_performed=false`.

This proves **DEPLOYED** and scoped **OBSERVED** template state only. It does not prove owner authorization, InTr transmission, Publisher rendering, artifact readback, private-bundle reconstruction, publication, release, or runtime activation.

## First owner-authorized connected-KV document run — 2026-08-30

The owner authorized a non-restricted activation brief for the exact purpose
`Prove the authentic governed KV → InTr → Publisher → KV document-creation and reconstruction path.`
and limited formats to Markdown, PDF, and JSON.

Observed connected-KV records:

```text
source note:                 1zGar20KrIe0fKNkPpX9Hr1I_2W7cSnKE
request:                     1_DhXUcnnNsBblvmPT2fO-BWYwu5jLf9r
retained Publisher bundle:   1nnB6hAtOVbWCRiyyNj-IgBx46O6X-CE1
preparation receipt:         1XoLxpKUKoBFKvYQPm6M9vSpMaw5AA0zl
Publisher admission receipt: 1AeJBXMy4MuGu31Qt2hAZL2kHhbnO38v-
artifact manifest:           1c3HdjeTWjrPtxaitjQnJLzAqyld93nch
rendering receipt:           10WMrPEPwu0wn80Tg-Qt4Iqmy5vLHh_Ba
Markdown artifact:           1YxL-4kFGWyEb8r4SwdikRzsdhzmpAEDF
PDF artifact:                1iNtfhUwT1buzZ6C-UsTKTyVFZQE8FrCG
JSON artifact:               1A0VrzCyCtoHUzhQ7AF81V--2VUldLfuc
```

Semantic hashes:

```text
request_sha256:  sha256:55b3cbaa950f5440d0ae7c370220bc8f337aeac0ecab511ddd4c721adee8ed81
export_sha256:   sha256:98622e0ba7b3335c7eea6e4ab5d7a819aa73bc74a7e5db55ced0266dba3a014d
prepare receipt: sha256:2a6c12f0313544eedbb603872964a76322cc78c011022714de845eda3bb1e703
manifest:        sha256:20e83ce0dedbb873284c4f2c5ebf7adb966c6151fea999c3dc92f1a0ededcb25
render receipt:  sha256:2b0cf96e0356b3c714940e419c9755427016af1fa4ae2569aaf2f5b8e1aff78e
```

Artifact byte hashes after Drive readback:

```text
Markdown: sha256:8d44eaebe69796bca29db2762bad18de9b67e639ee72183d17c71b39c5511e0a
PDF:      sha256:1fc18e95da0f79c2fc680457d7598b7c094c9e6b31005d6afa95b9f611449ed2
JSON:     sha256:79998e80c83ae57ac81cdab52ea8e4db562f420d67f7b01380a60fc94d19e5ca
```

All selected renderers reproduced byte-identically from the retained private bundle.
This advances authentic owner request, preparation, Publisher admission/render,
artifact/receipt readback, and reconstruction evidence. It does **not** advance
`ACTIVATED`, because `runtime/kv_interlock_endpoint.py` requires a previously
verified DEVICE→KV InTr envelope and receipt and none was observed in this run.
No transport receipt was fabricated or inferred. Publication, release, deployment,
and execution authority remain false.


## Universal InTr application payload/import contract — issue #148

The KV document lane now has an application-side exact-byte boundary matching the
canonical StegOS `publisher-artifact-transfer` profile.

```text
runtime/document_intr_transfer.py
  prepared owner-authorized bundle
    -> stegverse.publisher.artifact-transfer/v1 exact canonical bytes

  stegverse.publisher.artifact-return/v1 exact bytes
    -> exact artifact/manifest/source-export validation
    -> stegverse.kv.publisher-artifact-import-candidate/v1
    -> transport-bound import receipt
```

The import candidate is deliberately non-mutating:

```text
candidate_only=true
canonical_kv_mutation_authorized=false
publication_authorized=false
release_authorized=false
execution_authorized=false
authority_effect=NONE
```

A `stegverse.kv.publisher-artifact-import-receipt/v1` may be built only after
the caller supplies the authentic terminal reverse-InTr receipt hash. Its result
remains `VALIDATED_IMPORT_CANDIDATE_NOT_COMMITTED`.

This source does not construct StegOS transport intents/hop receipts or claim
forward/return transport. It is the KV application contract consumed by the
sovereign Universal InTr runtime.
