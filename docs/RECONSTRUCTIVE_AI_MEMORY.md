# Reconstructive AI Memory v0.1

## Thesis

The next state of AI memory should not require a permanently readable archive of a user's life. It should retain the minimum durable structure needed to locate, authorize, verify, and reconstruct the smallest causally complete section of prior context.

## Storage surfaces

### 1. Minimal continuity chain

The chain stores low-information event identity, sequence, pair and policy binding, authority references, content commitments, dependency edges, retention class, and chain hashes. It is not the plaintext conversation archive.

### 2. Protected object store

Sensitive content is protected separately and bound to one KnowledgeVault, one StegID identity, one designated StegVerse AI entity, one relationship epoch, and one active access policy. Public hashes identify and verify relationships; they are not encryption keys.

### 3. Ephemeral reconstruction workspace

An authorized request proves both identities, validates the relationship and capability, resolves an opaque route, selects a bounded causal subgraph, checks object lifecycle state, decrypts only selected objects, verifies commitments, emits a plaintext-free receipt, and returns a consumed capability state. Temporary plaintext is not retained by default.

## Relationship and capability lifecycle

A pair binding is valid only for one relationship epoch. Revocation makes that epoch unusable. Replacing an AI entity creates a successor pair and requires separately authorized key rewrapping.

`CapabilityGrant` is bound to one pair, policy, and epoch, with activation, expiration, nonce, and use limits. Expired, revoked, premature, mismatched, or exhausted capabilities fail closed.

## Dual-proof boundary

`ProofVerifier` separates proof presence from proof validity. Both the StegID proof and designated AI-entity proof must independently verify before protected routing, key release, or reconstruction.

## Minimized Ecosystem Chat ingestion

`EcosystemChatIngestor` accepts only user-approved observations. It creates a minimal `ChainEvent` containing no raw chat text. A caller-supplied minimizer selects the smallest approved durable representation, and a separate `ContentProtector` encrypts it outside the chain. Integrity-only observations create no protected object or content commitment.

## Protected-object deletion and tombstones

`ObjectLifecycleRegistry` separates continuity from recoverability. Tombstoned content cannot be reconstructed. The chain may retain an integrity-only deletion commitment without retaining the deleted content reference. Actual erasure still requires key destruction or object deletion in the custody layer.

## Opaque routing and bounded reconstruction

`OpaqueRouteIndex` stores opaque route tokens and committed candidate event identifiers, not plaintext queries or readable semantic labels. Candidate events are bounded, pair and policy bindings are rechecked, and `EphemeralReconstructor` follows only required dependency and supersession edges.

## Coordinated reconstruction sessions

`ReconstructionSessionCoordinator` orders the logical transaction:

1. resolve the active relationship;
2. verify both identity proofs;
3. validate the capability without consuming it;
4. resolve and validate bounded candidate events;
5. enforce lifecycle state when each protected object is decrypted;
6. reconstruct the dependency-complete event set;
7. emit a plaintext-free access receipt;
8. return the capability in consumed state only after all prior steps succeed.

No consumed capability is returned when proof, routing, lifecycle, integrity, or reconstruction fails.

## Plaintext-free session journal

`SessionJournal` records prepared, committed, aborted, and replay-rejected transactions in an append-only hash chain. Entries retain only pair, policy, epoch, capability and request commitments, receipt hashes, and bounded failure codes. Queries and reconstructed plaintext are excluded.

## Authoritative commit boundary

`AuthoritativeSessionStore` models the minimum compare-and-swap invariant needed after successful reconstruction. Under one lock it verifies the prepared session, unchanged capability state, pair/policy/epoch bindings, exact one-use transition, receipt integrity, and receipt uniqueness. It then makes these facts visible together:

- consumed capability state;
- committed access receipt;
- terminal committed journal entry.

Abort writes only an aborted journal state and leaves the capability unconsumed. This implementation is in-memory; production adapters must preserve the same invariant in durable replicated storage with authoritative clocks and replay-resistant nonce registration.

## Validation

The dedicated workflow `.github/workflows/reconstructive-memory.yml` compiles the module and runs:

```bash
python3 tools/check_reconstructive_memory.py
```

The validator checks required files and schemas and discovers all `test_reconstructive_memory*.py` tests.

## Implemented modules

- `core.py`: minimal chain and bounded causal reconstruction.
- `access.py`: relationship lifecycle, key-unwrapping boundary, and receipts.
- `proofs.py`: independent identity proof-verification interfaces.
- `ingestion.py`: approved and minimized chat ingestion.
- `routing.py`: opaque bounded candidate routing.
- `lifecycle.py`: expiring capabilities, replay denial, object lifecycle, and tombstones.
- `session.py`: coordinated fail-closed reconstruction.
- `journal.py`: plaintext-free transaction history.
- `authority.py`: atomic receipt, capability, and journal commit boundary.

## Explicitly not claimed

This prototype does not yet provide production cryptography, concrete StegID signatures, concrete AI-entity attestation, hardware-backed key custody, durable distributed transactions, actual custody-layer erasure, encrypted semantic indexing, process memory zeroization, distributed custody, Master-Records installation, or live Ecosystem Chat transport integration.

Those are successor implementation gates, not implied capabilities.

---

🔒 Layer: Framework | KV
