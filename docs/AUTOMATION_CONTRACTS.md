# Repository Automation Contracts

This document defines the minimum conditions that repository automation must preserve.

The executable source is `tools/test_automation_contracts.py`. Release validation and automated candidate publication run that test before a release may proceed.

## Release contracts

- Release tooling, vault initialization, and automation-contract tests must pass before publication.
- Release artifacts remain the ZIP, SHA-256 sidecar, and expanded manifest sidecar.
- Evidence receipts must describe their limited verification scope.
- Package or copy verification must never be presented as certification of user-authored content.

## Onboarding-friction contracts

- Reports enter only through an explicit GitHub issue form; no vault telemetry is permitted.
- The form must prohibit private vault content and unnecessary sensitive information.
- The durable registry must expose its schema version, report count, threshold, signature counts, reports, and privacy scope.
- The automation-candidate threshold remains three matching normalized reports unless the registry, workflows, documentation, and tests are changed together.
- Incomplete reports are not product evidence.

## Candidate contracts

- Candidate support must be reconstructed from the durable registry.
- Labels or issue titles alone do not grant implementation authority.
- Duplicate signatures preserve one canonical candidate.
- A merged pull request completes a candidate only when it explicitly references a currently supported candidate.
- A supported candidate permits only the smallest repository-native correction demonstrated by the evidence.
- Candidate automation never authorizes access to or mutation of user vault content.

## Downstream contracts

The automated propagation registry must continue to cover exactly these four destinations:

- `StegVerse-Labs/Site`
- `GCAT-BCAT-Engine/Publisher`
- `StegVerse-Labs/admissibility-wiki`
- `StegVerse-002/stegguardian-wiki`

A downstream update is required only when a destination already publishes a direct kit, release, install, download, compatibility, or mirror claim that would become stale.

## Change rule

A change that intentionally alters one of these contracts must update all affected workflows, evidence schemas, documentation, and `tools/test_automation_contracts.py` in the same change set.

---

🔒 Layer: Framework | KV
