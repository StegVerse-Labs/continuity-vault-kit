# KnowledgeVault Governed Document Export Mirror Handoff

Status: IMPLEMENTED_LOCAL_VALIDATED
Repository: StegVerse-Labs/continuity-vault-kit
Destination: GCAT-BCAT-Engine/Publisher
Updated: 2026-08-29

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
IMPLEMENTED: source complete on feature branch
VALIDATED: dependency-light local unit, CLI, schema, compile, and hosted-authority checks pass
MERGED: no
DEPLOYED: no
ACTIVATED: no
OBSERVED: no connected-KV request/artifact readback
RECONSTRUCTED: synthetic fixture replay is deterministic; no retained private-KV replay evidence
RELEASED: no
COMPLETE: no
```

## Remaining gates

1. Validate the exact branch head through repository workflows.
2. Merge only the validated head.
3. Install the four-file `_System/Exports/` source-template delta into the connected KV.
4. Obtain one owner-authorized private-KV export request and Interlock receipts.
5. Admit and render the exact bundle in Publisher.
6. Read back the artifact manifest and receipt into the private KV.
7. Prove deterministic reconstruction from the retained private bundle.

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
