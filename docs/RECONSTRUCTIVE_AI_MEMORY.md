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
3. validates the current pair, epoch, policy, and capability;
4. locates candidate events using minimal chain data;
5. follows only required dependency and supersession edges;
6. decrypts only the bounded selected objects;
7. verifies content commitments;
8. returns the reconstruction;
9. destroys the temporary working state;
10. emits an access receipt that does not retain reconstructed plaintext by default.

## Relationship lifecycle

A pair binding is valid only for one relationship epoch. Revocation makes that epoch unusable even when an old capability or wrapped key remains available. Replacing an AI entity creates a successor pair and requires separately authorized key rewrapping; the successor does not inherit access merely by being newer.

The v0.1 `RelationshipRegistry` models active and revoked epochs. It is intentionally local and in-memory. A production registry must obtain authoritative revocation state and verify StegID and entity proofs at the access boundary.

## Key-unwrapping boundary

`KeyUnwrapper` is an interface, not a key derivation scheme. Public StegID, entity, pair, and event hashes must never be used directly as encryption keys. The callable prototype validates pair, policy, and epoch state before delegating to an external unwrap operation and rejects empty or invalid key material.

Production implementations should bind this interface to hardware-backed, threshold, or user-controlled key services.

## Access receipts

Authorized reconstruction emits a receipt containing:

- pair and relationship epoch;
- policy reference;
- commitments to the capability and request descriptor;
- commitment to the selected event range;
- event count;
- workspace-destruction and plaintext-retention posture.

The receipt does not contain reconstructed plaintext, raw search terms, or the reusable capability identifier.

## Fail-closed rules

Reconstruction or key release fails when:

- either user or entity proof is missing;
- the pair identifier, relationship epoch, or policy does not match;
- the relationship is revoked or unknown;
- an event link or content commitment fails verification;
- a protected object is unavailable;
- a request crosses pair or policy boundaries;
- the dependency closure exceeds the permitted event window;
- key unwrapping returns no usable key material.

## Implemented in this slice

`reconstructive_memory/core.py` provides:

- deterministic pair identifiers;
- minimal hashed chain events;
- chain-link validation;
- dependency-complete bounded selection;
- dual-proof authorization context;
- protected-object binding checks;
- content-commitment verification;
- ephemeral reconstruction results marked as non-retained and destroyed.

`reconstructive_memory/access.py` provides:

- relationship-epoch state and revocation;
- fail-closed relationship resolution;
- a concrete key-unwrapping interface boundary;
- hashed access receipts that exclude plaintext.

The two JSON Schemas define the minimal event and access-receipt contracts. Unit tests cover reconstruction, integrity-only behavior, pair mismatch, bounded windows, revocation, epoch mismatch, key unwrap refusal, and plaintext-free access receipts.

## Explicitly not claimed

This prototype does not yet provide:

- production cryptography or key management;
- StegID signature verification;
- AI-entity attestation;
- hardware-backed or threshold key unwrapping;
- encrypted semantic indexing;
- process-level memory zeroization;
- distributed custody or Master-Records installation;
- live Ecosystem Chat ingestion.

Those are successor implementation gates, not implied capabilities.

---

🔒 Layer: Framework | KV
