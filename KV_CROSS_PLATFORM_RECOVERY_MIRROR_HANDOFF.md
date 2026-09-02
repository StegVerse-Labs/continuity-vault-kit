# KV Cross-Platform Recovery Mirror Handoff

Status: HOSTED_VALIDATED_MERGED_PHYSICAL_PROOF_OPEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Deterministic issue: #171
Physical proof owner: #173
Deterministic merge: `13ec71e343856c0bb40d231576f372de08a96725`

## Goal

Prove and then physically observe the lost-device/platform-change recovery case:

```text
old device: iPhone
KV provider: iCloud
old device: unavailable/lost
replacement: Samsung/Android
provider access on replacement: browser only
```

## Canonical invariant

```text
Cloud-account access != KV authority.
Possession of KV bytes != KV authority.
KV identity may continue across device replacement.
Device identity must not continue across device replacement.
Browser-only provider access is recovery transport, not an execution surface.
Interlock/InTr remains the transition boundary.
```

## Deterministic contract — complete

Installed source:

- `schemas/kv-cross-platform-recovery-package.schema.json`
- `schemas/kv-cross-platform-recovery-receipt.schema.json`
- `runtime/cross_platform_recovery.py`
- `fixtures/kv_cross_platform_recovery_cases.json`
- `tests/test_cross_platform_recovery.py`
- `tools/run_cross_platform_recovery_probe.py`
- `.github/workflows/kv-cross-platform-recovery.yml`

Validated PR #172 head `dd7b9201b691768104c1904fe40d0b5285477584`.
Merge `13ec71e343856c0bb40d231576f372de08a96725`.

Hosted validation:
- KV Cross-Platform Recovery 33583493140 SUCCESS
- Release integrity 33583493252 SUCCESS
- KV Guardrails 33583493163 SUCCESS
- Security Baseline 33583493195 SUCCESS
- Repository validation diagnostics 33583493227 SUCCESS

This proves only deterministic decision behavior.

## Physical recovery evidence ceremony — issue #173

Live inspection on 2026-09-02 found no separate canonical implementation for physical evidence reconstruction, replacement-device attestation capture, recovery-authority evidence binding, key-provisioning observation, or final receipt reconstruction beyond the deterministic evaluator.

PR #176 / merge `40976e8ac4e9621360c036f2a2c35a48eb593776` installs the non-authorizing evidence/reconstruction prerequisite:

- `schemas/kv-physical-recovery-evidence.schema.json`
- `runtime/physical_recovery_evidence.py`
- `tests/test_physical_recovery_evidence.py`
- `tools/run_physical_recovery_reconstruction.py`

The evidence bundle requires observations for:
- browser-only provider access and encrypted package acquisition;
- provider authentication not exposing usable KV content;
- old-device unavailable/lost-or-revoked state;
- distinct replacement-device registration plus attestation reference;
- recovery authority verified independently of provider authentication;
- continuity roots and KV-identity preservation;
- observed Interlock/InTr packet and receipt references;
- bounded key provisioning/rewrap observation with no old-device key reuse;
- durable final recovery receipt.

The reconstruction verifier fails closed if any required observation is absent and emits `physical_recovery_proven=false`. It cannot manufacture device/provider/InTr/key evidence.

## Authority boundary

```text
authority_effect: NONE
cloud account is KV authority: false
browser is execution surface: false
hosted CI is production recovery: false
hosted CI is physical-device observation: false
hosted CI is device attestation: false
hosted CI is key provisioning: false
hosted CI is live InTr: false
```

## Physical proof gate

Issue #173 remains OPEN until the real iPhone/iCloud-browser/Samsung ceremony is observed. Source, CI, fixtures, screenshots, or a filled evidence JSON without authentic referenced observations cannot close it.

Required real-world proof remains:

1. test KV exists through iPhone-connected iCloud;
2. old iPhone unavailable/lost for the experiment;
3. Samsung reaches iCloud through browser-only provider access;
4. encrypted recovery package acquired without native integration;
5. provider authentication alone cannot expose usable KV content;
6. Samsung establishes a distinct device identity;
7. recovery authority is satisfied separately;
8. governed Interlock/InTr recovery transition is observed;
9. KV identity and continuity survive correctly;
10. old device is not silently trusted;
11. key access is bounded/reprovisioned without old-device identity/key reuse;
12. durable receipt binds the transition and reconstructs successfully.

Current state:

```text
deterministic contract: IMPLEMENTED / HOSTED PASS / MERGED
physical evidence ceremony source: IMPLEMENTED
physical evidence ceremony hosted validation: PASS
physical evidence ceremony validated head: ad7c146990df95c3eb75a461522ec44b3e0b2e10
physical evidence ceremony merge: 40976e8ac4e9621360c036f2a2c35a48eb593776
physical evidence ceremony merged: YES
physical iPhone -> Samsung proof: NOT OBSERVED
production recovery activation: NOT CLAIMED
```


## Physical ceremony validation and merge — 2026-09-02

PR #176 exact head `ad7c146990df95c3eb75a461522ec44b3e0b2e10` passed:
- KV Cross-Platform Recovery: 33676819294 SUCCESS
- Release integrity: 33676819238 SUCCESS
- KV Guardrails: 33676819116 SUCCESS
- Security Baseline: 33676819208 SUCCESS
- Repository validation diagnostics: 33676819222 SUCCESS

Merged as `40976e8ac4e9621360c036f2a2c35a48eb593776`.

These runs validate source behavior only. Runtime recovery, provider interaction, physical-device observation, key provisioning, live Interlock/InTr, and production activation remain unobserved.
