# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_HOSTED_VALIDATED_EXTERNAL_PROVIDER_SKAP_CRYPTO_AND_TVC_KEY_PROVIDER_PASS_OWNER_INGRESS_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24T21:25:00-05:00

## Active goal

Define, validate, persist, reconstruct and ultimately prove:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

Transport, packet/ciphertext/receipt possession, model output, KV persistence, or key-handle possession does not itself confer execution, identity, continuity, governance, decryption, credential, or secret-custody authority.

## Hosted-proven protocol layers

- canonical InTr topology and packet envelope
- bidirectional per-hop receipt chains
- SKAP sealed-object lifecycle and transition receipts
- exact packet/grant/endpoint/TLS-session proof binding
- KV metadata-only persistence and reconstruction
- complete synthetic round-trip reconstruction
- loopback TCP forward/return transport
- real credential-free Coinbase TLS/HTTPS endpoint traversal
- AES-256-GCM + HKDF-SHA256 SKAP sealing/resolution using synthetic non-production material
- lifecycle/grant-bound decryption with runtime rotation/revocation/stale/consumed-grant invalidation
- TVC-resident ephemeral root-key provider boundary

## External provider-bound non-secret transport

Provider: Coinbase  
Endpoint: `https://api.coinbase.com/api/v3/brokerage/time`

Implementation:
- `scripts/run_intr_external_endpoint_probe.py` — `fba91f37312216ac8986a5f4f9ff02e8300493d1`
- workflow binding — `8a383bfc03673b99120a4704c9073d949a338ef4`

Hosted run `32800229287` completed `SUCCESS`.

Retained evidence:

```text
artifact_id: 9546225555
name: skap-intr-coinbase-external-probe-32800229287
digest: sha256:cc0aac0e4bb92ebee2a69462c1c01ed57da7bc89add1d9abe6b34200ccb66db6
```

The probe performs actual DNS/TLS/HTTPS contact, verifies trusted TLS + hostname, records only non-secret peer/session/response hashes and metadata, sends no Authorization header, rejects redirects, and preserves the forward/return InTr receipt path. It proves external transport, not credential-bearing provider authority.

## SKAP cryptographic boundary

Implementation:
- `skap/crypto_boundary.py` initial seal/resolve — `e7972e6040e1d9efb2c77120e57097a828889edf`
- fail-closed crypto tests — `f8aa3698128f11729d2b179f2be4e95e08a6cc58`
- lifecycle/grant resolution gate — `18638784df38903dd456a01498ceda6594a75eb4`
- lifecycle runtime tests — `d0bbb00e59bb45537e89e31c09d7e6d69c78afd0`
- provider-bound caller API — `4e8cbcc7c9b9efda0dc228f6c7c45f5d15aa80f8`

Properties:
- AES-256-GCM authenticated encryption
- HKDF-SHA256 object/version/context key derivation
- random 256-bit salt + 96-bit nonce per seal
- AAD binds object id, credential version, wrapping policy, purpose and endpoint
- sealed output contains ciphertext/reference metadata only
- `plaintext_persisted=false`
- `key_material_persisted=false`
- `authority_transfer=false`
- callback-only plaintext consumption with best-effort mutable-buffer wipe
- wrong key, ciphertext tamper, AAD/endpoint/purpose/version/key-authority substitution fail closed

Runtime resolution additionally requires lifecycle `ACTIVE`, exact current version, active/unrevoked/unconsumed grant, exact purpose/endpoint/object binding, and immediate revocation check PASS.

Hosted run `32800437274` on `c7b9c9ad407308b245e3ebd8d482c90d53240c8a` completed `SUCCESS`, including crypto tests, rotation/revocation proof, reconstruction and Coinbase external probe.

## TVC resident root-key provider boundary

Implementation:
- `skap/key_provider.py` — `8150c451802c68e2219f1d0fcf027217f59bbb42`
- provider-facing crypto wrappers — `4e8cbcc7c9b9efda0dc228f6c7c45f5d15aa80f8`
- provider tests — `15744dc7cfcead5b4ba05a6fb88d6eb381a9f32c`
- hosted workflow binding — `77e92fd3281a02283f36aea33c48156130b5e548`

Production key-provider policy follows the already-existing TVC resident pattern:

```text
/run/stegverse/tv-tvc-credentials/<credential-object>
```

The provider:
- requires an absolute path under that TVC root
- opens read-only with `O_NOFOLLOW` when available
- requires a regular root-owned file
- rejects group/world permissions
- requires exactly 256-bit root material
- exposes the key only to an in-process callback
- wipes its mutable key copy afterward
- never creates, persists, rotates, exports or logs the key
- binds the provider authority reference into the sealed ciphertext envelope

Hosted `KV Guardrails` run `32800687645` on `77e92fd3281a02283f36aea33c48156130b5e548` completed `SUCCESS`, including the TVC resident key-provider tests and every previously proven SKAP/InTr layer.

This proves the code path that can consume TV/TVC-resident ephemeral root-key material without returning raw key bytes to callers. It does **not** prove that a production SKAP root key has been provisioned into the TVC resident runtime.

## Authority boundaries

- TV/TVC remains credential/secret/token and production root-key authority.
- SKAP provides sealed custody and transient cryptographic use; custody does not create execution/governance/identity/continuity authority.
- KV preserves ciphertext/reference + non-secret lifecycle/access/continuity evidence only; KV has no decryption authority.
- Device has no durable secret custody.
- External Network is transport only.
- Endpoint plaintext use is permitted only after exact endpoint/session/grant/lifecycle/revocation verification and must remain on that authenticated session.
- Return InTr evidence carries no secret plaintext.
- model output grants no authority.

## Review gates

- RC-01 through RC-13 protocol/schema/reconstruction/synthetic transport: `HOSTED PASS`
- `RC-14A-EXTERNAL-NON_SECRET-PROVIDER-PROBE`: `HOSTED PASS`
- `RC-14B-PROVIDER_BOUND-CREDENTIAL-SESSION`: `OPEN`
- `RC-15A-SKAP-CRYPTO-IMPLEMENTATION`: `HOSTED PASS`
- `RC-15B-SKAP-RUNTIME-LIFECYCLE-INVALIDATION`: `HOSTED PASS`
- `RC-15C-TVC-RESIDENT-KEY-PROVIDER-CODE`: `HOSTED PASS`
- `RC-15D-TVC-PRODUCTION-KEY-PROVISIONING`: `OPEN`
- `RC-16-OWNER-CREDENTIAL-INGRESS`: `OPEN`
- `RC-17-KV-SEALED-CREDENTIAL-PERSISTENCE-READBACK`: `OPEN`
- `RC-18-FIRST-BOUNDED-PROVIDER-OPERATION`: `OPEN`

## Next executable work

1. Bind TVC runtime provisioning to the SKAP root-key provider without introducing GitHub/Actions/KV/Device/model key authority.
2. Implement owner-authorized credential ingress: Device plaintext enters only the resident cryptographic callback, then disappears; only ciphertext + non-secret receipt metadata may leave.
3. Persist the resulting sealed SKAP object/reference and lifecycle/access receipts in the live KnowledgeVault; verify read-back/reconstruction without decryption authority.
4. Bind a sealed Coinbase grant to the already-proven Coinbase TLS/session path.
5. Perform the first owner-authorized read-only Coinbase permission/fee observation before any maker proof operation.

## Completion boundary

This goal remains open. Hosted external transport, cryptography, lifecycle invalidation, and TVC-resident key-provider code do not equal production credential activation. Completion requires real TVC root-key provisioning, owner-authorized ingress, sealed KV persistence/reconstruction, provider-bound credential-session proof, and a bounded real credential operation with all authority/secret boundaries intact.
