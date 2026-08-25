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

`InTr` is the canonical bidirectional interlock/transport relationship between adjacent domains. Transport, packet possession, model output, receipt possession, or KV persistence does not itself confer execution, identity, continuity, governance, decryption, or secret-custody authority.

## Implemented artifacts

### Topology
- `specs/skap-intr-review-candidate.v1.json` — `9ad3038fac16e34f2fc4615bc75e491b21ba311d`
- `schemas/skap-intr-review-candidate.schema.json` — `380ba768196afb391299b2eb50b032cfa4491ad7`
- `scripts/validate_skap_intr_review_candidate.py` — `6ecd9be372fe84ffdf402277901b0e2eb3bb356d`

### Packet / envelope
- `specs/intr-packet-review-candidate.v1.json` — `ba83d378477d1c5058bb80094e136d225763d21f`
- `schemas/intr-packet-review-candidate.schema.json` — introduced `d630e64dab7ffd3731b2622ab0a1a3837a4b6d95`; repaired `5de479f0a8569389900446bc8c6682c51b6ec185`
- `scripts/validate_intr_packet_review_candidate.py` — `9ab2479b01db7b64d0a8852312d0d50007b9998d`

### Per-hop receipts / bidirectional reconstruction
- `schemas/intr-hop-receipt.schema.json` — `559795e32ba8cd4591750fc0c8e813f93ee35b2e`
- `scripts/intr_hop_receipt.py` — `53d34e581f23bfad5b182cda4b6632a94452e9e0`
- forward fixture `examples/intr-hop-receipt-chain.example.json` — `34298042c255a2cac5e2a9ecfb38e99549505e78`
- return fixture `examples/intr-hop-return-receipt-chain.example.json` — `7a193bd7fb87fb3afa2ee88320753b5486b80860`

Forward canonical path:
`SKAP -> KV -> DEVICE -> EXTERNAL_NETWORK -> ENDPOINT`

Return canonical path:
`ENDPOINT -> EXTERNAL_NETWORK -> DEVICE -> KV -> SKAP`

### SKAP sealed-object lifecycle
- `schemas/skap-sealed-object.schema.json` — `bf819eb75bd7615bc03394dc6d58567d75d42b15`
- lifecycle: `SEALED | ACTIVE | ROTATED | REVOKED | RECOVERY_ONLY`
- plaintext persistence forbidden
- KV decryption authority forbidden
- Device secret-custody authority forbidden
- model secret access forbidden
- lifecycle transition evidence timestamps required by state

### Endpoint-session proof
- `schemas/intr-endpoint-session-proof.schema.json` — `1813a85b8ba8665931809f6e4e4b4f001c6cccbe`
- `scripts/validate_skap_endpoint_contracts.py` — `7aec821aeeac34b7e782c387e7ef96fd375ea9b4`
- HTTPS endpoint/session identity is verified before credential resolution
- redirects are not implicitly authorized
- credential resolution and native submission require the same authenticated session
- failed endpoint proof => no resolution + `FAIL_CLOSED`

Local semantic negative tests reject persisted plaintext, missing revocation evidence, KV decryption authority, failed endpoint with resolution enabled, redirects, and disabled same-session binding.

## Hosted validation — exact location

Repository: `StegVerse-Labs/continuity-vault-kit`
Workflow: `KV Guardrails (Layer + Footer + Emoji + InTr)`
File: `.github/workflows/kv-guardrails.yml`
Initial SKAP/InTr integration: `db7a99d65f86b43f28683e06826416d25751120d`
Latest validation wiring: `b6d3b36e920f7b5e15957920297dc8936c71b9a7`

The existing workflow now performs:
- topology + packet JSON Schema validation;
- SKAP sealed-object, endpoint-session-proof and hop-receipt schema-definition checks;
- topology and packet semantic negative tests;
- SKAP lifecycle / endpoint proof semantic negative tests;
- forward and return receipt-chain verification;
- Python compilation;
- explicit non-authorizing checks (`contents: read`, no `contents: write`, no `git push`, no `secrets.` references).

The connected GitHub commit-status accessor currently returns no status records, and its workflow-run accessor exposes only PR-triggered runs. That is neither PASS nor FAIL evidence. Hosted result therefore remains OPEN. Manual inspection location, if needed, is exactly: `StegVerse-Labs/continuity-vault-kit -> Actions -> KV Guardrails (Layer + Footer + Emoji + InTr)` for commit `b6d3b36e...` or a descendant.

## Authority and secret boundary

- SKAP owns sealed secret custody state; custody does not create identity, continuity, governance, or execution authority.
- KV preserves sealed SKAP state and continuity/replay evidence; KV has no secret-resolution/decryption authority.
- Device is an ephemeral execution/transport edge and does not inherit secret custody or continuity authority.
- External Network is transport only and must never hold protected plaintext merely by transit.
- Endpoint-bound material remains sealed until intended endpoint/session verification and grant revalidation including immediate revocation check.
- Resolution + native endpoint submission occur on the same authenticated session.
- Return InTr packets/receipts never carry secret plaintext.
- Model output grants no execution or secret authority.

## Failure dispositions

- wrong boundary: `FAIL_CLOSED`
- expired packet: `FAIL_CLOSED`
- replay detected: `FAIL_CLOSED`
- authority mismatch: `FAIL_CLOSED`
- endpoint mismatch: `FAIL_CLOSED`
- revoked credential: `FAIL_CLOSED`
- redirect outside explicit authorization: `FAIL_CLOSED`
- session changed after endpoint verification: `FAIL_CLOSED`
- ambiguous post-submission state: `VERIFY_EXTERNALLY`

## Review gates

- `RC-01-SCHEMA`: IMPLEMENTED / HOSTED RESULT OPEN
- `RC-02-NEGATIVE-TOPOLOGY`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN
- `RC-03-AUTHORITY`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN
- `RC-04-ENDPOINT-RESOLUTION`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN
- `RC-05-PACKET`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN
- `RC-06-RECEIPT-CHAIN`: IMPLEMENTED / LOCAL PASS / HOSTED RESULT OPEN
- `RC-07-SKAP-LIFECYCLE`: IMPLEMENTED / LOCAL SEMANTIC COVERAGE / HOSTED RESULT OPEN
- `RC-08-BIDIRECTIONAL-INTR`: IMPLEMENTED / FORWARD+RETURN FIXTURES / HOSTED RESULT OPEN
- `RC-09-RUNTIME`: OPEN — requires observed real InTr transitions across all four adjacent boundaries with replayable non-secret receipts
- `RC-10-REAL-SKAP`: OPEN — no real password/key/API secret admitted until review acceptance plus runtime proof

## Next executable work

1. Bind InTr packet and receipt persistence into existing KV execution/continuity storage while explicitly denying KV decryption authority.
2. Add machine-readable SKAP lifecycle transition receipts, including rotation/revocation chain semantics.
3. Add packet-to-endpoint-session-proof binding so the proof is not independently replayable against another packet/operation.
4. Retrieve and inspect an observable hosted `KV Guardrails` conclusion when the connector exposes it; remediate any actual failure.
5. Only after review acceptance and runtime proof, perform first owner-authorized real SKAP credential ingress.

## Completion boundary

This goal remains open. Source, schemas, validators, fixtures, local semantic passes, workflow installation, folder existence, or durable handoff are not activation. Completion requires observable hosted validation, review acceptance, runtime InTr transitions across every adjacent boundary, replayable non-secret reconstruction, and an owner-authorized real SKAP credential operation with all authority and secret boundaries intact.
