# Onboarding Friction Hosted Control-Plane Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #85
Branch: `main`
State: MERGED_VALIDATED_HOSTED_CONTROL_PLANE_RETIRED

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

## Implemented source state

```text
onboarding-friction.yml: read-only current-event classifier + artifact
onboarding-friction-maintenance.yml: read-only durable-registry projection + artifact
onboarding-friction-bootstrap.yml: read-only expected-label vocabulary validation + artifact
automation-candidate-lifecycle.yml: read-only candidate-state projection + artifact

issue mutation: removed
label mutation: removed
repository writeback: removed
workflow dispatch: removed
github.token / GH_TOKEN: removed
credential persistence: false
threshold semantics: 3 retained
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
authority_effect: NONE
```

Regression:
- `tools/test_automation_contracts.py` rejects hosted mutation/token authority across all four surfaces.
- `tests/test_hosted_onboarding_control_plane_retirement.py` enforces read-only behavior and threshold preservation.
- Release Integrity executes the dedicated regression.

## Next executable boundary

Run exact-head validation; repair source/test defects without restoring hosted mutation authority; merge only after green evidence. Then scan remaining workflows for hosted mutation authority and continue only through a new bounded handoff if a distinct surface remains.


## Merge and validation evidence

```text
PR: #89
validated head: 017cd46ada5257ad2d2c44c966b4f60b9f9c0dd1
merge: 05125a75c4dddb42b3de2b70201dcd99eed368a1

Release integrity: 33135922653 SUCCESS
Repository validation diagnostics: 33135922657 SUCCESS
Security Baseline: 33135922517 SUCCESS
KV Guardrails: 33135922600 SUCCESS
```

All four coupled workflows are now read-only validation/evidence transport. Threshold=3 semantics remain intact. No issue, label, repository, workflow-dispatch, token, release, deployment, or activation authority was granted.

## Current next boundary

Issue #85 source-retirement goal is COMPLETE. Continue repository-wide inspection for any distinct hosted mutation authority not already covered by #78/#82/#84/#89. Production KV runtime deployment, live InTr boundary/readback, TVC owner ingress, provider execution, and TVC release publication remain separate open runtime gates.
