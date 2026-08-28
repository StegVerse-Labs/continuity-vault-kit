# KV Connection Registry Materialization Mirror Handoff

Status: SOURCE_IMPLEMENTED_ON_BRANCH / VALIDATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #115
Branch: `feature/kv-connection-registry-materialization`
Updated: 2026-08-28
Authority effect: NONE
Activation effect: false

## Purpose

Materialize the canonical non-secret connection assembly registry inside each Personal KnowledgeVault so the vault itself is the durable reconstruction source for its own ingress/egress Interlock/InTr paths.

## Canonical private KV paths

```text
KnowledgeVault/
  _System/
    Connections/
      Connection_Assemblies.json
      Source_Changes/
      Health/
```

## Boundary

- Public source carries only empty/synthetic initialization.
- User-specific assembly state persists only in the connected private KV.
- Reusable credentials, tokens, passwords, private keys, cookies, recovery material, and provider secrets are prohibited.
- TV/TVC remains credential authority.
- SKAP remains reusable credential/session custody.
- Provider operation authority remains NONE.
- Source-change observations and health receipts are non-secret evidence only.
- No connection is VERIFIED without connection proof and KV readback proof.

## Upstream contracts

- `KV_CONNECTION_ASSEMBLY_SOURCE_MIRROR_HANDOFF.md`
- `schemas/kv-connection-assembly-registry.schema.json`
- `schemas/kv-source-change-observation.schema.json`
- `schemas/kv-connection-health-receipt.schema.json`

## Planned source

- `KV_CONNECTION_REGISTRY_MATERIALIZATION_MIRROR_HANDOFF.md`
- `vault_template/KnowledgeVault/_System/Connections/Connection_Assemblies.json`
- `vault_template/KnowledgeVault/_System/Connections/Source_Changes/README.md`
- `vault_template/KnowledgeVault/_System/Connections/Health/README.md`
- `runtime/connection_registry_store.py`
- `tests/test_connection_registry_store.py`
- `tools/check_kv_connection_registry_materialization.py`
- read-only validation workflow

## Current boundary

Machine-executable template/store source is implemented on this branch. No live provider connection, credential resolution, provider monitoring, or private user assembly state is committed to the repository.
