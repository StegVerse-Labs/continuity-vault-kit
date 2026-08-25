# SKAP / InTr Review Candidate Mirror Handoff

Status: HOSTED_VALIDATED_THROUGH_KV_SEALED_READBACK_REAL_OWNER_PROVIDER_SESSION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Goal ID: `SV-KV-SKAP-INTR-001`
Last updated: 2026-08-24T21:25:00-05:00

## Active goal

Prove and activate the canonical credential/transport topology:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

Transport, packet/ciphertext/receipt possession, model output, KV persistence, or key-handle possession does not confer execution, identity, continuity, governance, decryption, credential, or secret-custody authority.

## Hosted-proven layers

- topology, packet/envelope and bidirectional hop-receipt schemas;
- endpoint-session proof binding packet/grant/endpoint/TLS session;
- loopback forward/return transport and full reconstruction;
- actual credential-free Coinbase DNS/TLS/HTTPS traversal to `https://api.coinbase.com/api/v3/brokerage/time`, with redirects denied and no Authorization header/credential material;
- AES-256-GCM + HKDF-SHA256 SKAP cryptographic sealing using synthetic material;
- lifecycle/grant-bound transient resolution, stale-version rejection, rotation/revocation invalidation, immediate revocation recheck and consumed-grant replay denial;
- TVC key-provider interface code with secret bytes confined to an in-process callback;
- owner-authorized synthetic ingress requiring `TRUSTED_INTERACTIVE_EDGE`, mutable plaintext, immediate sealing and buffer overwrite;
- KnowledgeVault persistence of canonical SKAP ciphertext/reference state plus secret-free ingress receipt, with exact hash-verified readback and no KV decryption/resolution authority.

## External Coinbase transport evidence

Implementation:
- `scripts/run_intr_external_endpoint_probe.py` — `fba91f37312216ac8986a5f4f9ff02e8300493d1`
- workflow binding — `8a383bfc03673b99120a4704c9073d949a338ef4`
- hosted run `32800229287` — `SUCCESS`
- artifact `9546225555`
- artifact digest `sha256:cc0aac0e4bb92ebee2a69462c1c01ed57da7bc89add1d9abe6b34200ccb66db6`

This proves a real Coinbase external endpoint can participate in the non-secret InTr path. It does not prove credential-bearing provider authority.

## SKAP cryptographic/lifecycle evidence

Canonical implementation: `skap/crypto_boundary.py`.

Properties:
- AES-256-GCM authenticated encryption;
- HKDF-SHA256 per object/version/context key derivation;
- AAD binds object id, credential version, wrapping policy, purpose and endpoint;
- ciphertext-only sealed output;
- callback-only transient plaintext use and best-effort mutable-buffer wipe;
- `plaintext_persisted=false`;
- `key_material_persisted=false`;
- `authority_transfer=false`.

Canonical lifecycle runtime rejects wrong key, tamper, endpoint/purpose/version/key-authority substitution, stale grants, rotated/revoked credentials, missing immediate revocation recheck and consumed-grant replay.

Full guardrail run `32800446563` completed `SUCCESS` across crypto, lifecycle, KV/InTr persistence, reconstruction, synthetic transport and Coinbase external traversal.

## Owner-authorized ingress evidence

Canonical implementation: `skap/ingress.py`.

Hosted synthetic proof requires owner authorization + explicit authorization reference, accepts only mutable in-memory material from `TRUSTED_INTERACTIVE_EDGE`, seals before return, wipes the supplied buffer, and returns only ciphertext plus a secret-free ingress receipt. Hosted run `32800926029` completed `SUCCESS`.

This is not a real iPhone credential capture or production Coinbase credential ingress.

## RC-17 — KV sealed credential persistence/readback: HOSTED PASS

Implemented:
- `execution/vault_store.py` commit `216a2e1e2858d62826afd057f1651a82e69a5973`;
- `tests/test_skap_kv_persistence.py` commit `948e597347d7039cbd6fb282f82b778ae0ad677a`;
- hosted guardrail binding `998cdfa594b32050ad19b6c5b8ed5da2c5021e99`.

The KV boundary now:
- persists the exact canonical SKAP ciphertext envelope plus secret-free owner-ingress receipt;
- validates object/version/purpose/endpoint and sealed-material hash bindings;
- hash-verifies every stored record on readback;
- reconstructs the exact sealed envelope;
- rejects plaintext, root/wrapping-key material, KV decryption authority, KV secret-resolution authority, Device custody and authority-transfer claims;
- detects stored-record tamper before readback.

Hosted `KV Guardrails` run `32801180017` completed the new `Validate SKAP ciphertext and ingress receipt KV readback` step successfully together with all prior SKAP/InTr gates.

This proves repository-local KnowledgeVault persistence semantics using synthetic sealed material. It does not yet prove a real owner-connected KnowledgeVault write.

## Physical-device and production-key constraint

`CURRENT_USER_IPHONE` remains the only user-operated physical surface. No second machine, shell, SSH session, Linux host or always-on external user-managed host may be required for production activation.

The existing `skap/key_provider.py` `/run/stegverse/...` file provider is a validated implementation/reference boundary only. **It must not become a production requirement that forces the user to operate another machine.** Production SKAP key provisioning remains OPEN and must satisfy the iPhone/StegVerse physical-runtime contract while retaining TV/TVC-only key authority.

## Authority boundaries

- TV/TVC remains credential/secret/token/key authority.
- SKAP provides sealed custody and transient resolution only.
- KV stores ciphertext/reference + non-secret evidence only and has no decryption/resolution authority.
- Device has no durable secret/key custody.
- External Network is transport only.
- exact endpoint/session and current grant/revocation state are mandatory before transient resolution.
- ambiguous native submission state => `VERIFY_EXTERNALLY`, never blind retry.
- model output grants no authority.

## Review gates

```text
RC-01..RC-13 protocol/schema/reconstruction/synthetic transport: HOSTED PASS
RC-14A external non-secret Coinbase endpoint: HOSTED PASS
RC-15A SKAP crypto implementation: HOSTED PASS
RC-15B lifecycle/grant invalidation: HOSTED PASS
RC-15C key-provider code boundary: HOSTED PASS
RC-15D production key provisioning under iPhone-only contract: OPEN
RC-16A owner-ingress code/synthetic proof: HOSTED PASS
RC-16B real owner/iPhone ingress: OPEN
RC-17 KV sealed credential persistence/readback: HOSTED PASS
RC-17B actual connected KnowledgeVault synthetic sealed write/read: OPEN
RC-18 provider-bound credential session: OPEN
RC-19 first bounded provider operation: OPEN
```

## Next executable work

1. Build the iPhone browser-to-SKAP sealed ingress transport so credential plaintext is encrypted before leaving the current-user iPhone and the phone receives no SKAP private/root key.
2. Reuse the existing `stegverse.org` WebAuthn participant surface for owner authorization; do not create a parallel authority surface.
3. Exercise ciphertext-only persistence against the actual connected KnowledgeVault using synthetic material if that surface is accessible, with no real credential/root key.
4. Bind a real sealed Coinbase grant to the already-proven Coinbase TLS/session path.
5. Only after explicit owner authorization and valid production TVC/SKAP key provisioning, admit the first real credential and perform read-only Coinbase permission/fee observation.
6. Then perform the max-$10 post-only maker proof, reconcile, obtain the next authenticated snapshot and repeat.

## Completion boundary

Source/CI/hosted proofs do not equal production activation. Completion requires real owner-authorized iPhone ingress, production SKAP key custody compatible with the no-second-machine rule, real sealed credential state, provider-bound authenticated session proof, authentic Coinbase observation, bounded execution, reconciliation and repeat-loop evidence.
