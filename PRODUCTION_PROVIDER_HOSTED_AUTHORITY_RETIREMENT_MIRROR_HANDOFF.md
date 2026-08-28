# Production Provider Hosted Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Canonical activation issue: #16
Branch: `main`
State: MERGED_VALIDATED_HOSTED_PRODUCTION_AUTHORITY_RETIRED

## Purpose

Correct the authority model of the existing Production Provider Activation lane without creating a duplicate activation owner.

Issue #16 remains the canonical activation lane. This handoff is the source-correction authority for the hosted workflow only.

## Live contradiction

Current `.github/workflows/production-provider-activation.yml` grants:

```text
id-token: write
GitHub OIDC -> AWS production role
Terraform plan against production providers
Terraform apply -auto-approve
provider identifier export after apply
GitHub-hosted activation evidence assembly
```

That conflicts with the current StegVerse execution contract:

```text
GitHub Actions production authority: NONE
GitHub Actions runtime authority: NONE
GitHub Actions control-plane authority: NONE
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
credential/secret/token authority: TV/TVC ONLY
production infrastructure mutation: sovereign resident / TVC-admitted execution only
```

A GitHub environment approval or typed `APPLY` token does not change the authority class of the hosted runner.

## Required corrected state

```text
workflow name: Production Provider Activation - Validation Only
permissions: contents: read
id-token: write: REMOVED
AWS role assumption: REMOVED
Terraform apply: REMOVED
production plan requiring cloud credentials: REMOVED
provider mutation: false
credential acquisition: false
GitHub-hosted activation: false
source/IaC validation: retained
non-secret activation-request artifact: retained
canonical_next_transition: TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION
authority_effect: NONE
```

The hosted workflow may validate Terraform formatting/configuration and emit a non-authorizing activation-request/readiness artifact. It may not acquire AWS credentials, mutate infrastructure, or claim provider deployment.

## Canonical runtime continuation

Issue #16 remains open until a non-hosted admitted runtime performs and proves:
1. TVC-authorized provider identity/capability admission.
2. Sovereign execution of provider provisioning/mutation.
3. Six live probes against actual configured services.
4. Master-Records acknowledgement.
5. rollback/revocation evidence.
6. signed deployment receipt.
7. repository readback of non-secret runtime evidence where admitted.

## Collision boundary

Do not create a second provider activation architecture, credential path, AWS broker, or provider authority. Existing Terraform source may remain as deployment intent/source, but hosted Actions may only validate it.

## Non-claims

This source repair does not deploy AWS resources, create an IAM role, establish OIDC trust, activate production providers, execute live probes, or satisfy issue #16.

## Implemented source state

```text
workflow: Production Provider Activation - Validation Only
permissions: contents: read
persist-credentials: false
GitHub OIDC: removed
AWS role assumption: removed
Terraform production plan: removed
Terraform apply: removed
cloud identity acquisition: false
provider mutation: false
Terraform fmt/init -backend=false/validate: retained
non-authorizing activation-request artifact: retained
canonical_next_transition: TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION
authority_effect: NONE
```

Regression:
- `tools/test_automation_contracts.py` rejects reintroduced OIDC/AWS/apply authority.
- `tests/test_production_provider_hosted_authority_retirement.py` enforces the hosted boundary.
- Release Integrity runs the dedicated regression.

## Next executable boundary

Validate exact head and merge only on green evidence. Then update issue #16 to remove GitHub OIDC/apply operator instructions and point the remaining live activation gates to TVC-admitted resident execution.


## Merge and validation evidence

```text
PR: #92
validated head: 55c0a18de596455f40f37d4cf368cf77a555fda3
merge: 1d487ed09007d42af602ce24d71e937541e279a3

Release Integrity: 33136076697 SUCCESS
Repository validation diagnostics: 33136076696 SUCCESS
Security Baseline: 33136076689 SUCCESS
KV Guardrails: 33136076726 SUCCESS
```

Issue #16 remains OPEN. Its canonical operator/runtime instructions now point to `TVC_ADMITTED_RESIDENT_PROVIDER_ACTIVATION`; GitHub OIDC/environment/APPLY instructions are retired.

## Current next boundary

The hosted-authority source correction is COMPLETE. Actual provider activation remains blocked on TVC-admitted resident execution plus six live probes, Master-Records acknowledgement, rollback/revocation evidence, and a signed deployment receipt.
