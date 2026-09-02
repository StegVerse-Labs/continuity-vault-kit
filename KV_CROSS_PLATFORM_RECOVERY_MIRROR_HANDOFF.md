# KV Cross-Platform Recovery Mirror Handoff

Status: HOSTED_VALIDATED_MERGED_PHYSICAL_PROOF_OPEN
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #171
Merge: `13ec71e343856c0bb40d231576f372de08a96725`

## Goal

Prove the deterministic recovery contract for a lost-device/platform-change case:

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

This lane consumes the existing repository architecture:

```text
KV holds what persists.
Device/StegOS supplies what happens.
Interlock/InTr governs transitions when activated.
```

## Installed source

- `schemas/kv-cross-platform-recovery-package.schema.json`
- `schemas/kv-cross-platform-recovery-receipt.schema.json`
- `runtime/cross_platform_recovery.py`
- `fixtures/kv_cross_platform_recovery_cases.json`
- `tests/test_cross_platform_recovery.py`
- `tools/run_cross_platform_recovery_probe.py`
- `.github/workflows/kv-cross-platform-recovery.yml`

## Required decisions

The deterministic suite includes:

- valid iPhone/iCloud -> Samsung/browser recovery: `ALLOW_WITH_SIGNOFF`
- cloud login without separate recovery authority: `DENY`
- tampered package: `FAIL_CLOSED`
- stale continuity root: `ESCALATE`
- old device identity reuse: `FAIL_CLOSED`
- browser execution attempt: `DENY`
- missing InTr binding: `FAIL_CLOSED`

## Authority boundary

```text
authority_effect: NONE
cloud account is KV authority: false
browser is execution surface: false
hosted CI is production recovery: false
hosted CI is device attestation: false
hosted CI is key provisioning: false
hosted CI is live InTr: false
```

## Physical proof gate

Source/CI completion does NOT prove a real platform migration.

Physical completion requires a separately observed run with:

1. a test KV stored through an iPhone-connected iCloud account;
2. old iPhone declared unavailable for the test;
3. Samsung/Android reaches iCloud through browser-only provider access;
4. encrypted recovery package is acquired without native iCloud integration;
5. cloud authentication alone cannot expose usable KV content;
6. Samsung establishes a distinct new device identity;
7. recovery authority is satisfied independently of provider login;
8. Interlock/InTr recovery transition is observed;
9. KV identity/continuity root survives;
10. old device does not remain silently trusted;
11. a durable recovery receipt binds the transition.

Until that evidence exists:

```text
deterministic contract: IMPLEMENTED
hosted validation: PASS
physical iPhone -> Samsung proof: NOT OBSERVED
production recovery activation: NOT CLAIMED
```


## Hosted validation evidence — 2026-09-01

Exact PR-head validation before merge:

```text
PR: #172
validated head: dd7b9201b691768104c1904fe40d0b5285477584
KV Cross-Platform Recovery run: 33583493140 SUCCESS
Release integrity run: 33583493252 SUCCESS
KV Guardrails run: 33583493163 SUCCESS
Security Baseline run: 33583493195 SUCCESS
Repository validation diagnostics run: 33583493227 SUCCESS
merge: 13ec71e343856c0bb40d231576f372de08a96725
```

The first PR head correctly exposed a repository-wide workflow-census mismatch after adding the 48th hosted workflow. The census was updated from 47 to 48 without relaxing any forbidden authority marker; the successor exact-head run passed all repository gates.

Hosted validation proves only the deterministic contract. The physical iPhone/iCloud-browser/Samsung recovery remains NOT OBSERVED and must produce separate real-device evidence before production recovery is claimed.
