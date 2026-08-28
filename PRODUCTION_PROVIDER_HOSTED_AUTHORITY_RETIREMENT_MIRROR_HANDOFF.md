# Production Provider Hosted Authority Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Canonical activation issue: #16
Branch: `fix/production-provider-hosted-authority-16`
State: CORRECTIVE_SUBLANE_CLAIMED

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

## Next executable boundary

Convert the hosted workflow to validation-only, add fail-closed regression coverage, validate exact head, merge, then update issue #16 and canonical handoff so the next operator/runtime step points to TVC-admitted resident execution instead of GitHub OIDC apply.
