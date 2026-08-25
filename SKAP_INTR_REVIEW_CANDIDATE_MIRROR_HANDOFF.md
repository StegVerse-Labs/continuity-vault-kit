# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_HOSTED_VALIDATED_EXTERNAL_PROVIDER_SKAP_CRYPTO_TVC_KEY_PROVIDER_AND_OWNER_INGRESS_PASS_KV_PERSISTENCE_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24T21:35:00-05:00

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
- KV metadata-only execution persistence/reconstruction
- complete synthetic round-trip reconstruction
- loopback TCP forward/return transport
- real credential-free Coinbase TLS/HTTPS endpoint traversal
- AES-256-GCM + HKDF-SHA256 SKAP sealing/resolution with synthetic non-production material
- lifecycle/grant-bound decryption with runtime rotation/revocation/stale/consumed-grant invalidation
- TVC-resident ephemeral root-key provider boundary
- transient owner-authorized ingress contract with synthetic non-production bytes

## External provider-bound non-secret transport

Provider: Coinbase  
Endpoint: `https://api.coinbase.com/api/v3/brokerage/time`

Implementation:
- `scripts/run_intr_external_endpoint_probe.py` — `fba91f37312216ac8986a5f4f9ff02e8300493d1`
- workflow binding — `8a383bfc03673b99120a4704c9073d949a338ef4`
- hosted run `32800229287` = `SUCCESS`

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
- hosted run `32800437274` on `c7b9c9ad407308b245e3ebd8d482c90d53240c8a` = `SUCCESS`

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

## TVC resident root-key provider boundary

Implementation:
- `skap/key_provider.py` — `8150c451802c68e2219f1d0fcf027217f59bbb42`
- provider-facing crypto wrappers — `4e8cbcc7c9b9efda0dc228f6c7c45f5d15aa80f8`
- provider tests — `15744dc7cfcead5b4ba05a6fb88d6eb381a9f32c`
- hosted workflow binding — `77e92fd3281a02283f36aea33c48156130b5e548`
- hosted `KV Guardrails` run `32800687645` = `SUCCESS`

Production key-provider policy follows the existing TVC resident pattern:

```text
/run/stegverse/tv-tvc-credentials/<credential-object>
```

The provider confines root-key lookup to that TVC ephemeral root, uses read-only/no-follow protections where available, requires a regular root-owned non-group/world-readable file with exactly 256 bits of material, exposes key bytes only to an in-process callback, wipes its mutable copy afterward, and never creates/persists/rotates/exports/logs the key. Provider authority is bound into the ciphertext envelope.

This proves the code path that can consume TV/TVC-resident ephemeral root-key material without returning raw key bytes to callers. It does not prove production key provisioning.

## Owner-authorized credential ingress — HOSTED PASS WITH SYNTHETIC MATERIAL

Implementation:
- `skap/ingress.py` — `896e1a80b64e2fd2b51fa09b71ffaea9d4ba61e4`
- tests `tests/test_skap_owner_ingress.py` — `9ad9753ee4ecdb975c8c39db766e48f1542a8b20`
- hosted workflow binding — `5a5c6f6d10290ed8d09f318292ef38d3b6b44ecd`
- hosted `KV Guardrails` run `32800926029` = `SUCCESS`

Ingress properties:
- requires `owner_authorized=true` plus an explicit authorization reference before invoking the key provider
- accepts only a mutable in-memory `bytearray` from `TRUSTED_INTERACTIVE_EDGE`
- rejects source classes `ARGV`, `ENVIRONMENT`, `FILE`, `NETWORK` and `MODEL_OUTPUT`
- rejects immutable `bytes`/`str` inputs because this boundary cannot wipe them
- seals immediately through the key-provider API
- overwrites the caller-provided mutable plaintext buffer after sealing
- returns only sealed material and a secret-free receipt
- receipt records `plaintext_persisted=false`, `device_durable_secret_custody=false`, `kv_decryption_authority=false`, `model_secret_access=false`, `authority_transfer=false`
- tests prove the plaintext literal does not occur in the serialized sealed-envelope/receipt output

This is a real ingress implementation and hosted validation using explicitly synthetic non-production bytes. It does **not** constitute owner authorization for any real credential, real Device UI capture, or production credential ingress.

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
- `RC-16A-OWNER-INGRESS-CODE-AND-SYNTHETIC-PROOF`: `HOSTED PASS`
- `RC-16B-REAL-OWNER-INGRESS`: `OPEN`
- `RC-17-KV-SEALED-CREDENTIAL-PERSISTENCE-READBACK`: `OPEN`
- `RC-18-PROVIDER-BOUND-CREDENTIAL-SESSION`: `OPEN`
- `RC-19-FIRST-BOUNDED-PROVIDER-OPERATION`: `OPEN`

## Next executable work

1. Implement the SKAP-specific KnowledgeVault ciphertext/reference + ingress/lifecycle receipt persistence boundary and prove read-back/reconstruction using synthetic sealed material only.
2. Exercise that persistence against the actual connected KnowledgeVault without placing any real credential or production root key there.
3. Bind TVC runtime provisioning to the SKAP root-key provider without introducing GitHub/Actions/KV/Device/model key authority.
4. Bind a sealed Coinbase grant to the already-proven Coinbase TLS/session path.
5. Only after explicit owner authorization and production TVC key provisioning, admit the first real credential and perform a read-only Coinbase permission/fee observation before any bounded effect.

## Completion boundary

This goal remains open. Hosted external transport, cryptography, lifecycle invalidation, TVC-resident key-provider code and synthetic owner-ingress proof do not equal production credential activation. Completion requires real TVC root-key provisioning, actual owner-authorized credential ingress, sealed KV persistence/reconstruction, provider-bound credential-session proof, and a bounded real credential operation with all authority/secret boundaries intact.
