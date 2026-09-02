# KV Provider Relocation Mirror Handoff

Status: HOSTED_VALIDATED_MERGED_LIVE_PROVIDER_RELOCATION_OPEN
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #177
Completing PR: #181
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
source implementation: IMPLEMENTED
hosted validation: PASS
validated head: ed1e82ebb61d2af36e3cc773ef76b6b28fa16136
merge: 1f8f9334ac7ab1cf22319492ef3b4557e8396d5f
merged: YES
live iCloud -> Google Drive migration: NOT OBSERVED
provider credential/session activation: NOT OBSERVED
runtime activation: NOT CLAIMED
authority_effect: NONE
```


## Validation and merge — 2026-09-02

PR #181 exact head `ed1e82ebb61d2af36e3cc773ef76b6b28fa16136` passed:

- KV Cross-Platform Recovery: `33689065518` SUCCESS
- KV Guardrails: `33689065554` SUCCESS
- Release integrity: `33689065590` SUCCESS
- Security Baseline: `33689065529` SUCCESS
- Repository validation diagnostics: `33689065501` SUCCESS

Merged as `1f8f9334ac7ab1cf22319492ef3b4557e8396d5f`.

The deterministic provider-relocation contract is therefore implemented, validated, and merged. This does not prove an actual iCloud -> Google Drive provider operation, a TVC provider session, Interlock/InTr runtime transition, provider readback, or production activation.

## Successor runtime boundary

The live relocation must reuse the same shared HB/InTr runtime-observability contract and the existing TV/TVC provider authority lane.

Exact live predicates remain:

```text
eligible resident alive/current
TVC-owned source/destination provider sessions admitted
governed relocation request admitted by Interlock
InTr relocation packet consumed
source exact-byte readback observed
destination exact-byte write/readback observed
continuity transition receipt retained
provider authority transferred=false
provider credentials exported=false
relocation reconstruction PASS
```

No new provider credential path is authorized by this handoff.
