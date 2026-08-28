# KV Monitor Targets Canonical State Mirror Handoff

Status: SOURCE_IMPLEMENTED_ON_BRANCH / VALIDATION_PENDING
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #117
Branch: `feature/kv-monitor-targets-canonical`
Updated: 2026-08-28
Authority effect: NONE
Activation effect: false

## Purpose

Make provider/source monitoring targets canonical, non-secret Personal KV state so the resident provider-change observer can derive its work from the vault itself rather than from an ad hoc external runtime file.

## Canonical private KV path

```text
KnowledgeVault/
  _System/
    Connections/
      Monitor_Targets.json
```

## Contract

`Monitor_Targets.json` uses:

`stegverse.kv.provider-monitor-targets/v1`

Each target must bind:

- target ID;
- provider;
- explicit HTTPS source URL;
- exact allowed host;
- source type: provider documentation, changelog, or status;
- source-change class;
- severity;
- whether any content change is treated as breaking;
- affected connection assumptions;
- bounded summary text.

## Boundaries

1. Monitoring targets are public provider/source observation instructions only.
2. Embedded URL credentials are prohibited.
3. HTTP/non-TLS sources are prohibited.
4. Provider login, owner-account access, cookies, Authorization headers, API keys, tokens, passwords, and private keys are prohibited.
5. TV/TVC credential authority remains unchanged.
6. SKAP is not resolved by this monitoring contract.
7. Provider operation authority remains NONE.
8. GitHub Actions may validate source only; resident execution is owned by the WorkerCoordinator provider-change observer.
9. The target set may be generated from connection assembly monitoring configuration, but provider capability facts must not be duplicated.
10. User-specific target state belongs in the private KV; public source contains only an empty template and synthetic tests.

## Machine surfaces

- `KV_MONITOR_TARGETS_CANONICAL_STATE_MIRROR_HANDOFF.md`
- `schemas/kv-provider-monitor-targets.schema.json`
- `vault_template/KnowledgeVault/_System/Connections/Monitor_Targets.json`
- `runtime/connection_monitor_targets.py`
- `tests/test_connection_monitor_targets.py`
- `tools/check_kv_monitor_targets.py`
- read-only validation workflow

## Downstream consumer

`StegVerse-Labs/.github#362` resident provider-change observer.

## Current boundary

Machine-executable source, empty private-KV template, compiler, tests, and validation are implemented on this branch. No live provider source monitoring is performed by this branch.
