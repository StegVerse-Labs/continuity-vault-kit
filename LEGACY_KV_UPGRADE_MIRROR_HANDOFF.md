# Legacy KnowledgeVault Upgrade / Reinstall Test Mirror Handoff

Status: PLAN_ONLY_PREDECESSOR_MERGED / AUTOMATED_SUCCESSOR_ACTIVE / RUNTIME_NOT_EXECUTED  
Repository: StegVerse-Labs/continuity-vault-kit  
Issue: #174  
Implementation PR: #175 (merged)  
Updated: 2026-09-15  
Authority effect: NONE

## Purpose

Use the owner's older iCloud KnowledgeVault, installed around 2026-05-20, as a bounded test lane for upgrading or reinstalling an older KnowledgeVault against the current continuity-vault-kit.

The current Google Drive KnowledgeVault installed 2026-08-28 remains the current canonical production candidate. The iCloud vault is a test subject and is not automatically authoritative.

## Governing rule

A newer kit must never silently overwrite an existing vault. The canonical sequence remains:

1. inspect the legacy vault manifest, receipt, and format/version metadata;
2. compare the legacy vault against the current template;
3. classify source-template matches, required template updates, required additions, and legacy-only content that must be preserved;
4. emit a deterministic plan without mutation;
5. preserve a rollback copy before any admitted update/reinstall;
6. apply only an explicitly owner-authorized bounded migration/update operation to an isolated copy;
7. regenerate update evidence and verify post-update package parity/readback;
8. require owner acceptance before treating the upgraded test copy as current.

## Plan-only predecessor

`tools/plan_legacy_kv_upgrade.py` produces `stegverse.kv.legacy-upgrade-plan/v1`.

The planner is deliberately non-destructive:

- `mutation_performed=false`;
- `overwrite_existing_vault=false`;
- `owner_acceptance_required=true`;
- `rollback_copy_required=true`;
- `credential_material_required=false`;
- `authority_effect=NONE_PLAN_ONLY`.

It excludes the mutable template manifest from ordinary hash-equality decisions, treats the installation receipt as evidence rather than owner content, and preserves vault-only files as `legacy_only_preserve`.

PR #175 merged this plan-only source. That merge does not prove a physical iCloud upgrade.

## Automated successor

The admitted apply/rollback/verify work is now owned by:

```text
Goal Task ID: KV-ICLOUD-AUTOMATED-UPGRADE-001
COSV: 40000100100000
Issue: #215
Implementation PR: #216
Handoff: KV_ICLOUD_AUTOMATED_UPGRADE_MIRROR_HANDOFF.md
```

The successor reuses this planner and is intentionally separate from it. Its target owner experience is one owner-selected iCloud vault copy/archive; the executor then creates rollback evidence first, builds an isolated updated copy, preserves owner/private and protected runtime bytes, applies bounded framework changes, stages unsafe conflicts, emits receipts, packages the result, and independently verifies package/content hashes. No manual file-by-file comparison is required.

The automated successor must not mutate the selected live source in place and must not disturb the existing Google Drive KV #2 request lineage.

## Current physical test candidate

- provider/location: iCloud
- approximate installation date: 2026-05-20
- version: unknown until manifest/format inspection
- role: legacy upgrade/reinstall test subject
- canonical production candidate: Google Drive KnowledgeVault installed 2026-08-28

No mutation of either physical vault has been performed by repository source/CI work.

## Completion boundary

This predecessor's source/planner implementation is merged. The active source completion boundary moved to `KV-ICLOUD-AUTOMATED-UPGRADE-001`.

Runtime completion still requires authentic owner-selected bytes from the legacy iCloud vault, rollback artifact creation, executor completion, verified updated package/readback, durable receipt evidence, and owner acceptance. None of those runtime outcomes may be inferred from source, CI, or merge.
