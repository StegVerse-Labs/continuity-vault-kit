# KV Provider-Opaque Persistence Mirror Handoff

Updated: 2026-09-13
Repository: `StegVerse-Labs/continuity-vault-kit`
Goal Task ID: `KV-PROVIDER-OPAQUE-PERSISTENCE-001`
Parent Goal Task ID: `STEGOS-DEVICE-KV-SKAP-ROUNDTRIP-001`
COSV ID: `50000000102000`
State: `SOURCE_IMPLEMENTED / VALIDATION_PENDING / RUNTIME_NOT_PROVEN`

## Implemented source

`continuity/provider_opaque_persistence.py` introduces a provider-neutral KnowledgeVault persisted-object envelope using P-256 ECDH, HKDF-SHA256, and AES-256-GCM. The persisted object binds KV instance, KV set, object identity/version/classification, state commitment, and recipient protected-key identifier as authenticated data.

The persisted representation explicitly carries no plaintext or private key and grants no storage-provider plaintext, decryption, use, transition, credential, or execution authority.

Readback is callback-bound to a separately supplied protected-key operation. The resolver does not accept provider locator/account identity as decryption authority and fails closed unless governed readback admission is separately present.

## Validation source

`tests/test_provider_opaque_persistence.py` covers:

- plaintext input zeroization after sealing;
- no plaintext/private-key persistence;
- governed-admission requirement before readback;
- successful exact readback only through the matching protected-key operation;
- copied provider object + unrelated key cannot decrypt;
- object-binding tamper failure;
- ciphertext tamper failure;
- persisted authority-claim rejection.

No test result is claimed until repository CI executes against the exact branch head.

## Authority preservation

This component does not replace or modify TV/TVC credential authority, SKAP custody, Interlock/InTr transition admission, WorkerCoordinator claim/fence authority, or current-iPhone opaque key semantics. It provides the missing provider-independent confidentiality layer for ordinary KV provider materialization.

The protected-key callback is deliberate: production can bind to a non-exportable Secure Enclave/opaque key operation without exporting private-key bytes into Python, provider storage, repository state, or ordinary KV materialization.

## Remaining

1. Run deterministic repository validation against the exact branch head.
2. Repair any source/test defects exposed by CI.
3. Bind the protected-key callback to the canonical current-device opaque recipient capability without changing authority ownership.
4. Add an authentic provider-backed KV materialization/readback proof and return the verified component to the parent Device <-> KV <-> SKAP roundtrip.

## Manual work

None.
