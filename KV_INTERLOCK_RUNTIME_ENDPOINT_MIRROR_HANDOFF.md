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


## 2026-08-27 response-hash compatibility repair

Cross-repository inspection against the hosted-validated StegHealth `KV-INTERLOCK-v1` specialization exposed a source-level runtime compatibility defect: issue #79 computed `receipt.response_hash` over the full response including receipt metadata (with only `response_hash` removed), while the established StegHealth client verifies the canonical response payload projection.

The runtime core is corrected to hash exactly:
`schema_version`, `request_id`, `decision`, `granted_scope`, `context`, and `source_refs`.

The protocol now states this projection explicitly, and the runtime test independently constructs the projection before comparing the digest. This is a compatibility repair only. It does not deploy the endpoint, establish boundary identity/sealing, grant credential or execution authority, mutate canonical KV state, or activate production runtime.

State: `HOSTED_VALIDATED_MERGED`.

Validation evidence:
- PR `#86`;
- exact head `e48bcc53e93c0f059a3e557a146e35dbe49097ce`;
- Repository validation diagnostics run `33121047732`: PASS;
- Validate KV Interlock Contract run `33121047747`: PASS;
- KV Guardrails run `33121047902`: PASS;
- Security Baseline run `33121047899`: PASS;
- merge `1cb64044e9e10364f7ddb4b0ff514c1f06c3eac5`;
- durable evidence `evidence/kv/2026-08-27-runtime-response-hash-compatibility-validation.json`.

Production endpoint deployment and live boundary identity/sealing remain unobserved.


## Endpoint fanout probe — 2026-08-30

A machine-executed local-isolated contract test now exercises one non-secret probe through the existing `KVInterlockRuntime.handle` request boundary and reduces the outcome to exactly two bounded report structures.

Source:

```text
tools/run_endpoint_fanout_probe.py
tests/test_endpoint_fanout_probe.py
.github/workflows/validate-kv-interlock-contract.yml
evidence/kv/2026-08-30-endpoint-fanout-probe-local.json
PR #150
```

Probe:

```text
probe_id: manual-endpoint-fanout-001
value: stegverse-endpoint-fanout-probe
classification: TEST_ONLY_NON_SECRET
probe_sha256: a1efc09faba9a044f7778192387584a4564444bce08f8ea45141202e9db4b4c0
```

Report 1 — KV Interlock endpoint status:

```text
schema: stegverse.kv-interlock.endpoint-status-report.v1
endpoint_status: PASS
decision: ALLOW_BOUNDED_CONTEXT
request_payload_sha256: sha256:be0483e6057696cec2338878bb2d82af084f659be6d04b928f80ce429181e30a
intr_receipt_ref: sha256:799595a0e78a890a1a5936caed170a4d053576c25964c554b2311ee9e77a5315
response_hash: 3a6573085535b2b3df624851b8a14edfdb403212cf723547bd166cb83743ec56
report_sha256: b5f4f9a3a1cbbf982b851c11d5dbb5f47679bf0e2b9682648a2e7aeccab6e214
canonical_state_changed: false
execution_authority: NONE
credential_authority: TV/TVC
```

Report 2 — Master Records travel report:

```text
schema: stegverse.master-records.travel-report.v1
local custody state: TEST_ONLY_RECORDED
master_record_ref: master-record:sha256:cd421a1c3d2989dadb8d172c50ed2f270bfbfa9c9260e741df09c597897259f8
hop_count: 5
1 TEST_PROBE_INGRESS
2 DEVICE->KV
3 KV_INTERLOCK_RUNTIME
4 REPORT_FANOUT
5 MASTER_RECORDS_TEST_CUSTODY
authority_granted: false
production_custody_claimed: false
```

The fanout is intentionally asymmetric: the KV report returns the endpoint disposition and hash/receipt binding, while the Master Records report retains the traversal chain and the hash of the record offered to the Master Records-compatible custody contract.

This proves the requested one-input/two-report reduction in an isolated contract integration. It does **not** prove production endpoint deployment, live DEVICE_KV_INTR, or live authenticated Master Records custody.

Live follow-up is tracked in `master-records/orchestration#50`. That repository's current root handoff marks live authenticated custody round-trip work as machine-owned / authority-bound, so this test does not compete with or synthesize that external evidence.
