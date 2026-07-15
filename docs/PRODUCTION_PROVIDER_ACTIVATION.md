# Production Provider Activation

## Selected staging profile

The first concrete activation profile uses:

- **StegID signature verification:** AWS KMS asymmetric `Verify` with a dedicated customer-managed signing key.
- **AI-entity attestation:** SPIFFE/SPIRE X.509-SVID workload identity for the designated StegVerse AI entity.
- **Key custody:** AWS KMS customer-managed keys, with separate key policy, wrapping context, rotation, disablement, and scheduled deletion procedures.
- **Replicated state:** Amazon DynamoDB conditional writes implementing exact prior-version comparison and one-version advancement.
- **Ecosystem Chat transport:** the StegVerse authenticated chat endpoint, identity still unconfigured.
- **Master-Records:** the StegVerse receipt-ingestion endpoint, identity still unconfigured.

Selection does not equal activation. `default_aws_profile()` intentionally uses `UNCONFIGURED` identity references and cannot return activation-ready status.

## Activation gates

Every provider must progress independently through:

1. `selected` — technology and service chosen;
2. `configured` — resource and endpoint identity recorded;
3. `verified` — conformance test and evidence commitment recorded;
4. `revoked` — provider identity is no longer admissible.

Production activation requires all six providers to be `verified`, a green repository validation commit, and a deployment receipt containing one evidence commitment per provider.

## Evidence boundaries

Deployment receipts retain provider identity references and evidence commitments. They must not include raw chat, queries, reconstructed plaintext, unwrapped data keys, signing private keys, bearer credentials, or attestation secrets.

## Rollback and revocation

A bounded rollback must:

1. fail closed for new reconstruction sessions;
2. revoke the affected provider identity or relationship epoch;
3. disable key release before changing transport or storage routing;
4. preserve pending Master-Records exports until acknowledged, superseded, or explicitly deprecated;
5. restore the last verified activation profile only through a new deployment receipt;
6. record the failed profile hash, reason, authority, and validation commit;
7. never reactivate tombstoned protected objects or exhausted capabilities.

Key destruction is a custody operation, not a state-label change. Scheduled deletion must be independently confirmed before an erasure receipt can claim loss of recoverability.

## Remaining external inputs

The following values cannot be produced safely inside the repository:

- actual AWS account, KMS key, and DynamoDB table identifiers;
- SPIFFE trust domain, SPIRE server identity, and workload selectors;
- Ecosystem Chat endpoint identity and transport verifier configuration;
- Master-Records endpoint identity and acknowledgement verifier configuration;
- secrets, credentials, hardware custody evidence, and production network access.

---

🔒 Layer: Framework | KV
