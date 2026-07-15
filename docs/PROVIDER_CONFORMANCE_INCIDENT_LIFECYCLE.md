# Provider Conformance Incident Lifecycle

A drift finding is not merely informational. Any non-empty provider drift report opens a durable incident and removes activation readiness until a successor baseline is explicitly issued.

## State sequence

`DETECTED -> QUARANTINED -> REVOKED -> REMEDIATING -> REATTESTING -> RESOLVED`

A failed re-attestation returns to `REMEDIATING`. No other backward transition is allowed.

## State meaning

- **DETECTED** — a committed drift report identifies provider identity, capability, evidence, freshness, profile, role-coverage, or probe failure.
- **QUARANTINED** — new reconstructive-memory activation decisions are blocked while evidence is preserved.
- **REVOKED** — the prior deployment receipt and baseline no longer confer current readiness.
- **REMEDIATING** — the operator repairs or replaces the affected provider without mutating the historical incident.
- **REATTESTING** — all six providers are probed again and a new conformance report is assembled.
- **RESOLVED** — only a newly committed baseline and deployment receipt may restore readiness.

## Resolution boundary

Resolution requires both:

1. `successor_baseline_commitment`
2. `successor_receipt_commitment`

A successful probe by itself cannot close the incident. A prior deployment receipt cannot be reused after drift. Failed re-attestation returns the incident to remediation and keeps readiness blocked.

## Evidence discipline

Every transition records:

- incident identifier;
- actor;
- transition timestamp;
- evidence commitment;
- optional bounded note;
- full ordered event history;
- deterministic incident commitment.

Incident evidence must not include credentials, bearer tokens, private keys, raw chat, reconstructed plaintext, or protected memory content.

## Operational rule

Open incidents block readiness. Historical incidents remain immutable after resolution. A successor baseline starts a new continuity period rather than rewriting the previous one.
