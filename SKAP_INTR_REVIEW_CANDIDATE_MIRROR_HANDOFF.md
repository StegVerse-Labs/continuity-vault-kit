# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_HOSTED_VALIDATED_EXTERNAL_PROVIDER_PROBE_PASS_REAL_SKAP_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24T21:15:00-05:00

## Active goal

Define, validate, persist, reconstruct and ultimately prove the machine-readable protocol:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

`InTr` is the canonical bidirectional interlock/transport relationship between adjacent domains. Transport, packet possession, model output, receipt possession, endpoint proof possession, lifecycle receipt possession, or KV persistence does not itself confer execution, identity, continuity, governance, decryption, or secret-custody authority.

## Implemented machine layers

### Topology
- `specs/skap-intr-review-candidate.v1.json`
- `schemas/skap-intr-review-candidate.schema.json`
- `scripts/validate_skap_intr_review_candidate.py`

### Packet / envelope
- `specs/intr-packet-review-candidate.v1.json`
- `schemas/intr-packet-review-candidate.schema.json`
- `scripts/validate_intr_packet_review_candidate.py`

### Bidirectional hop receipts
- `schemas/intr-hop-receipt.schema.json`
- `scripts/intr_hop_receipt.py`

Forward: `SKAP -> KV -> DEVICE -> EXTERNAL_NETWORK -> ENDPOINT`
Return: `ENDPOINT -> EXTERNAL_NETWORK -> DEVICE -> KV -> SKAP`

### SKAP sealed-object lifecycle
- `schemas/skap-sealed-object.schema.json`
- lifecycle: `SEALED | ACTIVE | ROTATED | REVOKED | RECOVERY_ONLY`
- plaintext persistence, KV decryption authority, Device secret-custody authority, and model secret access are forbidden

### Lifecycle transition receipts
- `schemas/skap-lifecycle-transition-receipt.schema.json`
- rotation invalidates outstanding grants and applies `NO_NEW_GRANTS` to the superseded version
- revocation invalidates outstanding grants and applies `BLOCK_ALL_RESOLUTION`
- prior-hash chained, secret-free and non-authorizing

### Endpoint-session proof
- `schemas/intr-endpoint-session-proof.schema.json`
- binds exact packet id/hash, operation hash, credential-grant hash, authorized endpoint and TLS-session binding hash
- redirect not implicitly permitted
- endpoint/session verification before credential resolution
- immediate revocation recheck before resolution
- same authenticated session required for transient resolution + native submission
- failed proof => no resolution + `FAIL_CLOSED`

### KV persistence / reconstruction
- `execution/vault_store.py`
- `tests/test_vault_store.py`
- InTr packets persist under `_System/Execution/Extensions`
- hop receipts persist under `_System/Execution/Receipts`
- KV rejects protected plaintext, packet/receipt authority transfer, KV decryption authority, KV secret-resolution authority and forbidden credential material

### End-to-end reconstruction
- `tests/test_skap_intr_reconstruction.py`
- proves synthetic lifecycle activation -> KV packet persistence -> forward receipt chain -> exact endpoint proof -> return receipt chain -> KV read-back
- proves endpoint proof cannot be reused under substituted packet hash

### Synthetic non-secret transport
- `scripts/run_intr_synthetic_runtime.py`
- actual TCP socket I/O on loopback for all canonical forward and return adjacent boundaries
- evidence class `LOOPBACK_TCP_SYNTHETIC_NON_SECRET`
- no real credential, no third-party endpoint, no production runtime claim

### External provider-bound non-secret transport — HOSTED PASS
- `scripts/run_intr_external_endpoint_probe.py` introduced at `fba91f37312216ac8986a5f4f9ff02e8300493d1`
- guardrail workflow binding at `8a383bfc03673b99120a4704c9073d949a338ef4`
- provider: Coinbase
- endpoint: `https://api.coinbase.com/api/v3/brokerage/time`
- performs real DNS/TLS/HTTPS contact to the intended provider endpoint
- uses default trusted TLS verification + hostname verification
- records peer certificate hash, peer IP, TLS version/cipher, session-binding hash, response hash/status
- sends no Authorization header and no credential material
- rejects redirects
- preserves sealed/no-secret/no-authority-transfer semantics
- completes internal forward InTr hops, actual `EXTERNAL_NETWORK -> ENDPOINT`, and return InTr receipt traversal
- does not claim credential resolution, SKAP custody, trading authority or production credential operation

Hosted workflow `KV Guardrails (Layer + Footer + Emoji + InTr)` run `32800229287` completed `SUCCESS`. The external endpoint traversal step and retained-artifact step both passed. Retained artifact:

```text
artifact_id: 9546225555
name: skap-intr-coinbase-external-probe-32800229287
digest: sha256:cc0aac0e4bb92ebee2a69462c1c01ed57da7bc89add1d9abe6b34200ccb66db6
```

This proves an actual external Coinbase endpoint can participate in the non-secret InTr transport path under the current hosted validation environment. It does not prove real SKAP secret custody or a credential-bearing Coinbase session.

## Authority and secret boundary

- TV/TVC remains credential/secret/token authority and evidence.
- SKAP is target sealed secret custody; custody does not create identity, continuity, governance or execution authority.
- KV preserves sealed SKAP metadata plus continuity/replay evidence; KV has no secret-resolution/decryption authority.
- Device is an ephemeral execution/transport edge and does not inherit secret custody or continuity authority.
- External Network is transport only and never gains protected plaintext merely by transit.
- Endpoint-bound material stays sealed until intended endpoint/session verification and grant/revocation revalidation.
- Resolution + native endpoint submission occur on the same authenticated session.
- Return InTr packets/receipts never carry secret plaintext.
- Model output grants no execution or secret authority.

## Failure dispositions

- wrong boundary / expiry / replay / authority mismatch / endpoint mismatch / revoked credential / unauthorized redirect / session mismatch / packet mismatch / grant mismatch: `FAIL_CLOSED`
- ambiguous post-submission state: `VERIFY_EXTERNALLY`

## Review gates

- `RC-01-SCHEMA`: HOSTED PASS
- `RC-02-NEGATIVE-TOPOLOGY`: HOSTED PASS
- `RC-03-AUTHORITY`: HOSTED PASS
- `RC-04-ENDPOINT-RESOLUTION`: HOSTED PASS
- `RC-05-PACKET`: HOSTED PASS
- `RC-06-RECEIPT-CHAIN`: HOSTED PASS
- `RC-07-SKAP-LIFECYCLE`: HOSTED PASS
- `RC-08-BIDIRECTIONAL-INTR`: HOSTED PASS
- `RC-09-KV-PERSISTENCE`: HOSTED PASS
- `RC-10-LIFECYCLE-TRANSITION-RECEIPTS`: HOSTED PASS
- `RC-11-ENDPOINT-PACKET-GRANT-SESSION-BINDING`: HOSTED PASS
- `RC-12-END-TO-END-RECONSTRUCTION`: HOSTED PASS
- `RC-13-SYNTHETIC-TRANSPORT`: HOSTED PASS
- `RC-14A-EXTERNAL-NON_SECRET-PROVIDER-PROBE`: HOSTED PASS — real Coinbase TLS/HTTPS endpoint traversal, no credential
- `RC-14B-PROVIDER_BOUND-CREDENTIAL-SESSION`: OPEN — requires an admitted sealed credential grant bound to the verified Coinbase session
- `RC-15-REAL-SKAP`: OPEN — real cryptographic sealed custody/resolution not yet activated

## Cross-repository significance for governed trading

The Coinbase trade lane no longer lacks a demonstrated external provider transport path. `StegVerse-Labs/TVC` and `StegVerse-Labs/crypto-bot` may now treat the non-secret external-network/endpoint portion as hosted-proven evidence, while continuing to fail closed on actual credential use until RC-14B + RC-15 complete.

## Next executable work

1. Implement real SKAP sealed-object cryptographic wrapping/unwrapping behind the existing lifecycle/authority schemas using non-production synthetic material first.
2. Prove runtime rotation and revocation invalidate outstanding grants.
3. Bind the existing Coinbase external TLS/session observation into a credential-aware endpoint-session proof only after a real sealed grant exists.
4. Add owner-authorized iPhone credential ingress without durable Device custody.
5. Perform first real Coinbase permission/fee observation, then the bounded maker proof operation.

## Completion boundary

This goal remains open. External provider transport is now hosted-proven without credentials. Completion still requires real sealed SKAP cryptographic custody/resolution, provider-bound credential-session proof, replayable KV evidence, and an owner-authorized real credential operation with all authority and secret boundaries intact.
