# Residual Hosted Release Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #81
Branch: `main`
State: MERGED_VALIDATED_HOSTED_AUTHORITY_RETIRED_TVC_PUBLICATION_PENDING

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

## Implemented source state

```text
release-integrity.yml:
  contents: read
  checkout credential persistence: false
  release build/verify: retained
  durable main writeback: removed
  hosted observation: short-lived artifact only

automated-release.yml:
  state: Automated release readiness - Validation Only
  contents: read
  checkout credential persistence: false
  ephemeral patch candidate build: allowed for validation
  persistent VERSION mutation: false
  persistent CHANGELOG mutation: false
  commit/tag/push: removed
  github.token / GH_TOKEN: removed
  GitHub release publication: removed
  TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED: explicit

release-cycle-outcome.yml:
  observes renamed validation-only readiness workflow

regression:
  release-integrity + automated-release included in hosted-authority retirement tests
  automation contract rejects hosted mutation/publication tokens on all four release-cycle validation surfaces
```

## Release metadata correction

`CHANGELOG.md#Unreleased` now records the merged KV Interlock endpoint and hosted release-authority retirements. `VERSION` intentionally remains `0.1.9`; successor version mutation/tag/publication is reserved for admitted TV/TVC release execution.

## Next executable boundary

Run exact-head hosted validation, repair any source/test defect without reintroducing hosted authority, merge only after green evidence, then reconcile TVC credential-model consistency and the global project handoff. A successor release remains blocked until the TVC-admitted release runtime is actually observed.


## Merge and post-merge evidence

```text
PR: #82
validated head: 28bf473fc353ab6e9b80bdbcc53fcaf2fa4fda72
merge: f2deeb4ade6f522ea9284dc2a1748b9749064502

exact-head:
  Release integrity 33119477875 SUCCESS
  Repository validation diagnostics 33119477843 SUCCESS
  Security Baseline 33119477790 SUCCESS
  KnowledgeVault Execution Recovery 33119477819 SUCCESS
  KV Guardrails 33119477814 SUCCESS

post-merge main:
  Release integrity 33119620345 SUCCESS
  KV Guardrails 33119620346 SUCCESS
  Security Baseline 33119620381 SUCCESS
  KnowledgeVault Execution Recovery 33119620306 SUCCESS
  Automated release readiness - Validation Only 33119637686 SUCCESS
  readiness artifact: 9665916881
  artifact digest: sha256:99ca14953f4cf21ad958c3ae86d2b6e03788d98cdcf21f1272f82a56493ec67a
```

Post-merge readiness observation:

```text
source_head_sha: f2deeb4ade6f522ea9284dc2a1748b9749064502
release_required: true
candidate_version: 0.1.10
state: TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED
credential_authority: TV/TVC
github_actions_role: VALIDATION_TRANSPORT_ONLY
repository_mutation_performed: false
version_mutation_persisted: false
changelog_mutation_persisted: false
tag_mutation_performed: false
release_publication_performed: false
authority_effect: NONE
persistent VERSION on main: 0.1.9
```

The ephemeral 0.1.10 candidate is validation evidence only. It is not a release, tag, or canonical version transition.

## Current next boundary

The source-retirement goal of issue #81 is COMPLETE. The next release transition is separate: an admitted TV/TVC release capability must consume the validated Unreleased candidate and perform any canonical VERSION/changelog/tag/publication transition. Until that runtime is observed, v0.1.9 remains the latest published release.
