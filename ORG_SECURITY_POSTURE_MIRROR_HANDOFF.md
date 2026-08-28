# Organizational KV Security Posture Mirror Handoff

Updated: 2026-08-28
Repository: StegVerse-Labs/continuity-vault-kit
Issue: #121
Branch: feature/org-security-posture-v1
State: SOURCE_IMPLEMENTED_AWAITING_VALIDATION

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

## Preset families

EMPLOYEE_PRIVATE
BUSINESS_GOVERNED
ADMINISTRATIVE_SUPERVISION
GOVERNMENT_HIGH_CONTROL
COMPARTMENTED_REGULATED

## Completion

SOURCE_IMPLEMENTED -> SOURCE_VALIDATED -> MERGED

Runtime/org deployment activation, real employee-KV enrollment, org Replay execution and org Reconstruction execution remain separate evidence transitions.
