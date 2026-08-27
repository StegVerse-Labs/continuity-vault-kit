# KV Interlock Runtime Endpoint Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #79
Branch: `feat/kv-interlock-runtime-endpoint-79`
State: CLAIMED_FOR_IMPLEMENTATION

## Goal

Implement the missing fail-closed runtime endpoint core for the already-canonical `KV-INTERLOCK-v1` request/response contract without claiming production activation.

## Canonical upstream contracts

- `docs/KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md`
- `schemas/kv-interlock-request.schema.json`
- `schemas/kv-interlock-response.schema.json`
- `schemas/kv-interlock-intr-envelope.schema.json`
- `KNOWLEDGEVAULT_MODULE_INTEGRATIONS_MIRROR_HANDOFF.md`

## Authority boundary

```text
KV remains canonical personal-record custodian
Interlock/InTr admission is required
TV/TVC remains credential/key authority
runtime endpoint grants filesystem authority: false
runtime endpoint grants credential authority: false
runtime endpoint grants SKAP authority: false
runtime endpoint grants provider authority: false
runtime endpoint grants execution authority: false
COMMIT_CANDIDATE changes canonical state: false
GitHub Actions production authority: NONE
```

The runtime core may consume only an already-verified DEVICE->KV InTr admission context. It must not create boundary identity, mint authority, acquire credentials, or infer a valid owner session from a request body.

## Planned source surfaces

```text
runtime/kv_interlock_endpoint.py
tests/test_kv_interlock_runtime_endpoint.py
.github/workflows/validate-kv-interlock-contract.yml
docs/KNOWLEDGEVAULT_INTERLOCK_PROTOCOL.md
KNOWLEDGEVAULT_MODULE_INTEGRATIONS_MIRROR_HANDOFF.md
```

## Required behavior

1. Canonical request shape and operation validation.
2. Exact verified DEVICE->KV admission binding.
3. Injected authority validation; missing/stale authority fails closed.
4. Injected policy decision; granted scope may never exceed requested scope.
5. Bounded context may contain only granted fields.
6. Secret-like context fields fail closed.
7. REQUEST returns source references and secret-free receipt evidence.
8. COMMIT_CANDIDATE is candidate-only and never mutates canonical state.
9. Receipt persistence is injected and secret-free; receipt hash is deterministic.
10. Ambiguous adapter/runtime results fail closed with no blind retry semantics.

## Collision boundary

Do not modify or depend on PR #78 hosted release-authority retirement. Do not create a second Site endpoint, credential broker, SKAP vault, or runtime authority.

## Current non-claims

```text
source implementation: PENDING
hosted validation: PENDING
merge: PENDING
production endpoint deployed: false
live InTr boundary verified: false
live boundary identity/sealing service observed: false
canonical Site readback observed: false
owner/device/install production transitions observed: false
activation: false
```

## Next executable boundary

Implement the dependency-light runtime core and deterministic negative/positive tests, wire them into the existing KV Interlock validation workflow, validate the exact branch head, and merge only after green evidence.
