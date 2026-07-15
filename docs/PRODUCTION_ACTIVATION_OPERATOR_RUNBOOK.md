# Production Activation Operator Runbook

This runbook completes issue #16 only when real provider resources exist and the resulting evidence is retained. It does not authorize a production claim by itself.

## 1. Provision and record resources

Record the exact identifiers for:

- StegID AWS KMS asymmetric verification key ARN;
- reconstructive-memory AWS KMS custody key ARN;
- DynamoDB authoritative-state table ARN and region;
- SPIFFE trust domain, workload SPIFFE ID, and workload API socket;
- Ecosystem Chat absolute HTTPS endpoint;
- Master-Records absolute HTTPS endpoint.

Do not commit credentials, bearer tokens, private keys, plaintext chat, reconstructed context, or decrypted protected objects.

## 2. Create the configured profile

Copy `config/production-provider-profile.template.json` to a deployment-controlled profile path. Replace every `UNCONFIGURED` value, set all provider evidence commitments, and retain the rollback and revocation references.

Run:

```bash
python3 tools/check_provider_readiness.py path/to/configured-profile.json
```

Continue only when the command exits `0` and the reported profile commitment is retained.

## 3. Supply runtime authority outside the repository

Provide the operator environment with:

- AWS workload credentials authorized only for the required KMS and DynamoDB metadata operations;
- `SPIFFE_ENDPOINT_SOCKET` for the registered workload;
- `ECOSYSTEM_CHAT_PROBE_TOKEN` with probe-only endpoint authority;
- `MASTER_RECORDS_PROBE_TOKEN` with probe-only endpoint authority.

Use short-lived workload credentials where possible. Never copy secret values into issue comments, artifacts, receipts, or probe evidence.

## 4. Execute all six probes

Run the concrete probe set against the configured profile. Retain the conformance report containing exactly one successful result for each canonical role:

- `steg-id-signature`;
- `ai-entity-attestation`;
- `key-custody`;
- `replicated-state`;
- `ecosystem-chat`;
- `master-records`.

Any missing, duplicate, failed, stale, or tampered result keeps activation fail-closed.

## 5. Assemble and sign the deployment receipt

The deployment receipt must bind:

- configured profile hash;
- conformance report hash;
- validation commit;
- rollback reference;
- one evidence commitment for every provider role;
- `ALLOW` decision;
- trusted issuance time;
- authorized deployment signer.

A successful network request is not custody confirmation. Master-Records acceptance requires its verified destination acknowledgement.

## 6. Retain evidence

Retain the following in the governed deployment evidence location:

- configured profile without secrets;
- readiness report;
- six probe results;
- conformance report;
- signed deployment receipt;
- CI validation commit and results;
- rollback test result;
- revocation test result;
- endpoint identity and custody-boundary evidence.

## 7. Rollback and revocation

On provider drift, credential compromise, endpoint identity mismatch, failed acknowledgement verification, or state-store CAS violation:

1. revoke or disable affected provider authority;
2. mark the production profile or provider as revoked;
3. deny new reconstruction sessions;
4. preserve tombstones and exhausted capabilities;
5. retain unresolved Master-Records exports;
6. issue a revocation receipt;
7. rerun readiness and all six probes before restoration.

## Completion rule

Issue #16 may close only after the configured resources pass readiness and all six live probes, the signed deployment receipt is retained, rollback and revocation are demonstrated, and existing repository validation remains green.

---
🔒 Layer: Framework | KV
