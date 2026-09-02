# KV Provider Relocation Mirror Handoff

Status: SOURCE_IMPLEMENTED_VALIDATION_PENDING
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #177
Branch: feature/kv-provider-relocation-177-v2
Authority effect: NONE
Credential authority: TV/TVC

## Goal

Prove a KnowledgeVault storage-provider relocation without transferring KV, device, credential, execution, recovery, governance, or continuity authority to either provider.

Initial deterministic case:

`iCloud -> Google Drive`

## Canonical invariants

- provider access != KV authority;
- storage relocation != device enrollment;
- KV identity persists across provider change;
- continuity root is preserved or advances only through an explicit governed transition;
- Interlock/InTr binds the relocation transition;
- TV/TVC remains credential authority;
- provider credentials are never exported through the relocation evidence contract;
- source/CI/merge do not prove a live provider migration.

## Installed source on branch

- `schemas/kv-provider-relocation-request.schema.json`
- `schemas/kv-provider-relocation-evidence.schema.json`
- `schemas/kv-provider-relocation-receipt.schema.json`
- `runtime/provider_relocation.py`
- `tests/test_provider_relocation.py`
- `tools/run_provider_relocation_probe.py`

The deterministic path returns `ALLOW_WITH_SIGNOFF` because source validation cannot prove provider execution.

A supplied observation evidence bundle may return `ALLOW` only when:
- provider authority remains false;
- provider credentials were not exported;
- InTr packet/receipt references exist;
- continuity receipt reference exists;
- source and destination exact-byte readback hashes match.

Missing or contradictory evidence fails closed or escalates.

## Shared HB / InTr runtime binding

Provider relocation is a consumer of:
`StegVerse-Labs/.github/docs/HB_RUNTIME_PRESENCE_RESIDENT_OBSERVABILITY_MIRROR_HANDOFF.md`

No provider-relocation-specific heartbeat, resident scheduler, liveness signal, credential broker, or execution authority is introduced.

A future live relocation must independently observe its provider operation, governed InTr transition, exact readback, continuity receipt, retained evidence, and reconstruction. HB provides synchronization/freshness only.

## Current state

```text
source implementation: IMPLEMENTED_ON_BRANCH
hosted validation: PENDING
merged: NO
live iCloud -> Google Drive migration: NOT OBSERVED
provider credential/session activation: NOT OBSERVED
runtime activation: NOT CLAIMED
authority_effect: NONE
```
