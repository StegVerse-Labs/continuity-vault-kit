state: active
works_today: yes — use the verified initializer or copy the template directly; no accounts, services, or lock-in
current_version: 0.1.2
current_focus: complete the automatic 0.1.3 publication cycle using source-SHA ancestry, durable outcome receipts, and bounded self-recovery
known_gaps:
  - Some docs may be reorganized as StegVerse expands
  - Data-sharing revenue behavior is documented but not implemented
  - No real onboarding-friction reports have yet crossed the automation-candidate threshold
  - The latest observed release-cycle receipt remains INCOMPLETE until the corrected workflow publishes or records a newer outcome
completed_recently:
  - Published automated verified release v0.1.2 at commit 5e38ca635ed420a3800ca53dd59f236175207edb
  - Added repository-native release, evidence, initializer, downstream-propagation, report-maintenance, and candidate-lifecycle automation
  - Replaced historical issue gates with changelog-driven release state and durable release_required evidence
  - Connected supported merged candidate fixes to idempotent Unreleased changelog recording and verified publication
  - Added release-cycle outcome receipts for PUBLISHED, SKIPPED, FAILED, INCOMPLETE, and RECONCILED states
  - Moved publication eligibility out of the job-level predicate and into an observable gate step
  - Replaced unreliable event and pull-request metadata filters with a Git ancestry check requiring the source integrity SHA to be contained in main
  - Added .github/workflows/release-cycle-recovery.yml for one bounded recovery dispatch per distinct incomplete source run
  - Added docs/release_evidence/recovery_state.json to suppress duplicate recovery loops
next_steps:
  - Treat docs/release_evidence/latest.json as the machine-readable integrity and release-required gate
  - Treat docs/release_evidence/latest_release.json as the latest successful publication receipt
  - Treat docs/release_evidence/latest_cycle.json as the authoritative latest release-cycle outcome
  - Treat docs/release_evidence/recovery_state.json as the bounded recovery source of truth
  - Allow the ancestry-gated workflow chain to publish the substantive Unreleased state as the next verified patch release
  - Allow three matching reports to create, independently validate, implement, record, and publish the smallest supported correction automatically
  - Keep first-contact use independent of accounts, hosted services, mandatory SDKs, and vault telemetry
last_reviewed_utc: 2026-07-14T15:50:00Z
