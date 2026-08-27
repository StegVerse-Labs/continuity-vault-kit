# Residual Hosted Release Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #81
Branch: `fix/residual-hosted-release-authority-81`
State: CLAIMED_FOR_IMPLEMENTATION

## Purpose

Close the residual CMC-023 hosted repository/publication authority still present after PR #78.

Live main still contains:

```text
.github/workflows/release-integrity.yml:
  contents: write
  commits docs/release_evidence/latest.*
  git push

.github/workflows/automated-release.yml:
  contents: write
  mutates VERSION + CHANGELOG
  creates commit + tag
  git push
  consumes github.token through GH_TOKEN
  gh release create
  commits release receipt
```

These behaviors contradict the current TV/TVC credential/release model and the downstream TVC consistency claim that hosted repository control-plane authority is NONE.

## Required state

```text
GitHub Actions release authority: NONE
GitHub Actions repository mutation authority: NONE
GitHub Actions tag authority: NONE
GitHub Actions publication authority: NONE
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
credential/release authority: TV/TVC
VERSION persistent mutation: TVC-admitted release only
CHANGELOG finalization persistent mutation: TVC-admitted release only
release publication runtime: separate / NOT OBSERVED
```

Hosted workflows may rebuild, validate, derive candidate readiness, and upload non-secret short-lived evidence artifacts. They may not persist canonical state or execute release publication.

## Collision boundary

- PR #78 is completed historical source retirement and must not be reopened.
- Do not alter v0.1.9 release evidence or claim a successor release.
- Do not introduce a new GitHub credential or TVC credential into Actions.
- Do not change production KV/SKAP/InTr runtime authority.
- Do not create a second release credential model.

## Planned source

- `.github/workflows/release-integrity.yml`
- `.github/workflows/automated-release.yml`
- `.github/workflows/release-cycle-outcome.yml` only for renamed workflow observation binding
- `tools/test_automation_contracts.py`
- `tests/test_hosted_release_authority_retirement.py`
- `STATUS.md`
- `CONTINUITY_VAULT_KIT_MIRROR_HANDOFF.md`

## Non-claims

No release, tag, deployment, publication, resident TVC capability, or activation is produced by this source repair.

## Next executable boundary

Implement validation-only workflow behavior, extend regression enforcement, run exact-head validation, merge only after all applicable checks pass, then reconcile TVC credential-model consistency source so the hosted-authority claim matches live CVK state.
