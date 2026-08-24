# SKAP / InTr Review Candidate Mirror Handoff

Status: ACTIVE
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24

## Active goal

Define a machine-readable review-candidate specification for the relationship among SKAP, KnowledgeVault, Device, External Network, and Endpoint, with `InTr` as the canonical interlock/transport relationship between each adjacent domain.

Canonical topology:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

## Authority boundary

- SKAP is secret/key/API/password custody and controlled-release state.
- KnowledgeVault is durable persistence/custody and continuity state; possession of KV does not grant SKAP decryption authority.
- Device is an execution/transport edge and does not become identity, continuity, secret-custody, or governance authority merely by carrying a packet.
- External Network is transport environment only and must never receive plaintext protected material solely by transit.
- Endpoint is the externally addressed service/resource; endpoint identity must be verified before endpoint-bound secret material may be transiently resolved for native endpoint evaluation.
- `InTr` is the governed interlock/transport protocol relationship. It carries bounded state transitions and receipts; it does not confer authority from one node to another.

## Planned machine-readable artifacts

- `specs/skap-intr-review-candidate.v1.json`
- `schemas/skap-intr-review-candidate.schema.json`
- `scripts/validate_skap_intr_review_candidate.py`

## Required invariants

1. Exactly five canonical node roles are represented: `SKAP`, `KV`, `DEVICE`, `EXTERNAL_NETWORK`, `ENDPOINT`.
2. Exactly four canonical bidirectional `InTr` relationships connect adjacent roles in this order.
3. No non-adjacent direct transport edge is canonical in the review candidate.
4. Every `InTr` relationship requires next-boundary verification before protected-state interpretation.
5. Protected secret material remains sealed across SKAP, KV, Device, and External Network transit.
6. Endpoint-bound secret resolution is permitted only after the intended endpoint/session is positively verified and the operation grant remains valid.
7. No node or transport hop inherits authority merely because it received or relayed a valid packet.
8. Return-path communication uses the same `InTr` relationship family and must not return secret plaintext.
9. Every governed transition emits non-secret continuity/replay evidence sufficient for later reconstruction.
10. Ambiguous or unverifiable transitions fail closed.

## Completion boundary

This review-candidate goal is not complete merely because the JSON exists. Completion requires schema validation, deterministic negative tests for topology and authority violations, handoff reconciliation, and review acceptance before any real SKAP secrets are stored under this contract.
