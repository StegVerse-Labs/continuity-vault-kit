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

## Fail-closed rules

Reconstruction fails when:

- either user or entity proof is missing;
- the pair identifier or policy does not match;
- an event link or content commitment fails verification;
- a protected object is unavailable;
- a request crosses pair or policy boundaries;
- the dependency closure exceeds the permitted event window.

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

`schemas/reconstructive-memory-event.v0.1.json` defines the public minimal-event contract.

`tests/test_reconstructive_memory.py` verifies minimal reconstruction, integrity-only behavior, pair mismatch refusal, and bounded-window refusal.

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
