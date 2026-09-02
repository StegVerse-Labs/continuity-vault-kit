# Legacy KnowledgeVault Upgrade / Reinstall Test Mirror Handoff

Status: ACTIVE_IMPLEMENTATION / NON_DESTRUCTIVE_PLAN_FIRST  
Repository: StegVerse-Labs/continuity-vault-kit  
Issue: #174  
Branch: feature/legacy-kv-upgrade-test-174  
Updated: 2026-09-02  
Authority effect: NONE

## Purpose

Use the owner's older iCloud KnowledgeVault, installed around 2026-05-20, as a bounded test lane for upgrading or reinstalling an older KnowledgeVault against the current continuity-vault-kit.

The current Google Drive KnowledgeVault installed 2026-08-28 remains the current canonical production candidate. The iCloud vault is a test subject and is not automatically authoritative.

## Governing rule

A newer kit must never silently overwrite an existing vault. The test sequence is:

1. inspect the legacy vault manifest, receipt, and format/version metadata;
2. compare the legacy vault against the current template;
3. classify source-template matches, required template updates, required additions, and legacy-only content that must be preserved;
4. emit a deterministic plan without mutation;
5. preserve a rollback copy before any admitted update/reinstall;
6. apply only an explicitly admitted migration/update operation;
7. regenerate installation evidence and verify post-update parity;
8. require owner acceptance before treating the upgraded test copy as current.

## Initial implementation

`tools/plan_legacy_kv_upgrade.py` produces `stegverse.kv.legacy-upgrade-plan/v1`.

The planner is deliberately non-destructive:

- `mutation_performed=false`;
- `overwrite_existing_vault=false`;
- `owner_acceptance_required=true`;
- `rollback_copy_required=true`;
- `credential_material_required=false`;
- `authority_effect=NONE_PLAN_ONLY`.

It excludes the mutable template manifest from ordinary hash-equality decisions, treats the installation receipt as evidence rather than owner content, and preserves vault-only files as `legacy_only_preserve`.

## Current physical test candidate

- provider/location: iCloud
- approximate installation date: 2026-05-20
- version: unknown until manifest/format inspection
- role: legacy upgrade/reinstall test subject
- canonical production candidate: Google Drive KnowledgeVault installed 2026-08-28

No mutation of either vault has been performed by this lane yet.

## Completion boundary

Source completion requires implementation, tests, exact-head validation, and merge.

Runtime test completion requires an owner-selected copy of the legacy iCloud vault to be inspected, a plan to be produced, a rollback-safe admitted update/reinstall to execute, post-update parity/receipt verification, and owner acceptance. None of those runtime outcomes may be inferred from source merge.
