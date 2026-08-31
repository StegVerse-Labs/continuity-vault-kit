# Portable Direct-Source Admission Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: `#156`
Branch: `feat/portable-direct-source-admission-156`
State: ACTIVE_IMPLEMENTATION
Updated: 2026-08-31
Credential authority: TV/TVC
Authority effect: NONE

## Goal

Consume an already-admitted canonical DEVICE_KV Universal InTr materialization that carries a bounded owner-controlled inline payload and durably stage the exact bytes inside the KnowledgeVault without falsely promoting them to trusted semantic knowledge.

## Canonical upstream

- `StegVerse-Labs/Site#789`
- destination: `{"boundary":"KV","subsystem":"KnowledgeVault:Interlock"}`
- downstream owner: `StegVerse-Labs/continuity-vault-kit#79`
- ingress receipt schema: `stegverse.device-kv-intr-materialization-ingress/v1`

## Runtime contract

```text
admitted DEVICE_KV materialization
 -> validate request hash + payload hash
 -> validate inline payload schema
 -> decode exact bytes
 -> per-file SHA-256 + size verification
 -> reject secret-like/unsafe path metadata
 -> durable write-once staging under 00_Inbox/DirectSource
 -> exact readback hash verification
 -> durable staging receipt
```

## State boundary

`STAGED_UNTRUSTED` means exact bytes are durably persisted in the KV data root but have not been promoted into the requested semantic directory.

It does not mean:
- trusted semantic admission;
- mailbox/provider session activation;
- SKAP credential activation;
- global Interlock activation;
- production network activation.

## Claimed surfaces

- `runtime/portable_direct_source_ingress.py`
- `tests/test_portable_direct_source_ingress.py`
- `PORTABLE_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`

## Completion gates

- exact request/request-hash validation;
- canonical destination/owner validation;
- <= 4 MiB aggregate payload bound;
- exact decoded file hash/size verification;
- path traversal and duplicate-name rejection;
- write-once staging;
- exact readback verification;
- reconstruction receipt;
- hosted validation;
- merge.

Runtime execution on an actual sovereign resident remains separately observed.

## 2026-08-31 canonical raw persistence extension

Issue #160 adds canonical HB carrier-binding verification and a second write-once transition, `PERSISTED_CANONICAL_RAW`. Exact owner-controlled bytes may be persisted at the owner-selected canonical KV path after staging/readback. `trusted_semantic_admission`, provider session, reusable credential material, and authority effect remain false/NONE.
