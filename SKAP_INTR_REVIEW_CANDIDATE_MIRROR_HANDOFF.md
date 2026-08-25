# SKAP / InTr Review Candidate Mirror Handoff

Status: HOSTED_VALIDATED_THROUGH_CONNECTED_KV_SEALED_READBACK_REAL_OWNER_PROVIDER_SESSION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Goal ID: `SV-KV-SKAP-INTR-001`
Last updated: 2026-08-25T02:40:00Z

## Active goal

Prove and activate the canonical credential/transport topology:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

Transport, packet/ciphertext/receipt possession, model output, KV persistence, or key-handle possession does not confer execution, identity, continuity, governance, decryption, credential, or secret-custody authority.

## Proven layers

- topology, packet/envelope and bidirectional hop-receipt schemas: HOSTED PASS;
- endpoint-session proof binding packet/grant/endpoint/TLS session: HOSTED PASS;
- loopback forward/return transport and full reconstruction: HOSTED PASS;
- real credential-free Coinbase DNS/TLS/HTTPS traversal to `https://api.coinbase.com/api/v3/brokerage/time`: HOSTED PASS;
- AES-256-GCM + HKDF-SHA256 SKAP sealing/resolution using synthetic material: HOSTED PASS;
- lifecycle/grant-bound resolution, stale-version rejection, rotation/revocation invalidation and consumed-grant replay denial: HOSTED PASS;
- TVC key-provider code boundary: HOSTED PASS;
- owner-authorized synthetic ingress requiring mutable in-memory `TRUSTED_INTERACTIVE_EDGE` material and immediate buffer wipe: HOSTED PASS;
- repository-local KV sealed-object persistence/readback: HOSTED PASS;
- actual connected KnowledgeVault synthetic sealed write/read: PASS.

## External Coinbase transport evidence

- `scripts/run_intr_external_endpoint_probe.py` — `fba91f37312216ac8986a5f4f9ff02e8300493d1`
- hosted run `32800229287` — `SUCCESS`
- retained artifact `9546225555`
- digest `sha256:cc0aac0e4bb92ebee2a69462c1c01ed57da7bc89add1d9abe6b34200ccb66db6`

No Authorization header or credential material is sent by the probe. Redirects are denied. This proves external InTr transport, not credential-bearing authority.

## SKAP cryptographic/lifecycle evidence

Canonical implementation: `skap/crypto_boundary.py`.

Properties include AES-256-GCM authenticated encryption, HKDF-SHA256 per-object/version/context key derivation, AAD binding of object/version/policy/purpose/endpoint, ciphertext-only output, callback-only plaintext consumption and best-effort mutable-buffer wiping.

Runtime resolution requires lifecycle `ACTIVE`, exact current version, active/unrevoked/unconsumed grant, exact object/purpose/endpoint binding and immediate revocation recheck PASS.

Hosted run `32800437274` completed `SUCCESS` for crypto, lifecycle invalidation, reconstruction and the external Coinbase probe.

## TVC key-provider boundary

- `skap/key_provider.py` — `8150c451802c68e2219f1d0fcf027217f59bbb42`
- provider-facing crypto wrappers — `4e8cbcc7c9b9efda0dc228f6c7c45f5d15aa80f8`
- provider tests — `15744dc7cfcead5b4ba05a6fb88d6eb381a9f32c`
- hosted run `32800687645` — `SUCCESS`

The validated `/run/stegverse/tv-tvc-credentials/...` provider is a reference/runtime boundary only and must not force the owner to operate a second machine. Production key provisioning remains open under the iPhone-only physical-runtime constraint.

## Owner ingress evidence

Canonical implementation: `skap/ingress.py`.

It rejects argv/env/file/network/model-output source classes, requires owner authorization before key-provider access, accepts only mutable in-memory trusted-edge input, seals immediately and wipes the supplied buffer. Hosted run `32800926029` completed `SUCCESS`.

This is synthetic proof only; real owner/iPhone credential ingress remains open.

## RC-17 repository-local sealed persistence/readback

- `execution/vault_store.py` — `216a2e1e2858d62826afd057f1651a82e69a5973`
- `tests/test_skap_kv_persistence.py` — `948e597347d7039cbd6fb282f82b778ae0ad677a`
- hosted binding — `998cdfa594b32050ad19b6c5b8ed5da2c5021e99`
- hosted run `32801180017`: PASS for SKAP ciphertext + ingress receipt KV readback.

## RC-17B connected KnowledgeVault sealed persistence/readback — PASS

Canonical storage layout added at `specs/skap-kv-storage-layout.v1.json`, commit `c7880b2a31f71a1f069a4f510e9977c840415369`.

Actual connected KnowledgeVault now contains:

```text
_Vault/                         1xNvbptiLxHc0ZfxAu0v8IuPVmaZoyYyp
  SKAP/                         1Mc3WXasLM8JLqplEl1ZLIXLIWTO4zp6O
    Sealed/                     1zoFRW2dywVan8d8NhdxbedvbERDZEzDz
    Lifecycle/                  1DwpsezAOBi-wWBbsa3sUR2K_xcz9tcQF
    Receipts/                   12Z-0BIxRroICYeUr2Bl8M2lHVj0P3BXU
    Revocations/                1cGgKzd0wgOmGARU4-1Ewf8sq-RVBreIW
```

Synthetic-only records persisted as unconverted `text/plain`:

- `Sealed/rc17-synthetic-coinbase-v1.sealed.json` — `1mVRvXIfx-a_iqVEBLuoy-wR_LK38MjR7`
- `Sealed/rc17-synthetic-coinbase-v1.object.json` — `1Pzrj3TIwJRgPO6BtDeVCGdvMnU_9f2kJ`
- `Lifecycle/rc17-synthetic-coinbase-v1.lifecycle.json` — `1i0cOBoc8P9E1TX4z4ax-bfVB0aYj5yU1`
- `Receipts/rc17-synthetic-coinbase-v1.ingress.json` — `1kpb6lj1LqlL2-W1yAyVp6s9SY0bZzyo-`

Connected-Drive readback recomputed the exact sealed material hash:

`sha256:3e00a8d61eca1df510132d3b82624b148aca6f4f4027960251dc49251a5960bc`

The persisted object references that exact hash and recomputes to:

`sha256:2208e31d8ba72b10e840c7ff3ac17deaa7e39e8b9b7d61bb67f9fc918705840e`

The live object and ingress receipt both preserve `plaintext_persisted=false`, `kv_decryption_authority=false`, no Device durable secret custody, no model access and no authority transfer. No production credential or production root key was used.

Durable evidence: `reports/skap_intr/RC17B_CONNECTED_KV_EVIDENCE.md` at `d4b4760d62833b6cf4d608dc53571dabe4afc668`.

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
RC-17 repository-local sealed persistence/readback: HOSTED PASS
RC-17B actual connected KnowledgeVault synthetic sealed write/read: PASS
RC-18 provider-bound credential session: OPEN
RC-19 first bounded provider operation: OPEN
```

## Next executable work

1. Build/reuse the iPhone browser-to-SKAP encrypted ingress transport so plaintext is encrypted before leaving the owner device and no SKAP root/private key is delivered to the phone.
2. Reuse the existing `stegverse.org` WebAuthn participant surface for owner authorization; do not create parallel authority.
3. Bind a sealed synthetic Coinbase grant to the already-proven Coinbase TLS/session path and prove same-session submission gating without a real credential.
4. Resolve production TVC/SKAP key provisioning compatible with the iPhone-only physical-runtime contract.
5. Only after explicit owner authorization, admit the first real credential and perform a read-only Coinbase permission/fee observation.
6. Only then advance to a bounded maker proof, reconciliation, next authenticated snapshot and repeat-loop evidence.

## Completion boundary

Source/CI/hosted/connected-KV synthetic proofs do not equal production activation. Completion requires real owner-authorized iPhone ingress, production SKAP key custody compatible with the no-second-machine rule, real sealed credential state, provider-bound authenticated session proof, authentic provider observation, bounded execution, reconciliation and repeat-loop evidence.
