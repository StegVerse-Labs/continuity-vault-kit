# Security Policy

## Security posture

Federal cybersecurity requirements are treated as the minimum acceptable floor. This repository applies a **Federal Floor Plus** profile: repository-native controls must meet the intent of NIST CSF 2.0, NIST SP 800-218 SSDF 1.1, relevant NIST SP 800-53 Rev. 5 control families, and CISA Secure by Design guidance, while adding stronger local boundaries where the kit handles continuity, provenance, release integrity, and personal-vault separation.

This is not a certification claim. Compliance and authorization depend on deployment context, system categorization, operating environment, and independent assessment.

## Enforced repository controls

- Least-privilege workflow permissions; read-only is the default.
- Fail-closed validation when required policy, evidence, manifests, or receipts are missing.
- Deterministic build, manifest, checksum, release, and release-cycle evidence.
- Protected distinction between public framework files, runtime templates, and user-authored private vault content.
- No workflow may inspect, collect, upload, migrate, overwrite, or mutate a user's personal iCloud KnowledgeVault.
- Canonical machine-readable security requirements in `security/security-baseline.v1.json`.
- CI validation through `tools/security_baseline_check.py` and `.github/workflows/security-baseline.yml`.
- Security-relevant changes require a pull request and inspectable workflow evidence before merge.
- Generated artifacts and derived indexes never replace canonical source records.
- Missing provenance, integrity, authority, or fidelity evidence must be reported honestly rather than inferred as success.

## Vulnerability reporting

Do not place secrets, credentials, private-vault content, health records, financial records, identity documents, or exploit details in a public issue. Use GitHub's private security reporting surface when enabled. Until a private reporting channel is verified, report only that a vulnerability exists and request a private contact path without including sensitive technical details.

## Release security

A releasable change must preserve:

1. executable release-tool self-tests;
2. initializer self-tests;
3. automation-contract validation;
4. KV layer and emoji guardrails;
5. security-baseline validation;
6. release archive, manifest, SHA-256 evidence, and release-cycle receipts;
7. explicit separation between repository validation and any claim about user-authored content.

## Personal-vault repair boundary

Repository green status authorizes use of the kit as a verified source package. It does **not** authorize unattended mutation of an existing personal vault. Repair or restart of an iCloud KnowledgeVault must use a new destination or an owner-approved migration, preserve the existing vault as read-only evidence until acceptance, generate an installation or migration receipt, and never silently overwrite owner-authored content.

---

🔒 Layer: Framework | KV
