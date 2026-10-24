# Workflow surface mirror handoff — G17 consolidation (continuity-vault-kit)

Goal: G17-WORKFLOW-SURFACE-MINIMIZATION (StegVerse-Labs/.github#167/#168), enforced
retroactively under Rigel's 2026-10-24 direction (StegVerse-org/.github#166).
Folded from commit bcc2d75 (main).

## Surface: 56 workflows → 2

| Surface | Classification | Triggers | Runs |
|---|---|---|---|
| `.github/workflows/validation-dispatcher.yml` | KEEP_STABLE_DISPATCHER | pull_request, push (main); no path filter | every catalog group declaring the event (matrix), plus the release readiness chain as four jobs |
| `.github/workflows/release-lifecycle.yml` | KEEP_STABLE_DISPATCHER (lifecycle) | release: published | catalog groups declaring `release` (build-and-attach-release, downstream-propagation, release-assets) |

The `release` trigger on `.github/workflows/release-lifecycle.yml` is recorded in
`control/workflow-surface-registry.json` (`lifecycle_trigger`) as pending owner approval.
It is the second of two surfaces, not a third-workflow exception.

## How checks are preserved

- `tools/tasks/task_catalog.json`: one group per folded job; step bodies are the original
  run blocks byte for byte, pinned by sha256 (`run_catalog.py verify` refuses drift).
- `tools/tasks/folded/<file>.yml`: the verbatim record of every original workflow
  (non-executing). `tests/test_folded_workflow_records.py` proves each consolidated
  record's run blocks equal its catalog step bodies. The content contracts in
  `tools/test_automation_contracts.py` and the `*_retirement` tests now read these
  records; the authority-marker scans also cover the live surfaces and every step body.
- Release readiness chain: `workflow_run` on display names (Release integrity →
  Automated release readiness → Release cycle outcome → Release cycle recovery) became
  dispatcher jobs chained by `needs`, each keyed on its upstream job's result
  (`CATALOG_UPSTREAM_CONCLUSION`); `workflow_run.head_sha`/`id` render as this run's
  `GITHUB_SHA`/`GITHUB_RUN_ID`.
- Path filters dropped: groups run on every event (superset). `kv-format-branch`
  (push to `format/**`) runs on pull_request. `release-assets` (push tags `v*`) runs on
  release published.

## Pending (not run until decided)

- TRANSFER_TO_STEGVERSE_WORKER (pending): automation-candidate-lifecycle (issues +
  schedule), onboarding-friction-maintenance (schedule), onboarding-friction (issues),
  sync-knowledgevault-overlay-from-stegdb (schedule), sync-overlay-from-stegdb (schedule).
- FAIL_CLOSED (pending): production-provider-activation (dispatch-only;
  hashicorp/setup-terraform removed, not reintroduced), one_button_release (dispatch-only),
  dispatch input modes of release-assets / downstream-propagation /
  reconcile-published-release / provider-readiness.

Each record carries the six fields in `control/workflow-surface-registry.json`.

## Carried from open pull requests (so they can drop their workflow-file changes)

| PR | Catalog entry |
|---|---|
| #260 | `runtime-import-and-secret-policy.guard.pr260` (selected when its `.stegverse/` finish-point files are present) |
| #261 | `runtime-import-and-secret-policy.guard.pr261` (selected when the parity files are present) |
| #262 | `kv-guardrails.kv-guardrails` step "Guardrail repair guidance" (`if: always()`, JOB_STATUS gate) |
| #265 | `kv-ranged-sha256-measurement.validate.py310/py312/py313` (NOT_SELECTED until `runtime/ranged_sha256_measurement.py` exists) |
| #267 | `skap-loader-tests.skap-loader-tests` (node 22); loader step + Setup Node removed from `kv-guardrails.kv-guardrails` |

The base group `runtime-import-and-secret-policy.guard` stays selected until
`.stegverse/finish_point_verdict.py` lands.

## Owner

Single owner of this repository's workflow surface while the consolidation PR is open
(StegVerse-org/.github#166). Open decisions for Rigel: the release lifecycle trigger,
transferred schedules/issue triggers, dispatch-only modes, the terraform removal.
