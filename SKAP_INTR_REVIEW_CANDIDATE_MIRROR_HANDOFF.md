# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_PENDING_REVIEW_AND_RUNTIME_VALIDATION
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24

## Active goal

Define and validate a machine-readable review-candidate protocol for:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

`InTr` is the canonical bidirectional interlock/transport relationship between adjacent domains. Transport, packet possession, model output, or receipt possession does not itself confer execution, identity, continuity, governance, or secret-custody authority.

## Implemented artifacts

### Topology contract

- `specs/skap-intr-review-candidate.v1.json` — `9ad3038fac16e34f2fc4615bc75e491b21ba311d`
- `schemas/skap-intr-review-candidate.schema.json` — `380ba768196afb391299b2eb50b032cfa4491ad7`
- `scripts/validate_skap_intr_review_candidate.py` — `6ecd9be372fe84ffdf402277901b0e2eb3bb356d`

### Packet / envelope contract

- `specs/intr-packet-review-candidate.v1.json` — `ba83d378477d1c5058bb80094e136d225763d21f`
- `schemas/intr-packet-review-candidate.schema.json`
  - introduced: `d630e64dab7ffd3731b2622ab0a1a3837a4b6d95`
  - repaired top-level state-machine/failure property definitions: `5de479f0a8569389900446bc8c6682c51b6ec185`
- `scripts/validate_intr_packet_review_candidate.py` — `9ab2479b01db7b64d0a8852312d0d50007b9998d`

The packet binds packet id/version, canonical adjacent source/next/final roles, operation hash, payload hash, prior receipt hash, timestamps, nonce, replay state, authority non-transfer, boundary proof, sealed protected payload, SKAP credential grant, endpoint constraints and receipt policy.

### Per-hop receipt / reconstruction contract

- `schemas/intr-hop-receipt.schema.json` — `559795e32ba8cd4591750fc0c8e813f93ee35b2e`
- `scripts/intr_hop_receipt.py` — `53d34e581f23bfad5b182cda4b6632a94452e9e0`
- `examples/intr-hop-receipt-chain.example.json` — `34298042c255a2cac5e2a9ecfb38e99549505e78`

The example is a four-hop forward hash chain: `SKAP -> KV -> DEVICE -> EXTERNAL_NETWORK -> ENDPOINT`.

### Hosted validation integration

Existing `.github/workflows/kv-guardrails.yml` was extended rather than creating another workflow.

Commit: `db7a99d65f86b43f28683e06826416d25751120d`

The lane now performs:

- JSON Schema validation for topology, packet and every hop receipt;
- topology semantic validator with deterministic negative tests;
- packet semantic validator with deterministic negative tests;
- receipt-chain verification;
- Python compile checks;
- explicit non-authorizing workflow checks (`contents: read`, no `contents: write`, no `git push`, no `secrets.` references).

This is validation/control-plane behavior only and grants no production or SKAP secret authority.

## Authority and secret boundary

- SKAP owns secret custody state; custody does not create identity, continuity, governance, or execution authority.
- KV preserves sealed SKAP state and continuity evidence; possession of KV does not grant secret resolution authority.
- Device is an ephemeral execution/transport edge and must not become secret-custody or continuity authority by carrying a packet.
- External Network is transport environment only and must never hold protected plaintext merely by transit.
- Endpoint-bound credential material remains sealed until the intended endpoint/session is positively verified, the operation grant remains valid, and revocation is rechecked immediately before resolution.
- Credential resolution and native endpoint credential submission must occur on the same authenticated session; changing sessions after verification fails closed.
- Return-path communication uses InTr and must not carry secret plaintext.
- Model output grants no execution authority.

## Packet state requirements

Canonical hop sequence:

```text
ISSUED -> BOUNDARY_VERIFIED -> CLAIMED -> FORWARDED -> RECEIPTED -> TERMINAL
```

Endpoint resolution sequence:

```text
ARRIVED_SEALED
-> ENDPOINT_SESSION_VERIFIED
-> GRANT_REVALIDATED
-> CREDENTIAL_RESOLVED_TRANSIENTLY
-> SUBMITTED_ON_SAME_SESSION
-> PLAINTEXT_DISCARDED
-> RECEIPTED
```

Failure dispositions:

- wrong boundary: `FAIL_CLOSED`
- expired packet: `FAIL_CLOSED`
- replay detected: `FAIL_CLOSED`
- authority mismatch: `FAIL_CLOSED`
- endpoint mismatch: `FAIL_CLOSED`
- revoked credential: `FAIL_CLOSED`
- session changed after endpoint verification: `FAIL_CLOSED`
- ambiguous state after submission: `VERIFY_EXTERNALLY`

## Validation evidence

### Topology candidate

Local deterministic semantic evidence passed for the baseline topology and rejected seven negative mutations: KV bypass, authority transfer, unsealed network transit, premature endpoint resolution, return secret plaintext, Device secret-custody escalation, and External Network plaintext possession.

### Packet candidate

Local deterministic semantic evidence passed for the baseline packet and rejected eight negative mutations: non-adjacent next hop, authority transfer, plaintext protected payload, exhausted replay count, changed authenticated session, skipped immediate revocation check, secret-bearing receipts, and automatic retry after ambiguous submission.

### Receipt chain

The four-hop example was locally verified for canonical order, stable packet/operation/payload hashes, contiguous hop indexes, canonical receipt hashes, prior-receipt linkage, zero secret plaintext and zero authority transfer. A deliberately broken prior link was detected.

### Hosted evidence

The hosted validation lane is installed at commit `db7a99d65f86b43f28683e06826416d25751120d`. The GitHub combined-status accessor returned `statuses: []`; this is neither pass nor failure evidence. Hosted results therefore remain OPEN until an observable run/job conclusion is retrieved.

## Review gates

- `RC-01-SCHEMA`: IMPLEMENTED / HOSTED RESULT OPEN — schemas corrected and wired into KV Guardrails.
- `RC-02-NEGATIVE-TOPOLOGY`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN.
- `RC-03-AUTHORITY`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN.
- `RC-04-ENDPOINT-RESOLUTION`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN.
- `RC-05-PACKET`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN.
- `RC-06-RECEIPT-CHAIN`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN.
- `RC-07-RUNTIME`: OPEN — requires observed real InTr transitions across all four adjacent boundaries with replayable non-secret receipts.
- `RC-08-REAL-SKAP`: OPEN — no real password/key/API secret may be admitted until review acceptance plus runtime proof establish the sealed credential path.

## Next executable work

1. Retrieve/inspect an observable KV Guardrails run for `db7a99d6...` or a descendant and remediate any actual failure.
2. Define the SKAP sealed-object storage contract and lifecycle (`SEALED`, `ACTIVE`, `ROTATED`, `REVOKED`, `RECOVERY_ONLY`) without storing real credentials.
3. Define the endpoint-session proof object consumed immediately before transient credential resolution.
4. Add reverse/return InTr packet and receipt fixtures.
5. Bind packet/receipt persistence into KV Continuity storage without making KV secret-resolution authority.
6. Only after review acceptance and runtime proof, perform the first owner-authorized real SKAP credential ingress.

## Completion boundary

This goal remains open. Source, schemas, validators, fixtures, local semantic passes, workflow installation or durable handoff are not activation. Completion requires observable hosted validation evidence, review acceptance, runtime InTr transitions across every adjacent boundary, replayable non-secret receipt reconstruction, and an owner-authorized real SKAP credential operation with all authority and secret boundaries intact.
