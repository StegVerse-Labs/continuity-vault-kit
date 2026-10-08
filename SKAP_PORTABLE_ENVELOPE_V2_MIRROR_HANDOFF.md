# SKAP Portable Envelope v2 Mirror Handoff

Status: SOURCE_ONLY_REVIEW_CANDIDATE
Repository: `StegVerse-Labs/continuity-vault-kit`
Approval: FINAL-REVIEW-009 D2/D6
Owning goal: `TVC-CREDENTIAL-MODEL-CONSISTENCY-20260826`

## What this is

Source only. No runtime is installed, no genesis has been performed, no root key or
recovery secret exists because of this change, and nothing has been written to any
KV. The test vectors are fixed, publicly known test values and must never be used as
real material.

Installed source:

- `specs/skap-kv-storage-layout.v2.json` (supersedes v1; v1 is preserved unchanged)
- `skap/portable_envelope.py` (canonical JSON, recovery secret, root key, `root_key_id`, wrap/unwrap, `KVWrappedEnvelopeKeyProvider`, bootstrap anchor helpers)
- `fixtures/skap/portable-envelope-v2.vectors.json` (deterministic cross-implementation vectors)
- `tests/test_skap_portable_envelope.py` (run by `.github/workflows/kv-guardrails.yml`)
- `skap/crypto_boundary.py`: `seal()` gains keyword-only `_test_vector_salt` / `_test_vector_nonce`, default `None`. They exist only to reproduce published vectors; no production path forwards them, and both must be supplied together with exact lengths.

## Invariants

```text
Plaintext root key at rest: forbidden.
Recovery secret at rest (KV, SKAP, receipts, logs, storage): forbidden.
Wrapped root envelope: at most one, at _Vault/SKAP/Root/wrapped-root-envelope.json.
KDF: PBKDF2-HMAC-SHA256, iterations >= 600000; lower values are refused on unwrap (downgrade).
AEAD: AES-256-GCM; AAD binds schema, kv_identity, root_key_id, kdf, policy_hash.
Root key bytes exist only inside an in-process callback and are wiped afterwards.
Decryption is permitted only at the SKAP boundary on an authenticated per-attempt execution surface.
kv_role: sealed-ciphertext-and-non-secret-evidence-custody-only.
Credential authority: TV/TVC.
Sealed objects reuse stegverse.skap.sealed_material/aes256gcm-hkdf-sha256/v1 unchanged.
TVCResidentFileKeyProvider (tvc-resident://) is unchanged; its legacy scope is preserved.
```

## Sealed-object bindings

`crypto_boundary` requires `skap://` object ids, so the spec's
`provider/<provider>/api-key` is carried as `skap://provider/<provider>/api-key`.
`key_authority_ref` is `kv-wrapped://<root_key_id>`, `wrapping_policy_ref` is the
TVC `policy_hash`, and `endpoint_ref` is the provider endpoint URL. The bootstrap
anchor uses `skap://kv-skap/bootstrap-anchor`, purpose `kv-skap-bootstrap-anchor`.

## KV/SKAP loader (genesis, enrollment, transient use)

- `skap/loader/kv-skap-loader.html`: one self-contained file, WebCrypto only. CSP: `default-src 'none'`, `script-src` and `style-src` are the SHA-256 hashes of the single inline script and style, and `connect-src` is limited to `https://api.openai.com https://api.anthropic.com`.
- `skap/loader/kv-skap-loader.sha256`: the expected file digest. Verify it with an independent tool before entering any secret. A digest the page computes about itself is not verification.
- Modes:
  - GENESIS checks existing KV state (deny on an initialized KV, fail closed when ambiguous), then verifies the owner's stage-2 inputs before generating any secret. It produces `wrapped-root-envelope.json`, `bootstrap-anchor.sealed.json` and a non-secret genesis receipt.
  - ENROLL seals a provider API key as `provider-credential`.
  - USE checks that the manifest and Organization receipt are present, evaluates POLICY_ADMISSION exactly as TVC does, and on ALLOW makes one bounded provider request. It then emits a non-secret attempt receipt for InTr delivery.
- The Organization ledger append and readback of the genesis receipt is the authoritative exactly-once fence. The loader's local check is advisory.
- `fixtures/tvc/` is a copy of TVC's POLICY_ADMISSION policy and vectors, pinned by digest (see `fixtures/tvc/PINNED.json`).
- Tests: `tests/loader/kv_skap_loader.test.mjs` (node, run by `tests/test_skap_loader_js.py`, which skips with an explicit reason when node is absent).
- Per approved design S11/D14, the owner reviews and merges the loader. That merge is the approval of these exact bytes. Any edit to the inline script or style changes its CSP hash, and the node test fails until the CSP and `kv-skap-loader.sha256` are recomputed.
- Browser limits: JavaScript strings, including a pasted API key or recovery secret, cannot be overwritten in place. The loader wipes every byte buffer it controls, clears the input fields after use, keeps no references, and writes nothing to storage or logs.

## Runtime truth

No KV/SKAP trust genesis is claimed. Genesis requires the owner-reviewed loader, an
Organization admission receipt, and an Organization ledger append and readback of
the genesis receipt (the authoritative exactly-once fence).

## Manual work

None for this source change.

---

🔒 Layer: Framework | KV
