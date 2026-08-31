# Portable Direct-Source Canonical Raw Persistence Mirror Handoff

Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: `#160`
Branch: `feat/portable-canonical-raw-persistence-159`
State: ACTIVE_IMPLEMENTATION
Updated: 2026-08-31T11:34:00-05:00
Credential authority: TV/TVC
Authority effect: NONE

## Goal

Advance an already admitted portable DEVICE_KV owner-controlled payload from exact write-once staging to exact write-once raw canonical KV persistence at the owner-selected target path.

## Required sequence

```text
INGRESS_ADMITTED materialization
 -> validate request hash
 -> validate HB carrier binding identity/hash/zero-authority
 -> decode and exact-hash verify portable payload
 -> STAGED_UNTRUSTED write/readback
 -> verify staging receipt
 -> write exact bytes to requested canonical KV path
 -> exact canonical-path readback
 -> PERSISTED_CANONICAL_RAW receipt
```

## Semantics

`PERSISTED_CANONICAL_RAW` means the exact owner-controlled file bytes are durably present at the requested canonical KV path. It does not mean semantic interpretation is trusted, a provider session exists, SKAP credentials are active, or any write/send/trade/provider authority exists.

## Claimed surfaces

- `runtime/portable_direct_source_ingress.py`
- `tests/test_portable_direct_source_ingress.py`
- `PORTABLE_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md`
- `PORTABLE_DIRECT_SOURCE_CANONICAL_RAW_MIRROR_HANDOFF.md`

## Completion boundary

Carrier validation, write-once canonical raw persistence, exact readback receipt, tests, hosted validation and merge. Resident execution remains an independently observed runtime step.
