# Automated iCloud KnowledgeVault Upgrade Mirror Handoff

Goal Task ID: `KV-ICLOUD-AUTOMATED-UPGRADE-001`  
COSV ID: `40000100100000`  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#215`  
Branch: `feature/kv-icloud-automated-upgrade-215`  
Status: `ACTIVE / IMPLEMENTATION_IN_PROGRESS / RUNTIME_NOT_EXECUTED`  
Updated: 2026-09-15  
Authority effect: `NONE_SOURCE_AND_COORDINATION_ONLY`

## Purpose

Reduce the owner's iPhone burden for upgrading the older iCloud KnowledgeVault from manual file-by-file comparison to one owner-selected source copy/archive followed by automated rollback preservation, deterministic planning, safe framework update, package verification, and durable receipts.

This is the admitted apply/rollback/verify successor to `CVK-LEGACY-KV-UPGRADE-174` and reuses `tools/plan_legacy_kv_upgrade.py`. It does not replace or rewrite the legacy planner.

## Owner UX target

```text
owner selects/attaches one iCloud KnowledgeVault copy/archive
-> automation preserves exact rollback input
-> inventories and hashes source
-> computes legacy-upgrade plan
-> builds an isolated updated copy
-> preserves owner-only/private files
-> applies only safe framework changes
-> stages unresolved template conflicts instead of deleting owner bytes
-> emits update receipt + verification report
-> packages verified updated vault
-> owner saves/replaces only after observing the verified result
```

No manual file-by-file comparison is part of the intended runtime path.

## Hard boundaries

- Never mutate or silently overwrite the live iCloud source vault in place.
- Never upload personal vault bytes to GitHub or repository artifacts.
- Never require provider credentials for file-only upgrade packaging.
- Never infer owner acceptance from source code, CI, merge, or package creation.
- Preserve legacy-only/private content.
- Preserve or stage conflicting owner-modified bytes before any framework replacement.
- Protect runtime identity, provider, receipt, continuity, and execution state from generic template overwrite.
- Do not re-emit, replace, rename, or otherwise disturb pending Google Drive KV #2 request `SITE-CLOUD-KV-4347408852127319cbda574f02e03edb`.

## Dependencies

- `LEGACY_KV_UPGRADE_MIRROR_HANDOFF.md`
- `tools/plan_legacy_kv_upgrade.py`
- `tests/test_legacy_kv_upgrade_plan.py`
- canonical task registry record `StegVerse-Labs/.github/data/canonical-task-records/KV-ICLOUD-AUTOMATED-UPGRADE-001.json`

## Required source evidence

1. Automated executor consumes directory or ZIP input and rejects unsafe archives.
2. Rollback package is created before constructing the updated output.
3. Original source inventory/hash is recorded.
4. Owner-only files survive exact-byte in the updated copy.
5. Protected runtime state is never generically overwritten by template bytes.
6. Safe framework additions/updates are deterministic and non-lossy.
7. Conflicts preserve original bytes and stage incoming framework bytes when automatic replacement is not admissible.
8. Update receipt binds plan, rollback, output, version, preserved/conflict paths, and verification outcome.
9. Output ZIP can be independently re-read and verified before delivery.
10. Tests cover success, collision refusal, idempotency/repeat behavior, private content preservation, rollback, archive traversal refusal, and tamper/hash detection.
11. README and iOS guidance describe the automated path without claiming live execution.

## Runtime completion boundary

Runtime completion requires authentic owner-selected iCloud KnowledgeVault bytes, execution of the merged executor against those bytes, retained rollback package, verified updated package, receipt/readback evidence, and owner acceptance. Source/CI/merge is insufficient.

## Manual work

None for source implementation. Private iCloud bytes cannot be selected by repository automation; after source completion, the minimum unavoidable owner action is one source selection/attachment from iCloud Drive.
