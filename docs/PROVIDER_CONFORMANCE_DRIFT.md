# Continuous Provider Conformance

Production activation is not permanent authority. It remains valid only while the active provider profile and all required provider observations continue to match the committed activation baseline.

## Baseline

The baseline binds:

- the activated provider-profile commitment;
- exactly one observation for each required provider role;
- each provider resource identity;
- each tested capability;
- each evidence commitment;
- the baseline creation time.

## Drift classes

The monitor emits deterministic findings for:

- provider-profile commitment changes;
- missing or duplicate roles;
- provider resource-identity changes;
- capability expansion or contraction;
- evidence-commitment changes;
- failed probes;
- stale or future-dated observations;
- malformed timestamps and unexpected roles.

Any finding changes the decision to `FAIL_CLOSED`.

## Recovery

A drifted deployment does not regain readiness merely because a later probe succeeds. Recovery requires a new verified conformance report and a new deployment receipt that establishes a successor baseline. Prior activation and drift receipts remain preserved.

## Evidence boundary

Monitoring evidence may contain provider identifiers, capability labels, timestamps, commitments, and bounded failure classifications. It must not contain cloud credentials, bearer tokens, private keys, raw chat, reconstructed plaintext, or protected memory content.

## External execution

The comparison logic and tests are repository-owned. Scheduled live probe execution remains dependent on the protected production activation environment and configured provider identities.
