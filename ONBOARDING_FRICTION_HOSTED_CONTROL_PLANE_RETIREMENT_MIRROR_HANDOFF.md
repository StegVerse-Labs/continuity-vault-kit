# Onboarding Friction Hosted Control-Plane Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #85
Branch: `fix/onboarding-friction-hosted-control-plane-85`
State: CLAIMED_FOR_IMPLEMENTATION

## Goal

Retire hosted issue/repository/workflow mutation authority across the four coupled onboarding-friction/candidate-lifecycle workflows while preserving deterministic classification and evidence projection.

## Canonical affected surfaces

- `.github/workflows/onboarding-friction.yml`
- `.github/workflows/onboarding-friction-maintenance.yml`
- `.github/workflows/onboarding-friction-bootstrap.yml`
- `.github/workflows/automation-candidate-lifecycle.yml`

Issue #83 / PR #84 already retired `automation-candidate-implementation.yml`; this lane does not reopen it.

## Live contradiction

Current main includes combinations of:

```text
issues: write
contents: write
actions: write
github.token / GH_TOKEN
gh label create
gh issue edit/comment/create/close
git commit
git push
gh workflow run
```

These hosted mutation surfaces are incompatible with the current StegVerse contract.

## Required state

```text
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
credential authority: TV/TVC
permissions: read-only
credential persistence: false where checkout exists
issue mutation: false
label mutation: false
repository mutation: false
workflow dispatch: false
candidate lifecycle authority: NONE
friction lifecycle authority: NONE
authority_effect: NONE
```

Hosted workflows may:
- classify the current issue event deterministically from its provided metadata/body;
- validate or summarize already-durable repository evidence;
- calculate threshold/candidate projections without making them canonical;
- upload non-secret short-lived observation artifacts.

Hosted workflows may not:
- query with a privileged token and then mutate issues;
- create/update labels;
- create/close/comment/edit issues;
- commit or push evidence/CHANGELOG state;
- dispatch another workflow;
- infer that an observation is a canonical lifecycle transition.

## Collision boundary

Do not change the threshold value or candidate signature semantics. Do not create a second friction registry or candidate registry. Durable lifecycle ownership must be separately admitted to a non-hosted sovereign path if needed.

## Planned source

- four workflow files above
- `tools/test_automation_contracts.py`
- dedicated hosted onboarding-control regression tests
- Release integrity regression execution
- root CVK handoff/CHANGELOG where materially needed

## Non-claims

No real issue is triaged, labeled, reminded, closed, created, or reconciled by this repair. No user vault content is read or mutated. No release, deployment, provider execution, or activation is produced.

## Next executable boundary

Implement read-only observation workflows, enforce regression checks, validate exact head, merge only on green evidence, then inspect any remaining hosted mutation surfaces separately.
