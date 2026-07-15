# Provider Containment Actions

Continuous conformance drift must produce enforceable containment, not only a diagnostic report.

## Canonical actions

- disable StegID signing KMS key;
- disable reconstructive-memory custody KMS key;
- freeze authoritative replicated-state writes;
- suspend the affected SPIFFE workload identity;
- quarantine Ecosystem Chat endpoint access;
- quarantine Master-Records endpoint access.

Each command binds the incident commitment, canonical provider role, resource identity, action, and reason commitment. Each receipt binds the command commitment, actor, evidence commitment, timestamp, and bounded status.

A containment plan reports `CONTAINED` only when exactly one successful receipt exists for every command and no unknown receipt is supplied. Missing, duplicated, failed, pending, rolled-back, or unknown receipts produce `FAIL_CLOSED`.

## Rollback boundary

Rollback is not readiness restoration. A rolled-back containment action remains fail-closed until the incident lifecycle reaches successful re-attestation and issues both a successor conformance baseline and successor deployment receipt.

## Secret exclusion

Commands and receipts must not contain private keys, bearer tokens, AWS credentials, raw chat, reconstructed plaintext, or protected memory content. Evidence is represented only by commitments and bounded provider metadata.
