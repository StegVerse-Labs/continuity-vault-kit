# KV Connection Revalidation Proof Mirror Handoff

Status: SOURCE_MERGED_VALIDATED / LIVE_PROOF_GENERATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #119
Merged PR: #120
Merge commit: `21e2b47f358652813699e1b17ce7cfd01d47a8ab`
Updated: 2026-08-29
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

## Installed source

- `KV_CONNECTION_REVALIDATION_PROOF_MIRROR_HANDOFF.md`
- `schemas/kv-connection-conformance-proof.schema.json`
- `schemas/kv-connection-readback-proof.schema.json`
- `runtime/connection_revalidation.py`
- `tests/test_connection_revalidation.py`
- `tools/check_kv_connection_revalidation.py`
- read-only validation workflow

## Validation evidence

PR #120 exact head `5b74bf676b25d76e2a6483d22fc14301da061426` passed the repository validation surfaces before merge, including:

- `Validate KV Connection Revalidation` run `33192800972`: SUCCESS;
- `Repository validation diagnostics` run `33192801042`: SUCCESS;
- `Release integrity` run `33192800914`: SUCCESS;
- `Security Baseline` run `33192800999`: SUCCESS;
- `KV Guardrails (Layer + Footer + Emoji + InTr)` run `33192800976`: SUCCESS.

## Downstream machine consumer

`StegVerse-Labs/.github` now contains the merged resident WorkerCoordinator revalidation consumer and canonical COSV projection. That worker may consume these proof objects and persist the verified assembly/health receipt only after live provider and private-KV proof generation is separately observed.

## Current boundary

The proof schemas, admission runtime, tests, validation, resident consumer, and COSV projection are source-complete. Remaining work is authentic runtime evidence: a sovereign/resident execution context, an authentic provider/session conformance proof, an authentic private-KV readback proof, and inspectable VERIFIED assembly plus health-receipt persistence. No live provider session, readback proof, or connection verification is claimed by repository source completion.
