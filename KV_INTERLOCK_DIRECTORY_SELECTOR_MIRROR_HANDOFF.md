# KV Interlock Directory Selector Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: `#166`
Branch: `feat/kv-interlock-directory-selector-166`
State: ACTIVE_IMPLEMENTATION
Updated: 2026-08-31T13:20:00-05:00
Authority effect: NONE

## Goal

Add one bounded request selector to the canonical `kv.interlock.request.v1` contract so read requests can identify an exact KnowledgeVault directory without overloading purpose or scope strings.

## Contract

Optional:

```json
"selector": {
  "directory_id": "pictures",
  "canonical_path": "04_Media/Pictures"
}
```

Rules:
- allowed only when `operation=REQUEST`;
- exactly these two fields;
- both non-empty strings;
- selector never establishes authority;
- the existing injected authority validator and policy evaluator remain mandatory.

## Claimed surfaces

- `schemas/kv-interlock-request.schema.json`
- `runtime/kv_interlock_endpoint.py`
- `tests/test_kv_interlock_runtime_endpoint.py`
- `docs/KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md`
- `KV_INTERLOCK_DIRECTORY_SELECTOR_MIRROR_HANDOFF.md`

## Completion boundary

Schema/runtime/tests/contract validation and merge.
