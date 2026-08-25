# SKAP / InTr Review Candidate Mirror Handoff

Status: HOSTED_VALIDATED_THROUGH_KV_HOSTED_SKAP_VAULT_DOUBLE_INTERLOCK_AND_SYNTHETIC_PROVIDER_SESSION / PHYSICAL_RUNTIME_REAL_OWNER_INGRESS_AND_PROVIDER_OBSERVATION_OPEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Goal ID: `SV-KV-SKAP-INTR-001`
Last updated: 2026-08-25T13:42:00-05:00

## Active goal

Activate and evidence the KV-hosted SKAP Vault with two mandatory Interlock boundaries:

```text
Device <-InTr-> KV <-InTr-> SKAP Vault
```

Broader provider path:

```text
Device <-InTr-> KV <-InTr-> SKAP Vault
                         |
                         -> endpoint-session verification
                         -> transient secret resolution
                         -> External Network <-InTr-> authorized Endpoint
```

TV/TVC remains credential/key authority. `SKAP Vault` is the credential-custody boundary logically located inside the KnowledgeVault namespace at `_Vault/SKAP`. KV itself is not secret authority: outside the SKAP Vault boundary it exposes only references, ciphertext and non-secret evidence. Device has no durable secret/key custody. Model output grants no authority.

## Canonical double-interlock contract

Source:
- `specs/skap-vault-double-interlock.v1.json`
- `scripts/validate_skap_vault_double_interlock.py`
- `.github/workflows/skap-vault-double-interlock.yml`

Canonical topology state vector:

```text
DEVICE
-> INTR_DEVICE_KV
-> KV
-> INTR_KV_SKAP
-> SKAP_VAULT
```

Required credential storage namespace:

```text
_Vault/SKAP/Credentials
```

Supporting evidence namespaces remain:

```text
_Vault/SKAP/Sealed
_Vault/SKAP/Lifecycle
_Vault/SKAP/Receipts
_Vault/SKAP/Revocations
```

The SKAP Vault is logically inside KV but is separated from ordinary KV access by the second InTr connector. Therefore:
- direct Device -> SKAP Vault access is forbidden;
- direct KV -> credential plaintext access is forbidden;
- every credential read/write/rotation/revocation requires both interlocks;
- Device -> KV emits a boundary transition receipt;
- KV -> SKAP Vault emits a second boundary transition receipt;
- the second receipt must cryptographically bind the first receipt hash plus the same credential reference and operation id;
- either missing/broken/reordered boundary fails closed;
- secret plaintext is forbidden in both receipts;
- authority is never transferred across either boundary.

Hosted `SKAP Vault Double Interlock Validation` run `32884444828` completed `SUCCESS` for the new contract, deterministic negative tests and zero-credential hosted-authority assertions.

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
RC-17C generic browser P-256 ciphertext -> canonical SKAP reseal primitive: HOSTED PASS
RC-17D KV-hosted SKAP Vault double-interlock contract: HOSTED PASS
synthetic SKAP same-session Coinbase TLS resolution ordering: HOSTED PASS
```

Connected KnowledgeVault synthetic evidence already exists under `_Vault/SKAP/{Sealed,Lifecycle,Receipts,Revocations}` and uses no production credential or production root key. The new `_Vault/SKAP/Credentials` lane is now canonical for credential ciphertext/custody but real production credential persistence there is not yet claimed.

## Generic crypto primitive vs Coinbase deferred-resolution path

`skap/browser_admission.py` remains a valid generic browser-to-canonical-SKAP primitive. It can decrypt browser ciphertext callback-locally, reseal under a canonical SKAP root-key provider, and wipe mutable plaintext.

That generic primitive must not be confused with the current Coinbase activation path. Coinbase now uses a stronger deferred-resolution sequence:

```text
browser ciphertext
-> Device/KV InTr receipt
-> KV ciphertext staging
-> KV/SKAP InTr receipt
-> SKAP Vault unchanged ciphertext custody
-> exact Coinbase endpoint/session verification + current grant
-> transient credential resolution
```

For Coinbase, no decrypt/rewrap occurs at Device->KV or KV->SKAP Vault admission. This prevents the earlier browser-stage/canonical-reseal model from becoming an accidental production requirement.

## Production-key boundary

The earlier `/run/stegverse/tv-tvc-credentials/...` file provider remains a validated reference implementation only. It must not become a requirement for the owner to operate a second machine.

Production activation still requires a StegVerse/TVC-managed key runtime without exporting:
- P-256 recipient private key to Site/Device/GitHub/model;
- canonical SKAP root key to Site/Device/ordinary-KV/GitHub/model.

A public Site projection may contain only the ACTIVE recipient public JWK/key id/fingerprint and non-secret lease/liveness metadata.

## Current open gates

```text
KV/SKAP Vault double-interlock source contract: HOSTED PASS
actual KV/SKAP Vault runtime + both boundary receipts: NOT YET OBSERVED
production TVC/SKAP private-key provisioning under iPhone-only contract: OPEN
real current-iPhone owner ingress: OPEN
governed StegVerse public ciphertext route observation: OPEN
ACTIVE public-key lease projected to Site: OPEN
real Coinbase ciphertext stored under _Vault/SKAP/Credentials: OPEN
real provider-bound authenticated permission/fee observation: OPEN
first bounded max-$10 post-only maker operation: OPEN
reconciliation + return receipts: OPEN
second bounded repeat cycle: OPEN
```

## Next executable work

1. Require both Device/KV and KV/SKAP Vault receipts in every credential-specific TVC ingress/resolution lane.
2. Observe a real shared KV root exposing `_Vault/SKAP/Credentials` and `_Vault/SKAP/Receipts` to the authorized TVC runtime without granting KV decryption authority.
3. Establish/observe production recipient-key custody and current lease/liveness under TV/TVC authority.
4. Propagate only public key/lease/route evidence to Site after those runtime gates exist.
5. Perform one real current-iPhone owner-authorized Coinbase ingress through both interlocks and retain the double-receipt chain.
6. Obtain the first authentic permission/fee observation only after endpoint-session verification.
7. Only after that evidence and separate bounded authorization, execute/reconcile the first max-$10 ETH-USD LIMIT/GTC post-only maker order and repeat once.

## Non-claims

No production recipient private key or canonical root key was provisioned by these source/hosted proofs. No real Coinbase credential has been stored in the SKAP Vault. No authentic provider permission/fee observation through the new double-interlock path has occurred. No live order was submitted. Hosted and connected synthetic evidence does not equal production activation.
