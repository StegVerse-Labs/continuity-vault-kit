# KV Interlock Runtime Endpoint Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #79
Branch: `main`
State: MERGED_VALIDATED_SOURCE_RUNTIME_DEPLOYMENT_OPEN

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
source implementation: MERGED
hosted validation: PASS
merge: 4381edb086928d61615c99c0a0ba56e3a5d1c667
production endpoint deployed: false
live InTr boundary verified: false
live boundary identity/sealing service observed: false
canonical Site readback observed: false
owner/device/install production transitions observed: false
activation: false
```

## Next executable boundary

Consume the merged endpoint core from the existing sovereign resident/runtime activation lane. Bind it only behind a real verified DEVICE->KV InTr boundary identity/sealing service and durable receipt store; then observe canonical Site readback. Do not create a second endpoint or treat hosted validation as deployment.


## Merge and validation evidence

```text
PR: #80
validated head: af967aafb797799a760b76aeedab00b6b1c85ce1
merge: 4381edb086928d61615c99c0a0ba56e3a5d1c667
Validate KV Interlock Contract: 33118657666 SUCCESS
Security Baseline: 33118657661 SUCCESS
Release integrity: 33118657664 SUCCESS
Repository validation diagnostics: 33118657634 SUCCESS
KV Guardrails: 33118657667 SUCCESS
```

The first pre-repair exact-head runs correctly failed because the protocol footer was no longer terminal after documentation insertion. Commit `af967aafb797799a760b76aeedab00b6b1c85ce1` restored canonical footer ordering; the full exact-head validation set then passed. This was a documentation-layer defect, not a runtime-authority relaxation.

## Current runtime boundary

```text
runtime endpoint source: MERGED
runtime endpoint hosted validation: PASS
production endpoint deployment: NOT OBSERVED
verified live DEVICE->KV boundary identity/sealing: NOT OBSERVED
durable production receipt-store binding: NOT OBSERVED
canonical Site production readback: NOT OBSERVED
owner/device/install activation: NOT OBSERVED
authority_effect: NONE
```

Existing runtime ownership remains upstream/downstream coordinated through the sovereign resident execution lane and TV/TVC authority boundaries. No new resident worker, credential broker, or Site endpoint is authorized by this handoff.
