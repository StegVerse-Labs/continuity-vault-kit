# Organizational KV Security Posture Mirror Handoff

Updated: 2026-08-28
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #121
Pull request: #122
Branch: main
State: MERGED_VALIDATED_SOURCE_COMPLETE_RUNTIME_NOT_ACTIVATED

## Goal

Make organization/KV privacy, administrative visibility, Replay, Reconstruction, retention and incident-response boundaries explicit before organizational products depend on implicit assumptions.

## Invariants

- Organization posture is a versioned governance contract, not a UI preference.
- Presets are baselines; scoped overrides may narrow or expand only within declared authority.
- Posture changes emit a deterministic receipt and do not silently reinterpret historical evidence.
- Government/high-control posture may default official-use employee KVs to organization-visible without employee consent, while role, purpose, clearance, compartment, privilege and applicable-policy constraints still govern access.
- "No privacy expectation" does not mean universal access by every organizational actor.
- P1 enables user-facing Replay; P2 enables user-facing Reconstruction.
- Evidence/receipt generation is not disabled for lower subscription tiers; tiers govern exposed capabilities.
- Organization account sizing is employee-KV-count plus org capability level.
- Replay answers ordered historical transitions; Reconstruction derives state from surviving admissible evidence.
- Configuration grants no credential, provider, runtime, publication or sovereign execution authority.

## Source surfaces

- schemas/kv-organization-security-posture.schema.json
- schemas/kv-organization-posture-change-receipt.schema.json
- policy/organization-security-postures.v1.json
- runtime/organization_security_posture.py
- tests/test_organization_security_posture.py
- tools/check_organization_security_posture.py
- .github/workflows/validate-organization-security-posture.yml

## Preset families

EMPLOYEE_PRIVATE
BUSINESS_GOVERNED
ADMINISTRATIVE_SUPERVISION
GOVERNMENT_HIGH_CONTROL
COMPARTMENTED_REGULATED

## Capability tiers

CORE -> no user-facing organization Replay/Reconstruction
P1_REPLAY -> Replay enabled where posture admits it
P2_RECONSTRUCTION -> Replay + Reconstruction enabled where posture admits them

Tier selection cannot expand the organization's governance posture. Posture and tier must both admit the operation.

## Validation / merge evidence

Validated exact PR head: d0e408bec8d85e6a700a187a299e362ec23f0b2e

- Validate organization KV security posture: run 33220101836 SUCCESS
- Security Baseline: run 33220101824 SUCCESS
- Repository validation diagnostics: run 33220101820 SUCCESS
- Release integrity: run 33220101825 SUCCESS
- KV Guardrails: run 33220101875 SUCCESS

PR #122 merged successfully.
Merge commit: e6a3cc08fc0eb44dc5694021254aa25dfbdcc143

Hosted validation is validation-only and grants no runtime/governance execution authority.

## Lifecycle

SOURCE_IMPLEMENTED -> SOURCE_VALIDATED -> MERGED

Current:
- source contract: COMPLETE
- runtime organization deployment: NOT ACTIVATED
- real employee-KV enrollment under posture: NOT OBSERVED
- organization Replay execution: NOT OBSERVED
- organization Reconstruction execution: NOT OBSERVED

Those remain separate evidence transitions and must not be inferred from source merge.
