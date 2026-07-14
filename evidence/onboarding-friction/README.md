# Onboarding Friction Evidence

This directory is maintained by `.github/workflows/onboarding-friction.yml`.

It records structured, privacy-bounded setup friction reported through `.github/ISSUE_TEMPLATE/onboarding-friction.yml`.

Generated files:

- `latest.json` — machine-readable report registry and signature counts.
- `latest.md` — human-readable summary.

The workflow classifies reports by platform, setup path, and failure stage. When at least three reports share the same signature, it creates an `automation-candidate` issue automatically.

This evidence must not contain private vault content, credentials, recovery material, or unnecessary personal information. A repeated signature justifies investigation; it does not authorize mutation of user vaults or expansion of package-integrity claims.
