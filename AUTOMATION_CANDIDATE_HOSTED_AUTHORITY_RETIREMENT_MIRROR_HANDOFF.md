# Automation Candidate Hosted Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #83
Branch: `fix/automation-candidate-hosted-authority-83`
State: CLAIMED_FOR_IMPLEMENTATION

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

## Next executable boundary

Replace hosted mutation with deterministic observation artifact generation, install fail-closed regression coverage, validate exact head, merge on green evidence, then continue audit of adjacent candidate lifecycle surfaces without duplicating ownership.
