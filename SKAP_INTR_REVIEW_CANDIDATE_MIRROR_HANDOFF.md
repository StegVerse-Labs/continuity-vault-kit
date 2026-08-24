# SKAP / InTr Review Candidate Mirror Handoff

Status: IMPLEMENTED_PENDING_REVIEW_AND_RUNTIME_VALIDATION
Repository: StegVerse-Labs/continuity-vault-kit
Goal ID: SV-KV-SKAP-INTR-001
Created: 2026-08-24
Last updated: 2026-08-24

## Active goal

Define and validate a machine-readable review-candidate specification for the relationship among SKAP, KnowledgeVault, Device, External Network, and Endpoint, with `InTr` as the canonical interlock/transport relationship between each adjacent domain.

Canonical topology:

```text
SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint
```

## Implemented artifacts

- `specs/skap-intr-review-candidate.v1.json`
  - review-candidate contract
  - commit introducing candidate: `9ad3038fac16e34f2fc4615bc75e491b21ba311d`
- `schemas/skap-intr-review-candidate.schema.json`
  - JSON Schema Draft 2020-12 structural contract
  - commit: `380ba768196afb391299b2eb50b032cfa4491ad7`
- `scripts/validate_skap_intr_review_candidate.py`
  - dependency-free semantic validator and deterministic negative tests
  - commit: `6ecd9be372fe84ffdf402277901b0e2eb3bb356d`

## Authority boundary

- SKAP is secret/key/API/password custody and controlled-release state.
- KnowledgeVault is durable persistence/custody and continuity state; possession of KV does not grant SKAP decryption authority.
- Device is an execution/transport edge and does not become identity, continuity, secret-custody, governance, or execution authority merely by carrying a packet.
- External Network is transport environment only and must never receive plaintext protected material solely by transit.
- Endpoint is the externally addressed service/resource; intended endpoint/session identity must be verified before endpoint-bound secret material may be transiently resolved for native endpoint evaluation.
- `InTr` is the governed interlock/transport protocol relationship. It carries bounded state transitions and receipts; it does not confer authority from one node to another.
- Model output grants no execution authority.

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

## Validation evidence

An independent deterministic semantic check was run against the committed candidate content after commit. Baseline topology/invariants passed. Seven negative mutations were exercised and rejected by the same semantic rule set:

1. KV bypass / non-canonical direct adjacency.
2. `InTr` authority transfer enabled.
3. protected payload unsealed during Device-to-Network transit.
4. secret resolution permitted on arrival at an arbitrary endpoint rather than a verified intended endpoint/session.
5. return-path plaintext secret allowed.
6. Device escalated to secret-custody authority.
7. External Network permitted to hold plaintext secret material.

This is local semantic evidence, not hosted CI or physical/runtime proof.

## Review gates

- `RC-01-SCHEMA`: OPEN — committed schema exists; hosted schema-validation evidence not yet observed.
- `RC-02-NEGATIVE-TOPOLOGY`: IMPLEMENTED / LOCAL SEMANTIC PASS — hosted evidence remains open.
- `RC-03-AUTHORITY`: IMPLEMENTED / LOCAL SEMANTIC PASS — hosted evidence remains open.
- `RC-04-ENDPOINT-RESOLUTION`: IMPLEMENTED / LOCAL SEMANTIC PASS — hosted evidence remains open.
- `RC-05-RUNTIME`: OPEN — requires observed real `InTr` transitions across each adjacent boundary with replayable non-secret receipts.

## Completion boundary

This review-candidate goal is not complete merely because the JSON, schema, and validator exist. Completion requires observed schema/semantic validation, deterministic negative-test evidence from the committed validator, review acceptance, and runtime transition proof before any real SKAP secrets are stored under this contract.
