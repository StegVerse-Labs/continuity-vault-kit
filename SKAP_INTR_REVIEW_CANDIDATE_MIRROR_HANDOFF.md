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

- `specs/skap-intr-review-candidate.v1.json`
  - commit: `9ad3038fac16e34f2fc4615bc75e491b21ba311d`
- `schemas/skap-intr-review-candidate.schema.json`
  - commit: `380ba768196afb391299b2eb50b032cfa4491ad7`
- `scripts/validate_skap_intr_review_candidate.py`
  - commit: `6ecd9be372fe84ffdf402277901b0e2eb3bb356d`

### Packet / envelope contract

- `specs/intr-packet-review-candidate.v1.json`
  - commit: `ba83d378477d1c5058bb80094e136d225763d21f`
  - binds packet id/version, canonical adjacent source/next/final roles, operation hash, payload hash, prior receipt hash, timestamps, nonce, replay state, authority non-transfer, boundary proof, sealed protected payload, SKAP credential grant, endpoint constraints and receipt policy.
- `schemas/intr-packet-review-candidate.schema.json`
  - commit: `d630e64dab7ffd3731b2622ab0a1a3837a4b6d95`
- `scripts/validate_intr_packet_review_candidate.py`
  - commit: `9ab2479b01db7b64d0a8852312d0d50007b9998d`
  - enforces canonical adjacency, sealed transit, replay bounds, expiry ordering, SKAP reference semantics, HTTPS endpoint constraint, immediate pre-resolution revocation check, same authenticated session for resolution + submission, secret-free receipts, and `VERIFY_EXTERNALLY` for ambiguous post-submission state.

### Per-hop receipt / reconstruction contract

- `schemas/intr-hop-receipt.schema.json`
  - commit: `559795e32ba8cd4591750fc0c8e813f93ee35b2e`
- `scripts/intr_hop_receipt.py`
  - commit: `53d34e581f23bfad5b182cda4b6632a94452e9e0`
  - builds/verifies canonical hash-bound hop receipts and verifies receipt chains.
- `examples/intr-hop-receipt-chain.example.json`
  - commit: `34298042c255a2cac5e2a9ecfb38e99549505e78`
  - four-hop forward chain: SKAP->KV->DEVICE->EXTERNAL_NETWORK->ENDPOINT.

## Authority and secret boundary

- SKAP owns secret custody state; it does not gain identity, continuity, governance, or execution authority from custody.
- KV preserves sealed SKAP state and continuity evidence; possession of KV does not grant secret resolution authority.
- Device is an ephemeral execution/transport edge and must not become secret-custody or continuity authority by carrying a packet.
- External Network is transport environment only and must never hold protected plaintext merely by transit.
- Endpoint-bound credential material remains sealed until the intended endpoint/session is positively verified, the operation grant is still valid, and revocation state has been rechecked immediately before resolution.
- Credential resolution and native endpoint credential submission must occur on the same authenticated session; changing sessions after verification fails closed.
- Return-path communication uses InTr and must not carry secret plaintext.
- Model output grants no execution authority.

## Packet state requirements

Canonical hop state sequence:

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

Local deterministic semantic evidence passed for the baseline topology and rejects seven negative mutations: KV bypass, authority transfer, unsealed network transit, premature endpoint resolution, return secret plaintext, Device secret-custody escalation, and External Network plaintext possession.

### Packet candidate

Local deterministic semantic evidence passed for the baseline packet semantics and rejects eight negative mutations:

1. non-adjacent next hop;
2. authority transfer;
3. plaintext protected payload;
4. replay use index at/over maximum use count;
5. changed authenticated session between resolution and submission;
6. skipped immediate pre-resolution revocation check;
7. secret plaintext in receipt policy;
8. automatic retry instead of `VERIFY_EXTERNALLY` after ambiguous submission.

### Receipt chain

The four-hop example receipt chain was locally verified for:

- canonical hop order;
- stable packet, operation and payload hashes;
- contiguous hop indexes;
- each receipt hash over its canonical body;
- each `prior_receipt_hash` matching the previous receipt;
- zero secret plaintext;
- zero authority transfer.

A deliberately broken prior-receipt link was detected. This remains local semantic evidence, not hosted CI or physical/runtime proof.

## Review gates

- `RC-01-SCHEMA`: OPEN — schemas committed; hosted JSON-Schema validation evidence not yet observed.
- `RC-02-NEGATIVE-TOPOLOGY`: IMPLEMENTED / LOCAL SEMANTIC PASS — hosted evidence open.
- `RC-03-AUTHORITY`: IMPLEMENTED / LOCAL SEMANTIC PASS — hosted evidence open.
- `RC-04-ENDPOINT-RESOLUTION`: IMPLEMENTED / LOCAL SEMANTIC PASS — same-session + revocation constraints now machine-enforced; hosted evidence open.
- `RC-05-PACKET`: IMPLEMENTED / LOCAL SEMANTIC PASS — runtime packet processing not yet proven.
- `RC-06-RECEIPT-CHAIN`: IMPLEMENTED / LOCAL SEMANTIC PASS — runtime-generated chained receipts not yet proven.
- `RC-07-RUNTIME`: OPEN — requires observed real InTr transitions across all four adjacent boundaries with replayable non-secret receipts.
- `RC-08-REAL-SKAP`: OPEN — no real password/key/API secret may be admitted until review acceptance plus runtime proof establish the sealed credential path.

## Next executable work

1. Add hosted validation that runs the topology validator, packet validator, JSON Schema checks and receipt-chain verifier without granting production authority.
2. Define the SKAP sealed-object storage contract and credential lifecycle (`SEALED`, `ACTIVE`, `ROTATED`, `REVOKED`, `RECOVERY_ONLY`) without placing real credentials into it.
3. Define the endpoint-session proof object consumed immediately before transient credential resolution.
4. Define reverse/return InTr packet and receipt fixtures.
5. Bind packet/receipt persistence into KV continuity storage without making KV secret-resolution authority.
6. Only after review acceptance and runtime transition proof, perform the first owner-authorized real SKAP credential ingress.

## Completion boundary

This goal remains open. Machine-readable source, validators, fixtures, local semantic passes, or durable handoff are not activation. Completion requires hosted validation evidence, review acceptance, observed runtime InTr transitions across every adjacent boundary, replayable non-secret receipt reconstruction, and an owner-authorized real SKAP credential operation with the authority and secret boundaries intact.
