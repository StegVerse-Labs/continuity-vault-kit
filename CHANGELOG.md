# Changelog

All notable changes to the Continuity Vault Kit format will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- `schemas/delegation-policy.schema.json` defining direct instructions and revocable standing delegations
- `delegation/decision.py` with ACT, ASK, and DENY authority outcomes
- proposal-only onboarding and user-readable governance-profile rendering
- canonical authority, dialogue, and delegation-lifecycle fixtures
- executable accept, narrow, expand, reject, revoke, and expire transitions with immutable lineage receipts
- `schemas/delegation-transition-receipt.schema.json`
- mutually accepted relationship declarations recording user responsibilities, AI responsibilities, declared limitations, and renegotiation triggers
- dedicated Progressive Delegation Validation workflow and tests

### Improved
- clear user instructions and valid standing preferences authorize covered actions without repetitive per-item confirmation
- repeated behavior can produce a reviewable proposal but cannot silently expand authority
- lifecycle changes preserve source and result hashes, actor, reason, time, and acceptance basis
- fair agency is represented as reciprocal declared responsibility while the user retains originating authority over user-controlled resources

### Notes
Governance exists to make delegated action safe, attributable, bounded, revocable, and usable. Technical access does not create authority. No undeclared outbound transmission prevents unauthorized communication but does not prohibit user-authorized publishing, sharing, synchronization, or connected-service use.

---

## [0.1.5] – 2026-07-15

### Added
- `docs/STORAGE_BUDGET_AND_ADAPTIVE_CAPTURE_POLICY.md` defining governed reconstruction goals, material-property requirements, explicit capacity budgets, sensor substitution, adaptive sampling, fidelity elevation, exhaustion behavior, and capability-loss receipts
- `schemas/storage-budget-policy.schema.json` as the machine-readable storage-budget and adaptive-capture contract
- Four reference policies covering semantic recall, spatial/object-state recall, approximate experiential playback, and protected evidentiary preservation
- `tools/validate_storage_budget_policy.py` and `tests/test_storage_budget_policy.py` enforcing required-property coverage, allocation limits, substitution consistency, receipt requirements, and exhaustion behavior
- `multimodal_storage/budget_planner.py` and `tests/test_budget_planner.py` providing an advisory-only capture-plan analysis that cannot activate sensors, mutate retention, purchase capacity, or grant authority
- `docs/STORAGE_BUDGET_EXPERIENCE_CAPSULE_MAPPING.md` binding policy streams and capability-loss states to the existing ExperienceCapsule contract
- `.github/workflows/storage-budget-policy.yml` as the dedicated validation gate for storage-budget policies and planner behavior

### Improved
- Capacity pressure may reduce preferred properties only; required-property loss now forces an explicit capability-loss declaration
- Replication, continuity-receipt reserve, protected evidence, archival allocation, and temporary buffers are accounted for separately
- `RECONCILED` release-cycle receipts may identify the reconciliation workflow while all other outcomes remain bound to the automated release workflow
- Repository authority boundaries distinguish unauthorized action from valid direct or standing delegation

### Notes
The storage-budget layer is advisory and policy-bound. It does not establish surveillance authority, control sensors, grant protected-evidence access, purchase storage, or imply that cheaper compute removes physical storage cost. Generated reconstruction remains distinct from original evidence.

---

## [0.1.4] – 2026-07-15

### Added
- `docs/FIDELITY_GOVERNED_MULTIMODAL_STORAGE.md` defining artifact-class separation, transcription-only voice recall, multimodal fidelity transitions, sparse reconstruction, sensor substitution, and reconstruction-completeness requirements
- `schemas/experience-capsule.schema.json` as the machine-readable contract for governed multimodal episodes, streams, consent transitions, retention policy, reconstruction rights, missing evidence, and fidelity transitions
- Four reference capsules covering transcription-only voice, protected audio evidence, sparse video reconstruction, and materially incomplete ambient capture
- `tools/validate_experience_capsule.py` and `tests/test_experience_capsule.py` to enforce generated-content labeling, ephemeral payload restrictions, voice-recall boundaries, fidelity-loss declarations, and completeness consistency
- `multimodal_storage/adapter.py` and `tests/test_multimodal_storage_adapter.py` to authorize canonical text and derived recall without granting protected raw-media access by implication
- `.github/workflows/fidelity-governed-storage.yml` as the dedicated executable validation gate for the multimodal storage contract
