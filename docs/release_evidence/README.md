# Release Evidence Records

This directory contains repository-native receipts produced by the release-integrity workflow.

## Generated records

- `latest.md` — human-readable summary of the most recent successful `main` validation run.
- `latest.json` — machine-readable receipt for that run.

These files are generated and committed automatically by `.github/workflows/release-integrity.yml`. They must not be edited by hand to claim a successful validation.

A receipt records the tested commit, workflow run, artifact name, package digest, manifest schema, file count, version, and validation result. The uploaded GitHub Actions artifact remains the retained copy of the generated ZIP and sidecars.

## Scope boundary

A successful receipt verifies packaging integrity for the tested repository state. It does not certify the truth, safety, completeness, authority, or admissibility of user-authored vault content.
