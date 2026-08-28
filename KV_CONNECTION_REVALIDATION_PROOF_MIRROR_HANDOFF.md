# KV Connection Revalidation Proof Mirror Handoff

Status: SOURCE_LANE_OPEN / IMPLEMENTATION_IN_PROGRESS
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #119
Branch: `feature/kv-connection-revalidation-proof`
Updated: 2026-08-28
Authority effect: NONE
Activation effect: false

## Purpose

Define the exact non-secret proof contract required to restore a Personal KV connection assembly to `VERIFIED` after initial assembly, source-change invalidation, session repair, or runtime recovery.

Canonical verification flow:

```text
exact connection assembly
 + provider/source conformance proof
 + private KV readback proof
 -> proof admission
 -> existing verify_connection transition
 -> VERIFIED connection assembly
 -> connection-health receipt
```

## Required proof classes

### Provider/source conformance proof

Must bind:

- exact assembly ID;
- provider;
- direct source verified;
- provider session verified;
- exact adapter name/version;
- current source compatibility assumptions reference/hash;
- observation timestamp;
- provider operation authorized: false;
- credential material present: false;
- authority effect: NONE.

This proof may be emitted only by the separately governed provider/session lane. It contains no reusable credential or secret material.

### Private KV readback proof

Must bind:

- exact assembly ID;
- canonical KV path;
- readback verified: true;
- exact persisted state/receipt reference;
- observation timestamp;
- provider operation authorized: false;
- credential material present: false;
- authority effect: NONE.

## Verification rule

A connection may transition to `VERIFIED` only when:

1. both proof objects are present;
2. both match the same exact assembly;
3. provider and adapter bindings match the assembly;
4. canonical KV path matches the assembly;
5. direct-source/session verification is true;
6. readback verification is true;
7. credential material is absent;
8. provider operation authority is false;
9. neither proof predates the source-change/revalidation event that invalidated the prior verification;
10. the existing canonical `verify_connection` transition succeeds.

## Hard boundaries

- No provider credential, password, token, API key, private key, cookie, recovery material, or SKAP plaintext.
- No new credential architecture.
- No new generic provider-auth mechanism.
- Provider authentication remains owned by existing TVC/SKAP provider lanes.
- This lane admits proof only; it does not log in to a provider.
- GitHub Actions is validation-only and cannot produce live provider/readback proof.
- A source merge or test PASS cannot satisfy live conformance/readback proof.
- Provider mutation authority remains NONE.

## Planned source

- `KV_CONNECTION_REVALIDATION_PROOF_MIRROR_HANDOFF.md`
- `schemas/kv-connection-conformance-proof.schema.json`
- `schemas/kv-connection-readback-proof.schema.json`
- `runtime/connection_revalidation.py`
- `tests/test_connection_revalidation.py`
- `tools/check_kv_connection_revalidation.py`
- read-only validation workflow

## Downstream machine consumer

A resident WorkerCoordinator task may consume these proof objects and persist the verified assembly/health receipt after live provider and private-KV proof generation is separately observed.

## Current boundary

Source proof contract only. No live provider session, private-KV readback proof, or connection verification is claimed by this branch.
