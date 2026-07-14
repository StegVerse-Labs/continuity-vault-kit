state: active
works_today: yes — use the verified initializer or copy the template directly; no accounts, services, or lock-in
current_version: 0.1.2
current_focus: preserve the complete evidence-to-fix lifecycle while blocking release when automation contracts drift
known_gaps:
  - Some docs may be reorganized as StegVerse expands
  - Data-sharing revenue behavior is documented but not implemented
  - No real onboarding-friction reports have yet crossed the automation-candidate threshold
completed_recently:
  - Published automated verified release v0.1.2 at commit 5e38ca635ed420a3800ca53dd59f236175207edb
  - Closed release issues #7 and #8, example issue #9, and downstream issue #10
  - Added repository-native release, evidence, initializer, downstream-propagation, report-maintenance, and candidate-lifecycle automation
  - Added tools/test_automation_contracts.py for workflow, evidence-schema, threshold, privacy, scope, and destination validation
  - Added docs/AUTOMATION_CONTRACTS.md as the readable automation contract
  - Integrated automation-contract validation into release-integrity and automated-release workflows
  - Expanded release receipts to record automation-contract validation and its limited scope
next_steps:
  - Treat evidence/onboarding-friction/latest.json as the report-level source of truth
  - Treat evidence/onboarding-friction/candidates/ as the candidate-level source of truth
  - Block publication if release, friction, candidate, downstream, privacy, or threshold contracts drift
  - Allow three matching reports to create and independently validate a supported candidate automatically
  - Allow merged pull requests that explicitly fix supported candidates to complete and close the lifecycle automatically
  - Keep all corrections limited to the smallest demonstrated repository-native fix
  - Keep first-contact use independent of accounts, hosted services, mandatory SDKs, and vault telemetry
last_reviewed_utc: 2026-07-14T08:20:00Z
