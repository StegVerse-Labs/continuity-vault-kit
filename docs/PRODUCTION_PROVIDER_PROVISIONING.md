# Production Provider Provisioning

This document reduces issue #16's remaining infrastructure work to an apply-and-record sequence. It does not authorize production activation by itself.

## 1. Provision AWS resources

From `infra/production-providers`:

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
terraform output -json > provider-outputs.json
```

The module creates:

- an asymmetric AWS KMS key for StegID signing and verification;
- a rotating symmetric AWS KMS key for memory wrapping and custody;
- a deletion-protected, point-in-time-recoverable DynamoDB table encrypted with the custody key.

Do not commit Terraform state, credentials, plans, or provider tokens.

## 2. Populate the activation profile

Map Terraform outputs into the configured provider profile:

- `stegid_kms_key_arn` -> StegID verification resource identifier;
- `custody_kms_key_arn` -> key-custody resource identifier;
- `authoritative_state_table_arn` -> replicated-state resource identifier;
- `aws_region` -> the region for all three AWS providers.

Keep each provider status below `verified` until its executable probe succeeds.

## 3. Register the SPIFFE workload

Copy `spire-entry.template.json` outside the repository, replace all `UNCONFIGURED` values, and create the entry through the authorized SPIRE server.

The resulting workload identity must exactly match the AI-attestation resource identifier in the activation profile. The runtime must receive `SPIFFE_ENDPOINT_SOCKET` through its deployment environment.

## 4. Configure service endpoints

Supply absolute HTTPS endpoints and environment-only probe tokens for Ecosystem Chat and Master-Records. Tokens and endpoint credentials must not be written into repository files, workflow logs, conformance reports, or deployment receipts.

## 5. Execute readiness and conformance

Run the merged readiness validator, followed by the canonical six-provider probe set. Retain only committed metadata evidence and bounded failure codes.

Activation remains denied unless:

1. the configured profile passes readiness validation;
2. all six provider probes succeed;
3. the conformance report matches the exact profile commitment;
4. the signed deployment receipt is retained;
5. rollback and revocation evidence is present;
6. repository validation remains green.

## 6. Rollback

A failed activation attempt must not destroy evidence or silently weaken custody. Disable endpoint access, revoke workload identity, stop new writes, preserve unresolved Master-Records exports, and follow the governed KMS deletion window only after recovery and evidence-retention requirements are satisfied.

---

🔒 Layer: Framework | KV
