# Changelog

All notable changes to the Continuity Vault Kit format will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- `schemas/conversation-event.schema.json` for canonical append-only continuity events covering claims, decisions, supersession, artifacts, implementation, authority, handoffs, and archive state
- `continuity/recall.py` with deterministic chain validation, rebuildable indexing, time-bounded recall, supersession-aware current-state selection, and archive-readiness evaluation
- canonical example-vault fixtures containing events, a context packet, memory-use receipt, multimodal-input manifest, and selected AI context
- executable recall tests and dedicated Conversation Recall Validation CI
- `docs/AUTOMATED_CONVERSATION_RECALL.md` documenting fidelity classes, command-line recall, verification roots, and archive blockers

### Improved
- normal continuity recall no longer requires manually copying a reload packet when canonical events are present
- recall results distinguish exact source, semantic reconstruction, inference, integrity-only evidence, and unavailable data
- superseded decisions are excluded from current state
- altered payloads, broken chains, duplicate event identifiers, out-of-order timestamps, and unsupported fidelity claims fail closed
- accepted goals with incomplete implementation, release, verification, or propagation evidence keep archive readiness false

### Notes
Derived indexes remain disposable and rebuildable. Recall reports provenance and fidelity but does not create authority or silently elevate reconstructed content to exact source text.

---

## [0.1.7] – 2026-07-15

### Added
- `schemas/action-execution-envelope.schema.json` binding an ACT decision to an exact connector operation, destination, resource, payload, and idempotency key
- `schemas/action-execution-receipt.schema.json` for PREPARED, EXECUTED, FAILED, and INDETERMINATE outcomes
- `execution/adapter.py` with connector-neutral request preparation, exact binding checks, receipt generation, and duplicate suppression
- Facebook `Good times!` reference envelope and execution-result fixtures
- `tools/validate_action_execution.py`, `tests/test_action_execution.py`, and dedicated Governed Action Execution Validation CI

### Improved
- EXECUTED outcomes require platform identity and confirmation evidence
- INDETERMINATE outcomes block automatic retry when duplicate side effects remain possible
- prior EXECUTED receipts suppress duplicate execution and return the existing result
- confirmed FAILED outcomes may retry only the exact same envelope
- release handoff and downstream propagation evidence now identify published `v0.1.6`

### Notes
Connectors execute authority supplied by a valid envelope; they do not create, broaden, reinterpret, or retain authority. This implementation contains no live Facebook integration or platform credentials.

---

## [0.1.6] – 2026-07-15

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
