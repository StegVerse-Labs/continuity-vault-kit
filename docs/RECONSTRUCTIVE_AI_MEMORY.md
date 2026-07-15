# Reconstructive AI Memory v0.1

## Thesis

The next state of AI memory should not require a permanently readable archive of a user's life. It should retain the minimum durable structure needed to locate, authorize, verify, and reconstruct the smallest causally complete section of prior context.

## Storage surfaces

### 1. Minimal continuity chain

The chain stores low-information continuity records:

- event identity and sequence;
- pair-bound user/entity relationship identifier;
- policy and authority references;
- content reference and cryptographic commitment;
- dependency and supersession edges;
- retention class;
- previous-event hash and current-event hash.

The chain must not be treated as the plaintext conversation archive.

### 2. Protected object store

Potentially sensitive content is stored separately under encryption and bound to one KnowledgeVault, one StegID identity, one designated StegVerse AI entity, one relationship epoch, and one active access policy.

Public hashes identify and verify the relationship. They are not encryption keys.

### 3. Ephemeral reconstruction workspace

An authorized query proves both identities, validates the current relationship and capability, resolves an opaque route, selects a bounded causal subgraph, checks object lifecycle state, decrypts only selected objects, verifies commitments, emits a plaintext-free receipt, and returns a consumed capability state. Temporary plaintext is not retained by default.

## Relationship lifecycle

A pair binding is valid only for one relationship epoch. Revocation makes that epoch unusable even when an old capability or wrapped key remains available. Replacing an AI entity creates a successor pair and requires separately authorized key rewrapping; the successor does not inherit access merely by being newer.

## Capability lifecycle

`CapabilityGrant` models bounded authorization rather than a reusable bearer token. A capability is bound to one pair, policy, and relationship epoch; has an activation and expiration time; carries a nonce; and has an explicit use limit. Expired, revoked, premature, mismatched, or exhausted capabilities fail closed.

A production implementation must use an authoritative clock, atomic consumption, replay-resistant nonce registration, and distributed race protection.

## Dual-proof verification boundary

`ProofVerifier` separates proof presence from proof validity. Both the StegID proof and designated AI-entity proof must be independently accepted before protected routing, key release, or reconstruction proceeds.

The callable implementation is an adapter boundary only. It does not define a signature suite, trust store, attestation format, or replay-defense protocol.

## Minimized Ecosystem Chat ingestion

`EcosystemChatIngestor` accepts only user-approved observations. It creates a minimal `ChainEvent` containing no raw chat text. For reconstructable retention, a caller-supplied minimizer selects the smallest approved durable representation and a separate `ContentProtector` encrypts and binds it outside the chain.

Integrity-only observations create no protected object and preserve no content commitment.

## Protected-object deletion and tombstones

`ObjectLifecycleRegistry` separates chain continuity from content recoverability. An active object may be reconstructed only while its lifecycle binding matches the protected object. A user deletion or cryptographic-erasure action changes the object state to `tombstoned` and makes further reconstruction fail closed.

The chain may retain a minimal integrity-only tombstone event containing a commitment to the deletion reason and receipt. It does not retain the deleted content reference in the event payload.

Changing lifecycle metadata alone is not cryptographic erasure. Production custody must destroy the key or delete the protected object.

## Key-unwrapping boundary

`KeyUnwrapper` is an interface, not a key derivation scheme. Public StegID, entity, pair, and event hashes must never be used directly as encryption keys.

Production implementations should bind this interface to hardware-backed, threshold, or user-controlled key services.

## Opaque coarse routing

`OpaqueRouteIndex` stores opaque route tokens and committed event identifiers. It does not store natural-language queries or readable semantic labels. Candidate events are bounded and pair/policy bindings are rechecked before reconstruction.

This is a routing primitive, not encrypted semantic search.

## Coordinated reconstruction sessions

`ReconstructionSessionCoordinator` orders the full access path as one logical transaction:

1. resolve the active relationship;
2. verify both identity proofs;
3. validate the capability without consuming it;
4. resolve and validate bounded candidate events;
5. enforce lifecycle state at the moment each protected object is decrypted;
6. reconstruct the dependency-complete event set;
7. emit a plaintext-free access receipt;
8. return the capability in consumed state only after all prior steps succeed.

No consumed capability is returned when proof, routing, lifecycle, integrity, or reconstruction fails. This prevents ordinary failure paths from burning a capability before useful reconstruction occurs.

The coordinator is still a logical transaction. A production service must atomically persist capability consumption and the receipt in one authoritative store to prevent concurrent replay races.

## Access receipts

Authorized reconstruction emits a receipt containing pair and epoch, policy, commitments to the capability and request descriptor, commitment to the selected event range, event count, and workspace-destruction posture.

The receipt does not contain reconstructed plaintext, raw search terms, the reusable capability identifier, or capability nonce.

## Fail-closed rules

Reconstruction, routing, ingestion, proof verification, object access, or key release fails when:

- either user or entity proof is absent or fails verification;
- pair, epoch, or policy does not match;
- the relationship is revoked or unknown;
- a capability is premature, expired, revoked, mismatched, or exhausted;
- an observation lacks user approval;
- reconstructable retention produces no minimized content;
- an event link or content commitment fails verification;
- a protected object is unavailable, unknown, tombstoned, or incorrectly bound;
- a request crosses pair or policy boundaries;
- candidate routing or dependency closure exceeds its permitted window;
- an opaque route commitment fails verification;
- key unwrapping returns no usable key material.

## Implemented in this slice

- `core.py`: minimal chain and bounded causal reconstruction.
- `access.py`: relationship lifecycle, key-unwrapping boundary, and access receipts.
- `proofs.py`: independent StegID and entity proof-verification interfaces.
- `ingestion.py`: approved, minimized Ecosystem Chat ingestion.
- `routing.py`: opaque bounded candidate routing.
- `lifecycle.py`: expiring capabilities, replay denial, object lifecycle, and tombstones.
- `session.py`: coordinated fail-closed reconstruction sessions.
- JSON Schemas, unit tests, and a unified dependency-free validator.

Run validation with:

```bash
python3 tools/check_reconstructive_memory.py
```

## Explicitly not claimed

This prototype does not yet provide production cryptography, concrete StegID signatures, concrete AI-entity attestation, hardware-backed key custody, authoritative distributed capability consumption, actual custody-layer erasure, encrypted semantic indexing, process memory zeroization, distributed custody, Master-Records installation, or live Ecosystem Chat transport integration.

Those are successor implementation gates, not implied capabilities.

---

🔒 Layer: Framework | KV
