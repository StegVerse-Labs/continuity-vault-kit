# SKAP / InTr Review Candidate Mirror Handoff

Status: HOSTED_VALIDATED_THROUGH_BROWSER_TO_CANONICAL_SKAP_ADMISSION_CONNECTED_KV_AND_SYNTHETIC_PROVIDER_SESSION / PRODUCTION_KEY_AND_REAL_OWNER_INGRESS_OPEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Goal ID: `SV-KV-SKAP-INTR-001`
Last updated: 2026-08-25T04:10:00Z

## Active goal

Activate and evidence:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

TV/TVC remains credential/key authority. SKAP is sealed custody and transient resolution only. KV stores ciphertext/reference + non-secret evidence only. Device has no durable secret/key custody. External Network is transport only. Model output grants no authority.

## Hosted/connected proofs

```text
RC-01..RC-13 protocol/schema/reconstruction/synthetic transport: HOSTED PASS
RC-14A real non-secret Coinbase TLS/HTTPS endpoint traversal: HOSTED PASS
RC-15A canonical SKAP AES-256-GCM/HKDF-SHA256 crypto: HOSTED PASS
RC-15B lifecycle/grant rotation/revocation/replay invalidation: HOSTED PASS
RC-15C canonical SKAP root-key provider interface/reference implementation: HOSTED PASS
RC-16A owner-ingress synthetic proof: HOSTED PASS
RC-17 repository-local sealed persistence/readback: HOSTED PASS
RC-17B connected KnowledgeVault synthetic sealed persistence/readback: PASS
RC-17C browser P-256 ciphertext -> canonical SKAP reseal bridge: HOSTED PASS
synthetic SKAP same-session Coinbase TLS resolution ordering: HOSTED PASS
```

External Coinbase transport run `32800229287` completed `SUCCESS`; no Authorization header or credential material is sent and redirects are denied.

Connected KnowledgeVault synthetic evidence remains under `_Vault/SKAP/{Sealed,Lifecycle,Receipts,Revocations}` and uses no production credential or production root key.

## Browser ingress and canonical custody are distinct stages

Canonical browser primitive: `skap/browser_ingress.py`.

The browser/device receives only a P-256 recipient public key, generates one-operation ephemeral ECDH state, derives AES-256-GCM material via HKDF-SHA256 and sends ciphertext only. Recipient private key never leaves SKAP/TVC custody.

Canonical SKAP ciphertext primitive: `skap/crypto_boundary.py`.

These stages are now composed by:

- `skap/browser_admission.py` commit `5528bea33c8d5ab01c7bc86a0d802242d1cb231b`;
- `tests/test_skap_browser_admission.py` commit `495b61f307bbc97bff14841b978c5b6d087605eb`;
- hosted guardrail integration commit `0773981826daccfb7d3569f0a285dae1e041684a`.

The bridge uses two callback-scoped providers:
1. a `BrowserRecipientKeyProvider` that supplies the P-256 recipient private-key object only to the decrypt callback;
2. the existing canonical `KeyProvider` that supplies SKAP root-key bytes only to the canonical seal callback.

Transition:

```text
browser ciphertext
-> resolve_at_skap(recipient private key callback)
-> callback-local mutable plaintext
-> seal_with_provider(canonical root-key callback)
-> canonical SKAP ciphertext
-> mutable plaintext wiped
```

Wrong recipient key, recipient-key authority substitution, endpoint substitution and browser-context tamper all fail before the canonical root-key provider may produce a sealed object.

Hosted `KV Guardrails` run `32807856275` completed `SUCCESS`. The dedicated `Validate browser ciphertext to canonical SKAP admission bridge` step passed, as did every prior SKAP/InTr, connected persistence, external Coinbase transport, synthetic sealed-session and non-authorizing validation step.

## Production-key boundary

The earlier `/run/stegverse/tv-tvc-credentials/...` file provider remains a validated reference implementation only. It must not become a requirement for the owner to operate a second machine.

Production activation still requires a StegVerse/TVC-managed key runtime satisfying both provider interfaces without exporting:
- P-256 recipient private key to Site/Device/GitHub/model;
- canonical SKAP root key to Site/Device/KV/GitHub/model.

A public Site projection may contain only the ACTIVE recipient public JWK/key id/fingerprint and non-secret policy metadata.

## Current open gates

```text
RC-15D production TVC/SKAP private-key provisioning under iPhone-only contract: OPEN
RC-16B real current-iPhone owner ingress: OPEN
governed stegverse.org ciphertext receiver: OPEN
ACTIVE public-key lease projected to Site: OPEN
real canonical SKAP Coinbase sealed object/grant: OPEN
RC-18 real provider-bound authenticated permission/fee observation: OPEN
RC-19 first bounded max-$10 post-only maker operation: OPEN
reconciliation + return receipts: OPEN
second bounded repeat cycle: OPEN
```

## Next executable work

1. Bind TVC's existing `coinbase_browser_skap_ingress_service.py` `canonical_admit` adapter to `skap.browser_admission.admit_browser_envelope`; do not duplicate crypto.
2. Define the production P-256 recipient-private-key provider/lease contract and canonical root-key provider runtime under StegVerse/TVC authority, with no second user-operated machine.
3. Connect the existing Site iPhone sealing surface to a governed StegVerse-native ciphertext receiver.
4. Publish only an ACTIVE leased public key after real private-key custody exists.
5. Perform real current-iPhone owner-authorized Coinbase ingress, then authenticated sanitized permission/fee observation.
6. Only after that evidence, execute/reconcile the first max-$10 ETH-USD LIMIT/GTC post-only maker order and repeat once.

## Non-claims

No production recipient private key or canonical root key was provisioned by these source/hosted proofs. No real Coinbase credential has been admitted. No authentic provider permission/fee observation through the new path has occurred. No live order was submitted. Hosted and connected synthetic evidence does not equal production activation.
