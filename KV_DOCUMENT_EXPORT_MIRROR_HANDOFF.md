# KnowledgeVault Governed Document Export Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / CONNECTED_KV_TEMPLATE_INSTALLED
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
ACTIVATED: no
OBSERVED: yes — exact template files and scoped installation receipt read back; no owner request, transport, render, or artifact readback
RECONSTRUCTED: synthetic fixture replay is deterministic; no retained private-KV replay evidence
RELEASED: no
COMPLETE: no
```

## Remaining gates

1. Obtain one owner-authorized non-restricted KV export request and Interlock receipts.
2. Transport the admitted scoped bundle through InTr to Publisher.
3. Admit and render the exact authorized formats in Publisher.
4. Read back the artifacts, manifest, and receipts into the private KV and verify hashes.
5. Prove deterministic reconstruction from the retained private bundle.

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
