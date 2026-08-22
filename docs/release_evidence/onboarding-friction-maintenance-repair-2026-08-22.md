# Onboarding friction maintenance repair — 2026-08-22

## Observed failure

- Repository: `StegVerse-Labs/continuity-vault-kit`
- Workflow: `Onboarding friction maintenance`
- Run: `32565770202`
- Branch/commit: `main@6245b6f`
- Job: `maintain`
- Failing step: `Ensure maintenance labels exist`
- Failure: `failed to run git: fatal: not a git repository (or any of the parent directories): .git`

The workflow invoked `gh label create` before checking out the repository and without an explicit repository context. The failure occurred before issue reconciliation or registry rebuild.

## Bounded repair

Commit `950f591c1446d975aa518ee88a524d6c1290f39e` adds job-level `GH_REPO: ${{ github.repository }}` so GitHub CLI commands have explicit repository context without requiring checkout.

No personal vault content is read or mutated. No provider, credential, release, deployment, billing, or authority boundary is broadened. Existing issue-selection and inactivity rules are unchanged.

## Verification state

`REPAIR_INSTALLED_HOSTED_PROOF_PENDING`

A fresh scheduled or manually dispatched run must complete label reconciliation, incomplete-report reconciliation, and durable-registry rebuild before this maintenance regression is considered runtime-resolved.
