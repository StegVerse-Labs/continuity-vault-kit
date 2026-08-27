# Automation Candidate Hosted Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #83
Branch: `fix/automation-candidate-hosted-authority-83`
State: IMPLEMENTED_ON_BRANCH_VALIDATION_PENDING

## Goal

Convert the existing hosted automation-candidate implementation observer to validation/evidence transport only.

## Live contradiction

Current main `.github/workflows/automation-candidate-implementation.yml` has:

```text
actions: write
contents: write
issues: write
GH_TOKEN <- github.token
gh issue edit/comment
CHANGELOG.md mutation
git commit
git push origin HEAD:main
gh workflow run automation-candidate-lifecycle.yml
```

These are hosted control-plane/repository mutation behaviors and conflict with the current StegVerse boundary.

## Required state

```text
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
permissions: contents: read / pull-requests: read
persist-credentials: false
issue mutation: false
repository mutation: false
workflow dispatch: false
credential/token consumption: false
release authority: NONE
authority_effect: NONE
```

The hosted workflow may deterministically parse candidate references from a merged PR and emit a non-secret observation artifact. It must not determine canonical candidate lifecycle state or mutate it.

## Collision boundary

- Do not create another candidate registry or lifecycle owner.
- Do not change candidate threshold semantics.
- Do not publish releases or update canonical CHANGELOG state from hosted execution.
- Do not introduce TVC credentials into Actions.
- Existing candidate lifecycle/reconciliation surfaces remain separate and must be audited under their own authority if still hosted-mutating.

## Planned source

- `.github/workflows/automation-candidate-implementation.yml`
- `tools/test_automation_contracts.py`
- `tests/test_hosted_release_authority_retirement.py` only if broad hosted mutation regression can be safely generalized
- this handoff
- root CVK handoff/status where materially required

## Non-claims

No candidate is implemented, reconciled, labeled, closed, released, deployed, or activated by this source repair.

## Implemented source state

```text
automation-candidate-implementation.yml:
  name: Automation candidate implementation - Validation Only
  contents: read
  pull-requests: read
  persist-credentials: false
  candidate ID parsing: retained
  issue status/label resolution: deferred
  issue mutation: removed
  CHANGELOG mutation: removed
  git commit/push: removed
  workflow dispatch: removed
  github.token / GH_TOKEN: removed
  artifact: candidate-implementation-observation.json
  canonical_next_transition: NON_HOSTED_CANDIDATE_RECONCILIATION
  authority_effect: NONE

regression:
  tools/test_automation_contracts.py rejects hosted mutation tokens
  tests/test_hosted_candidate_authority_retirement.py enforces read-only validation boundary
  release-integrity workflow executes the dedicated regression
```

## Next executable boundary

Run exact-head hosted validation, repair any source/test defects without restoring hosted mutation authority, merge only after green evidence, then inspect adjacent candidate-lifecycle workflows separately. Candidate lifecycle state itself remains outside this hosted observer.
