# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_HOSTED_VALIDATED_EXTERNAL_PROVIDER_AND_SKAP_CRYPTO_PASS_REAL_CREDENTIAL_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24T21:20:00-05:00

## Active goal

Define, validate, persist, reconstruct and ultimately prove the machine-readable protocol:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

`InTr` is the canonical bidirectional interlock/transport relationship between adjacent domains. Transport, packet possession, model output, receipt possession, endpoint proof possession, lifecycle receipt possession, cryptographic ciphertext possession, or KV persistence does not itself confer execution, identity, continuity, governance, decryption, or secret-custody authority.

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

Hosted workflow run `32800229287` completed `SUCCESS`. Retained artifact:

```text
artifact_id: 9546225555
name: skap-intr-coinbase-external-probe-32800229287
digest: sha256:cc0aac0e4bb92ebee2a69462c1c01ed57da7bc89add1d9abe6b34200ccb66db6
```

### Real SKAP cryptographic boundary — HOSTED PASS WITH SYNTHETIC KEY/MATERIAL

Implementation:
- `skap/crypto_boundary.py` initial authenticated sealing commit `e7972e6040e1d9efb2c77120e57097a828889edf`
- fail-closed crypto test suite `tests/test_skap_crypto_boundary.py` at `f8aa3698128f11729d2b179f2be4e95e08a6cc58`
- lifecycle/grant-bound resolution hardening `18638784df38903dd456a01498ceda6594a75eb4`
- runtime rotation/revocation tests `tests/test_skap_crypto_lifecycle_runtime.py` at `d0bbb00e59bb45537e89e31c09d7e6d69c78afd0`
- hosted workflow binding `c7b9c9ad407308b245e3ebd8d482c90d53240c8a`

Cryptographic behavior:
- AES-256-GCM authenticated encryption
- HKDF-SHA256 per-object/version key derivation
- random 256-bit salt and 96-bit nonce per seal operation
- AAD binds object id, credential version, wrapping policy, purpose and endpoint
- root key material is caller-supplied for the operation and is not persisted in the sealed envelope
- sealed envelope records `plaintext_persisted=false`, `key_material_persisted=false`, `authority_transfer=false`
- resolution is callback-only; plaintext is not returned or serialized and the mutable resolution buffer is overwritten after use on a best-effort basis
- implementation explicitly does not claim Python can guarantee elimination of every immutable/runtime temporary allocation

Fail-closed coverage proves rejection of wrong root key, ciphertext tampering, endpoint/purpose/version/AAD substitution, key-authority substitution, non-persistence/authority flag drift and sub-256-bit root material.

Lifecycle-aware resolution additionally requires:
- credential lifecycle = `ACTIVE`
- exact current credential version
- active, unrevoked, unconsumed exact-object grant
- exact purpose and endpoint grant binding
- immediate revocation check = PASS

Runtime tests prove:
1. v1 resolves while ACTIVE.
2. after rotation, old v1 ciphertext + old v1 grant no longer resolve even if physically retained.
3. v2 resolves when ACTIVE/current.
4. stale v1 cannot be revived by merely relabeling lifecycle state ACTIVE because version binding still fails.
5. current v2 stops resolving after lifecycle REVOKED.
6. a revoked, consumed or revocation-unverified grant fails closed.

Hosted `KV Guardrails (Layer + Footer + Emoji + InTr)` run `32800437274` on `c7b9c9ad407308b245e3ebd8d482c90d53240c8a` completed `SUCCESS`. The job shows the SKAP cryptographic boundary, runtime rotation/revocation, KV persistence, reconstruction, synthetic transport, Coinbase external probe, artifact preservation and non-authorizing guard all completed successfully.

This is real cryptographic implementation and hosted runtime proof using synthetic non-production material. It is not yet proof of TV/TVC production root-key custody, owner credential ingress, or a credential-bearing provider session.

## Authority and secret boundary

- TV/TVC remains credential/secret/token authority and evidence.
- SKAP is sealed secret custody; custody does not create identity, continuity, governance or execution authority.
- Cryptographic root-key possession is not delegated to KV, Device, External Network, model output or provider transport.
- KV preserves sealed SKAP metadata plus continuity/replay evidence; KV has no secret-resolution/decryption authority.
- Device is an ephemeral execution/transport edge and does not inherit durable secret custody or continuity authority.
- External Network is transport only and never gains protected plaintext merely by transit.
- Endpoint-bound material stays sealed until intended endpoint/session verification plus grant/lifecycle/revocation revalidation.
- Resolution + native endpoint submission must occur on the same authenticated session.
- Return InTr packets/receipts never carry secret plaintext.
- Model output grants no execution or secret authority.

## Failure dispositions

- wrong boundary / expiry / replay / authority mismatch / endpoint mismatch / revoked credential / stale version / consumed grant / failed immediate revocation check / unauthorized redirect / session mismatch / packet mismatch / grant mismatch / ciphertext authentication failure: `FAIL_CLOSED`
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
- `RC-14B-PROVIDER_BOUND-CREDENTIAL-SESSION`: OPEN — requires an owner-authorized admitted sealed credential grant bound to a verified Coinbase session
- `RC-15A-SKAP-CRYPTO-IMPLEMENTATION`: HOSTED PASS — AES-256-GCM/HKDF, synthetic non-production material
- `RC-15B-SKAP-RUNTIME-LIFECYCLE-INVALIDATION`: HOSTED PASS — rotation/revocation/stale/consumed grant rejection
- `RC-15C-TVC-PRODUCTION-KEY-CUSTODY`: OPEN — production root-key custody/resolution authority must remain TV/TVC only and must not be simulated by repo/Actions secrets
- `RC-16-OWNER-CREDENTIAL-INGRESS`: OPEN — requires owner-authorized ingress with no durable Device plaintext/custody
- `RC-17-FIRST-BOUNDED-PROVIDER-OPERATION`: OPEN

## Cross-repository significance for governed trading

The Coinbase lane now has both an external provider transport proof and a hosted-proven cryptographic SKAP implementation using synthetic material. `StegVerse-Labs/TVC`, `StegVerse-Labs/crypto-bot` and StegFin provider adapters may consume these as prerequisite evidence, but must continue to fail closed on actual credential use until TVC production key custody, owner credential ingress, and RC-14B/RC-17 complete.

## Next executable work

1. Bind SKAP root-key resolution to TV/TVC production authority without storing the root key in GitHub, Actions, KV, Device durable storage or model-visible state.
2. Implement owner-authorized credential ingress so the Device passes plaintext only into the cryptographic boundary transiently and retains only sealed material + non-secret receipt metadata.
3. Bind a sealed Coinbase grant to the already-proven endpoint TLS/session contract and keep transient resolution + native submission on that same authenticated session.
4. Persist only sealed ciphertext/reference + lifecycle/access receipts into the live KnowledgeVault and verify reconstruction without decryption authority.
5. Perform the first owner-authorized read-only Coinbase permission/fee observation before any bounded maker proof operation.

## Completion boundary

This goal remains open. External provider transport and the cryptographic implementation are hosted-proven, but synthetic keys/material do not equal production custody. Completion requires TV/TVC production key authority, owner-authorized ingress, provider-bound credential-session proof, replayable KV evidence, and a bounded real credential operation with all secret and authority boundaries intact.
