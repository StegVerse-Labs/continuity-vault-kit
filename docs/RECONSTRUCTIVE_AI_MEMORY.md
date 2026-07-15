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

Potentially sensitive content is stored separately under encryption and bound to:

- one KnowledgeVault;
- one StegID identity;
- one designated StegVerse AI entity;
- one relationship epoch;
- one active access policy.

Public hashes identify and verify the relationship. They are not encryption keys.

### 3. Ephemeral reconstruction workspace

An authorized query:

1. proves the user identity;
2. proves the designated AI-entity identity;
3. validates the current pair, epoch, policy, and single-use capability;
4. resolves an opaque route token without storing the plaintext query in the chain index;
5. locates only bounded candidate events;
6. follows only required dependency and supersession edges;
7. confirms each selected protected object remains active and reconstructable;
8. decrypts only the bounded selected objects;
9. verifies content commitments;
10. returns the reconstruction;
11. destroys the temporary working state;
12. consumes the capability and emits an access receipt that does not retain reconstructed plaintext by default.

## Relationship lifecycle

A pair binding is valid only for one relationship epoch. Revocation makes that epoch unusable even when an old capability or wrapped key remains available. Replacing an AI entity creates a successor pair and requires separately authorized key rewrapping; the successor does not inherit access merely by being newer.

The v0.1 `RelationshipRegistry` models active and revoked epochs. It is intentionally local and in-memory. A production registry must obtain authoritative revocation state and verify StegID and entity proofs at the access boundary.

## Capability lifecycle

`CapabilityGrant` models bounded authorization rather than a reusable bearer token. A capability is bound to one pair, policy, and relationship epoch; has an activation and expiration time; carries a nonce; and has an explicit use limit. The normal posture is one use.

Expired, revoked, premature, mismatched, or exhausted capabilities fail closed. Receipts preserve a commitment to the capability rather than the reusable capability identifier or nonce.

This prototype uses caller-supplied integer time and an in-memory use counter. A production implementation must use an authoritative clock, atomic consumption, replay-resistant nonce registration, and distributed race protection.

## Dual-proof verification boundary

`ProofVerifier` separates proof presence from proof validity. A nonempty StegID or entity proof is not sufficient. Both proofs must be independently accepted by a verifier before protected routing, key release, or reconstruction proceeds.

The callable implementation is an adapter boundary only. It does not define a signature suite, trust store, attestation format, or replay-defense protocol. Those remain production security gates.

## Minimized Ecosystem Chat ingestion

`EcosystemChatIngestor` accepts only user-approved observations. It creates a minimal `ChainEvent` that contains no raw chat text. For reconstructable retention, a caller-supplied minimizer selects the smallest approved durable representation and a separate `ContentProtector` encrypts and binds it outside the chain.

Integrity-only observations create no protected object and preserve no content commitment. Unapproved observations fail closed. A live transport adapter must still prove that the approval, policy, pair, and event-order inputs are authentic before invoking this boundary.

## Protected-object deletion and tombstones

`ObjectLifecycleRegistry` separates chain continuity from content recoverability. An active object may be reconstructed only while its lifecycle binding matches the protected object. A user deletion or cryptographic-erasure action changes the object state to `tombstoned` and makes further reconstruction fail closed.

The chain may retain a minimal integrity-only tombstone event containing a commitment to the deletion reason and receipt. It does not retain the deleted content reference in the event payload. This preserves the fact and order of deletion without falsely claiming that the underlying personal content remains recoverable.

A production implementation must ensure actual key destruction or protected-object deletion in the custody layer; changing lifecycle metadata alone is not cryptographic erasure.

## Key-unwrapping boundary

`KeyUnwrapper` is an interface, not a key derivation scheme. Public StegID, entity, pair, and event hashes must never be used directly as encryption keys. The callable prototype validates pair, policy, and epoch state before delegating to an external unwrap operation and rejects empty or invalid key material.

Production implementations should bind this interface to hardware-backed, threshold, or user-controlled key services.

## Opaque coarse routing

`OpaqueRouteIndex` stores opaque route tokens and committed event identifiers. It does not store natural-language queries or readable semantic labels. An authorized resolver derives the opaque token only after pair, policy, and epoch validation. Candidate events are bounded and their pair/policy bindings are rechecked before reconstruction.

This is a routing primitive, not encrypted semantic search. Production search still requires a protected resolver, encrypted or isolated index custody, token rotation, and leakage analysis.

## Access receipts

Authorized reconstruction emits a receipt containing:

- pair and relationship epoch;
- policy reference;
- commitments to the capability and request descriptor;
- commitment to the selected event range;
- event count;
- workspace-destruction and plaintext-retention posture.

The receipt does not contain reconstructed plaintext, raw search terms, the reusable capability identifier, or capability nonce.

## Fail-closed rules

Reconstruction, routing, ingestion, proof verification, object access, or key release fails when:

- either user or entity proof is absent or fails verification;
- the pair identifier, relationship epoch, or policy does not match;
- the relationship is revoked or unknown;
- a capability is premature, expired, revoked, mismatched, or exhausted;
- an observation lacks user approval;
- reconstructable retention produces no minimized content;
- an event link or content commitment fails verification;
- a protected object is unavailable, unknown, tombstoned, or incorrectly bound;
- a request crosses pair or policy boundaries;
- the candidate route or dependency closure exceeds its permitted window;
- an opaque route commitment fails verification;
- key unwrapping returns no usable key material.

## Implemented in this slice

`reconstructive_memory/core.py` provides deterministic pair identifiers, minimal hashed chain events, chain validation, dependency-complete bounded selection, protected-object binding checks, content-commitment verification, and ephemeral reconstruction results.

`reconstructive_memory/access.py` provides relationship-epoch state and revocation, fail-closed relationship resolution, a concrete key-unwrapping interface boundary, and hashed access receipts that exclude plaintext.

`reconstructive_memory/proofs.py` provides independent StegID and designated-entity proof verification boundaries.

`reconstructive_memory/ingestion.py` provides user-approved, minimized Ecosystem Chat observation ingestion with protected-content separation.

`reconstructive_memory/routing.py` provides opaque candidate routing, event-set commitments, bounded candidate selection, and pair/policy revalidation.

`reconstructive_memory/lifecycle.py` provides expiring and single-use capability controls, protected-object lifecycle state, tombstone commitments, and integrity-only tombstone event construction.

The JSON Schemas define the minimal event and access-receipt contracts. Unit tests cover reconstruction, integrity-only behavior, pair mismatch, bounded windows, relationship revocation, epoch mismatch, proof refusal, key unwrap refusal, minimized ingestion, opaque routing boundaries, capability replay and expiration, object tombstones, and plaintext-free access receipts.

Run the complete dependency-free validation with:

```bash
python3 tools/check_reconstructive_memory.py
```

## Explicitly not claimed

This prototype does not yet provide:

- production cryptography or key management;
- a concrete StegID signature suite;
- a concrete AI-entity attestation suite;
- hardware-backed or threshold key unwrapping;
- authoritative distributed capability consumption;
- actual custody-layer cryptographic erasure;
- encrypted semantic indexing;
- process-level memory zeroization;
- distributed custody or Master-Records installation;
- live Ecosystem Chat transport integration.

Those are successor implementation gates, not implied capabilities.

---

🔒 Layer: Framework | KV
