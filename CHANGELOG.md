# Changelog

All notable changes to the Continuity Vault Kit format will be documented in this file.

The format is based on [Semantic Versioning](https://semver.org/).

---
## [Unreleased]

### Added
- `docs/EXAMPLES.md` as the stable index for small continuity patterns and reload-packet examples
- `docs/examples/Project_Continuation_Packet.md` as a tooling-independent project handoff with explicit evidence and mutation boundaries
- `docs/examples/Device_Migration_Packet.md` as a tooling-independent transfer packet with source authority, reconciliation, rollback, and owner acceptance
- `docs/RELEASE_CANDIDATE_CHECKLIST.md` defining entry conditions, change classification, migration review, candidate verification, tagging, and downstream checks
- `vault_template/KnowledgeVault/_migration/README.md` defining non-destructive migration and replacement behavior
- `tools/test_release_tools.py` for end-to-end release tooling self-tests
- `.github/workflows/release-integrity.yml` to run the release self-test, rebuild and verify artifacts, validate manifest shape, and upload evidence

### Improved
- README now exposes the examples path during first-contact repository review
- Documentation now distinguishes release integrity verification from the truth, safety, or completeness of user-authored content
- Release manifests now include schema version, file count, and per-file size and SHA-256 records
- Release verification now requires both sidecars and validates artifact identity, archive paths, required files, and every packaged file hash
- Release building now validates required source files before creating an artifact and reports failures with non-zero status
- Release sequencing is now durably divided across issues #7, #8, #9, and #10

### Notes
The migration README adds a file to the vault template but does not require existing `0.1.x` users to reorganize their vaults. The release tooling changes require newly built manifests to use the expanded file inventory before the next release is tagged. GitHub Actions execution evidence remains required before tagging.

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
