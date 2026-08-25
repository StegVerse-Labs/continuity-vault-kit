# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_PENDING_REVIEW_AND_RUNTIME_VALIDATION
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24T20:34:00-05:00

## Active goal

Define, validate, persist, reconstruct and ultimately prove the machine-readable protocol:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

`InTr` is the canonical bidirectional interlock/transport relationship between adjacent domains. Transport, packet possession, model output, receipt possession, endpoint proof possession, lifecycle receipt possession, or KV persistence does not itself confer execution, identity, continuity, governance, decryption, or secret-custody authority.

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

Forward: `SKAP -> KV -> DEVICE -> EXTERNAL_NETWORK -> ENDPOINT`
Return: `ENDPOINT -> EXTERNAL_NETWORK -> DEVICE -> KV -> SKAP`

### SKAP sealed-object lifecycle
- `schemas/skap-sealed-object.schema.json` — `bf819eb75bd7615bc03394dc6d58567d75d42b15`
- lifecycle: `SEALED | ACTIVE | ROTATED | REVOKED | RECOVERY_ONLY`
- plaintext persistence, KV decryption authority, Device secret-custody authority, and model secret access are forbidden

### SKAP lifecycle transition receipts
- `schemas/skap-lifecycle-transition-receipt.schema.json` — `126b22c4840fe37c43d5fde5056101d5a0a19d24`
- rotation requires outstanding grant invalidation and `NO_NEW_GRANTS` for the superseded version
- revocation requires outstanding grant invalidation and `BLOCK_ALL_RESOLUTION`
- transition receipts are prior-hash chained, secret-free and non-authorizing
- semantic chain validation is implemented in `scripts/validate_skap_endpoint_contracts.py` at `0cd6ac46ff202800b0d0d157867565b19033477f`

### Endpoint-session proof
- `schemas/intr-endpoint-session-proof.schema.json` — endpoint binding hardening `25082993d6e3b70acf3fba21f8598661b231c184`
- proof is bound to exact `packet_id`, `packet_hash`, `operation_hash`, `credential_grant_hash`, authorized endpoint and `tls_session_binding_hash`
- redirects are not implicitly authorized
- endpoint/session identity is verified before credential resolution
- immediate revocation recheck is required before resolution
- transient credential resolution and native submission require the same authenticated session
- failed proof => no resolution + `FAIL_CLOSED`
- semantic binding substitution tests are in `scripts/validate_skap_endpoint_contracts.py` — `0cd6ac46ff202800b0d0d157867565b19033477f`

### KV persistence binding
- `execution/vault_store.py` — InTr binding `cb58f7baedfc23854d14076bb793ea250d6743b8`
- `tests/test_vault_store.py` — persistence regression `a9ee0279dea395e1bda00a858e799fcf368c67bd`

InTr packets persist as metadata under `_System/Execution/Extensions` and hop receipts under `_System/Execution/Receipts`. The store rejects protected plaintext, packet/receipt authority transfer, KV decryption authority, KV secret-resolution authority and existing forbidden credential material. Persistence is continuity/replay custody only.

## Hosted validation — exact location

Repository: `StegVerse-Labs/continuity-vault-kit`
Workflow: `KV Guardrails (Layer + Footer + Emoji + InTr)`
File: `.github/workflows/kv-guardrails.yml`
Initial SKAP/InTr integration: `db7a99d65f86b43f28683e06826416d25751120d`
Lifecycle/return-path wiring: `b6d3b36e920f7b5e15957920297dc8936c71b9a7`
KV persistence regression target: `64cd52fe94205d3b9fb801500a8da6d80b497136`
Current validation definition including lifecycle-transition schema and endpoint binding semantics: `61baffc2b284207e7055c2d4063da15ab63df6b5`

The lane validates topology/packet schemas, SKAP sealed-object schema, lifecycle-transition receipt schema, endpoint-session-proof schema, hop-receipt schema, semantic negative tests, forward and return receipt chains, KV persistence regression tests, Python compilation and explicit non-authorizing workflow properties (`contents: read`, no `contents: write`, no `git push`, no `secrets.` references).

Hosted conclusion remains distinct from source implementation and must be retrieved for `61baffc2...` or a descendant before any hosted-pass claim.

## Cross-repository credential dependency significance

TVC now publishes the caller requirement that third-party credentials target InTr transport and SKAP custody. A machine-readable dependency registry exists in `StegVerse-Labs/TVC` at `contracts/third-party-credential-intr-skap-dependencies.v1.json` (`58710d6d3980b96831537e3c505f6cf54a9d98c5`). Known dependent lanes include GitHub heartbeat dispatch, Site/Cloudflare rendezvous, Coinbase governed trading, TVC private-source read/StegMusic, and portable artifact publication.

This means SKAP/InTr runtime readiness is a shared prerequisite for multiple third-party provider workflows, not an isolated KnowledgeVault feature.

## Authority and secret boundary

- TV/TVC remains credential/secret/token authority and evidence.
- SKAP owns target sealed secret custody state; custody does not create identity, continuity, governance, or execution authority.
- KV preserves sealed SKAP metadata plus continuity/replay evidence; KV has no secret-resolution or decryption authority.
- Device is an ephemeral execution/transport edge and does not inherit secret custody or continuity authority.
- External Network is transport only and never receives protected plaintext merely by transit.
- Endpoint-bound material remains sealed until intended endpoint/session verification and grant/revocation revalidation.
- Resolution + native endpoint submission occur on the same authenticated session.
- Return InTr packets/receipts never carry secret plaintext.
- Model output grants no execution or secret authority.

## Failure dispositions

- wrong boundary / expiry / replay / authority mismatch / endpoint mismatch / revoked credential / unauthorized redirect / session binding mismatch / packet binding mismatch / grant binding mismatch: `FAIL_CLOSED`
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
- `RC-09-KV-PERSISTENCE`: IMPLEMENTED / REGRESSION TESTS WIRED / HOSTED RESULT OPEN
- `RC-10-LIFECYCLE-TRANSITION-RECEIPTS`: IMPLEMENTED / SEMANTIC CHAIN COVERAGE / HOSTED RESULT OPEN
- `RC-11-ENDPOINT-PACKET-GRANT-SESSION-BINDING`: IMPLEMENTED / NEGATIVE SUBSTITUTION COVERAGE / HOSTED RESULT OPEN
- `RC-12-END-TO-END-RECONSTRUCTION`: OPEN — requires one test spanning persisted packet + forward receipts + endpoint proof + return receipts + lifecycle evidence
- `RC-13-RUNTIME`: OPEN — requires observed real InTr transitions across all four adjacent boundaries with replayable non-secret receipts
- `RC-14-REAL-SKAP`: OPEN — no real password/key/API secret admitted until review acceptance plus runtime proof

## Next executable work

1. Add end-to-end reconstruction test spanning KV persisted packet + forward receipt chain + exact endpoint proof + return receipt chain + applicable lifecycle receipt chain.
2. Propagate the TVC InTr/SKAP receipt requirement into provider-specific consumers beginning with Site/Cloudflare and Coinbase trading lanes, without creating duplicate credential authority.
3. Retrieve and inspect an observable hosted `KV Guardrails` conclusion for `61baffc2...` or descendant; remediate any actual failure.
4. Prove a non-secret synthetic runtime InTr traversal across every adjacent boundary before admitting any real credential.
5. Only after review acceptance and runtime proof, perform first owner-authorized real SKAP credential ingress.

## Completion boundary

This goal remains open. Source, schemas, validators, fixtures, local semantic passes, workflow installation, folder existence, dependency registration, or durable handoff are not activation. Completion requires observable hosted validation, review acceptance, runtime InTr transitions across every adjacent boundary, replayable non-secret reconstruction, and an owner-authorized real SKAP credential operation with all authority and secret boundaries intact.
