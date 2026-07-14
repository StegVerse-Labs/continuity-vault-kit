# Changelog

All notable changes to the Continuity Vault Kit format will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- `.github/ISSUE_TEMPLATE/onboarding-friction.yml` for structured, privacy-bounded first-use and setup reports
- `.github/workflows/onboarding-friction-bootstrap.yml` to create required triage labels automatically
- `.github/workflows/onboarding-friction.yml` to classify reports, provide path-specific guidance, maintain durable evidence, and create threshold-based automation candidates
- `.github/workflows/onboarding-friction-maintenance.yml` for scheduled label repair, incomplete-report reminders, abandoned-report closure, and registry reconciliation
- `.github/workflows/automation-candidate-lifecycle.yml` to verify candidate support, suppress duplicates, maintain evidence packets, and close completed candidates
- `.github/workflows/automation-candidate-implementation.yml` to detect merged fixes for supported candidates, complete their lifecycle, record the correction in `CHANGELOG.md`, and activate verified publication
- `tools/test_automation_contracts.py` to validate workflow presence, required triggers and permissions, evidence schemas, threshold consistency, privacy boundaries, downstream destination coverage, and the candidate-to-release bridge
- `docs/AUTOMATION_CONTRACTS.md` as the readable contract for release, friction, candidate, and downstream automation
- `evidence/onboarding-friction/` as the human-readable and machine-readable friction registry
- `evidence/onboarding-friction/candidates/` as durable per-candidate evidence and lifecycle receipts

### Improved
- Repeated onboarding failures now become automation-candidate issues automatically after three reports share the same platform, setup-path, and failure-stage signature
- Setup reports no longer require manual labeling, categorization, initial guidance, evidence aggregation, escalation, reminder follow-up, or stale-report cleanup
- Incomplete reports receive an automated reminder after seven inactive days and close after thirty inactive days without being treated as product evidence
- Candidate admission no longer requires manual threshold review; the workflow checks the durable registry and applies supported or insufficient-evidence state
- Duplicate candidates are linked to the earliest canonical issue and closed automatically
- Merged pull requests that explicitly fix supported candidates now mark implementation complete, preserve evidence, add an idempotent Unreleased changelog entry, and trigger release-integrity validation
- Release-integrity and automated-release workflows now block publication when repository automation contracts drift
- Release evidence receipts now record the automation-contract test result and its limited verification scope
- The release cycle derives state from substantive Unreleased content and no longer depends on historical issue numbers
- Onboarding evidence explicitly prohibits private vault content, credentials, recovery material, and unnecessary personal information

### Notes
This automation observes repository issue and pull-request records only. It does not add telemetry to user vaults, phone home, authorize vault mutation, or make an account or hosted service necessary. Automatically closed reports may be edited and reopened when privacy-safe reproduction details become available. A supported candidate authorizes only the smallest repository-native correction demonstrated by the evidence. Automation contract validation verifies repository consistency only; it does not certify user-authored content.

---

## [0.1.2] – 2026-07-14

### Added
- `docs/EXAMPLES.md` as the stable index for small continuity patterns and reload-packet examples
- `docs/examples/Project_Continuation_Packet.md` as a tooling-independent project handoff with explicit evidence and mutation boundaries
- `docs/examples/Device_Migration_Packet.md` as a tooling-independent transfer packet with source authority, reconciliation, rollback, and owner acceptance
- `docs/examples/Health_Record_Chronology.md` separating dated source records, facts, interpretations, and qualified-review boundaries
- `docs/examples/Research_Evidence_Review.md` separating sources, supported observations, interpretations, conflicts, and evidence gaps
- `docs/examples/Multi_Session_AI_Collaboration.md` preserving accepted state separately from AI-session proposals
- `docs/examples/Version_Replacement_and_Migration.md` demonstrating non-destructive adoption of a newer kit
- `docs/RELEASE_CANDIDATE_CHECKLIST.md` defining entry conditions, change classification, migration review, candidate verification, tagging, and downstream checks
- `docs/release_evidence/README.md` defining workflow-generated human-readable and machine-readable validation receipts
- `vault_template/KnowledgeVault/_migration/README.md` defining non-destructive migration and replacement behavior
- `tools/test_release_tools.py` for end-to-end release tooling self-tests
- `.github/workflows/release-integrity.yml` to run validation, upload artifacts, commit durable evidence receipts, close issue #7, and activate issue #8
- `.github/workflows/automated-release.yml` to select the patch version, verify the candidate, tag it, publish release assets, close issue #8, and activate issue #10

### Improved
- README now exposes the examples path during first-contact repository review
- Documentation now distinguishes release integrity verification from the truth, safety, or completeness of user-authored content
- Release manifests now include schema version, file count, and per-file size and SHA-256 records
- Release verification now requires both sidecars and validates artifact identity, archive paths, required files, and every packaged file hash
- Release building now validates required source files before creating an artifact and reports failures with non-zero status
- Successful main-branch integrity runs now preserve evidence and route successor work without manual copying or issue transitions
- The complete planned continuity-example set is now indexed and issue #9 is complete

### Notes
The migration README and examples add files without requiring existing `0.1.x` users to reorganize their vaults. The automated release path therefore classifies this batch as a backward-compatible patch release. A tag is created only after candidate build and verification succeed.

---

## [0.1.1] – 2026-01-31

### Added
- iOS setup guide (`docs/IOS_SETUP.md`) for Obsidian, Pretext, and Working Copy workflows
- GitHub Issue templates for:
  - Setup Help
  - Bug Reports
  - Feature Requests
- Public repository privacy boundary documentation (`SAFETY.md`)
- README guidance for mobile-first KnowledgeVault users

### Improved
- Clearer separation between **public starter kit** and **private personal vaults**
- Better onboarding path for new users cloning the repository
- More explicit iPhone/iPad usage recommendations

### Notes
This release does **not** change the vault format structure.  
It improves usability, onboarding, and safety documentation only.

---

## [0.1.0] – 2026-01-27
### Added
- Initial KnowledgeVault folder structure
- Index system for AI and human navigation
- Policy documentation for naming, intake, retention, and AI access
- Vault manifest format
- Build tooling to package portable vault releases
- GitHub Actions workflow for automated release builds

### Notes
This is the first stable format version of the KnowledgeVault system.
Future versions should remain backward-compatible whenever possible.
