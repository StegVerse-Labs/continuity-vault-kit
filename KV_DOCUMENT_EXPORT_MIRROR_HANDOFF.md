# KnowledgeVault Governed Document Export Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / CONNECTED_KV_INSTALLATION_PENDING
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
DEPLOYED: no
ACTIVATED: no
OBSERVED: no connected-KV request/artifact readback
RECONSTRUCTED: synthetic fixture replay is deterministic; no retained private-KV replay evidence
RELEASED: no
COMPLETE: no
```

## Remaining gates

1. Install the four-file `_System/Exports/` source-template delta into the connected KV.
2. Obtain one owner-authorized private-KV export request and Interlock receipts.
3. Admit and render the exact bundle in Publisher.
4. Read back the artifact manifest and receipt into the private KV.
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
