# Changelog

All notable changes to the Continuity Vault Kit format will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- private-KV canonical conversation-event store using the existing append-only recall chain, compare-and-swap persistence, exact readback verification, secret/transcript rejection, and persistent-session verification-root binding
- persistent-session reconstruction checkpoints bound to the existing append-only conversation-recall chain, with monotonic predecessor hashing, live-verification requirements, authority non-transfer, secret/transcript rejection, and private-KV Sessions guidance
- KV-INTERLOCK-v1 persistent-session read/candidate adapters that return bounded reconstruction context, stage only validated monotonic successors, bind current/successor/recall hashes, and fail closed on stale or ambiguous state
- governed KV-to-Publisher document export preparation with owner-scoped formats, provenance/fidelity classes, owner-approved redaction, deterministic receipts, revocation evidence, and fail-closed tests
- governed KnowledgeVault email-continuity ingress contract with pre-admission staging, fail-closed admission decisions, SKAP Vault credential-reference binding, deterministic mailbox mapping, and source-ready runtime validation
- provider-neutral email account mapping runtime that prohibits raw mailbox secrets in KV state and requires `skap://` binding before provider-session verification
- documented-unverified Gmail, Microsoft Graph/Outlook, and iCloud Mail provider adapter metadata with minimum read access, explicit user authorization, SKAP Vault credential destination, and fail-closed unknown-domain handling
- multi-email personal contact profile under `_Entities/Self`, allowing multiple independently mapped email addresses with one optional primary display address and per-address email-continuity state
- fail-closed `KV-INTERLOCK-v1` runtime endpoint core with exact DEVICE→KV InTr admission binding, injected authority/policy/storage boundaries, bounded-context enforcement, deterministic receipts, and candidate-only `COMMIT_CANDIDATE` semantics
- deterministic runtime endpoint tests and canonical runtime handoff for the Site/KV production backend seam

### Security
- retired GitHub-hosted release/publication and release-control-plane mutation authority from the CMC-022/CMC-023 workflow set
- retired residual `release-integrity.yml` evidence writeback and `automated-release.yml` VERSION/changelog/tag/GitHub-release mutation authority; hosted release workflows now validate and transport non-secret evidence only
- retired `automation-candidate-implementation.yml` hosted issue/repository/workflow-dispatch mutation authority; merged-PR candidate references are now emitted only as non-authorizing observation evidence
- retired the coupled onboarding-friction triage/maintenance/bootstrap and candidate-lifecycle hosted control plane; classification and threshold projections now emit non-authorizing artifacts without issue, label, repository, workflow-dispatch, or token authority
- retired GitHub-OIDC production-provider activation authority; hosted provider workflow now validates IaC source only and defers cloud identity/provisioning/apply to TVC-admitted resident execution
- retired residual hosted release reconciliation/downstream mutation and retry-dispatch authority; release/downstream workflows now emit non-authorizing observations and defer canonical transitions to TV/TVC/non-hosted owners
- retired hosted StegDB overlay writeback; scheduled/manual overlay workflows now build hash-verifiable candidate trees and patches as artifacts without committing or pushing canonical CVK state
- retired hosted KV format-branch writeback; auto-footer formatting now produces a validated candidate patch artifact without branch commits or pushes
- added a repository-wide hosted workflow non-authority invariant across all 38 workflows; every workflow must declare explicit permissions and any write/token/OIDC/cloud-mutation marker fails validation
- preserved TV/TVC as the only credential/release authority; no successor release is claimed until an admitted TVC publication path actually runs

### Notes
- governed document-export source is merged and validated; the four `_System/Exports/` template files are installed and exact-readback observed in the connected KnowledgeVault, while owner request, InTr transport, Publisher rendering, artifact readback, and retained private-bundle reconstruction remain unobserved
- production KV endpoint deployment, live InTr boundary identity/sealing, canonical Site readback, SKAP owner ingress, provider execution, and TVC release publication remain separate runtime evidence gates

---

## [0.1.9] – 2026-08-03

### Added
- executable Federal Floor Plus security policy in `SECURITY.md` and `security/security-baseline.v1.json`
- deterministic `tools/security_baseline_check.py` validator and dedicated Security Baseline CI workflow
- durable security execution and claim record in `docs/SECURITY_BASELINE_EXECUTION.md` and the canonical mirror handoff

### Improved
- applicable U.S. federal cybersecurity requirements are treated as the minimum engineering floor rather than the target ceiling
- repository automation fails closed when required policy or evidence is unavailable
- least-privilege workflow permissions, release provenance, manifests, SHA-256 evidence, and durable outcome receipts are explicitly enforced
- user-authored iCloud KnowledgeVault content remains outside repository automation authority and cannot be silently replaced
- delegated authority must be explicit, revocable, scoped, attributable, and limited to the smallest evidence-supported repository correction

### Notes
This is an executable engineering baseline, not a federal certification, authorization, accreditation, or compliance attestation. Personal-vault initialization or migration remains a separate owner-approved action with dry-run and receipt requirements.

---

## [0.1.8] – 2026-07-17

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
- deterministic dialogue reconstruction for agreed user/AI positions
- execution-readiness checks for reconstructed agreements
- evidence-aware recall of accepted, rejected, superseded, and unresolved proposals

### Improved
- unresolved or contradictory dialogue cannot silently become executable authority
- reconstructed agreements retain source-event provenance and confidence boundaries

### Notes
Dialogue reconstruction is evidentiary support only. It does not independently grant authority.
