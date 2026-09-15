# Automated iCloud KnowledgeVault Upgrade Mirror Handoff

Goal Task ID: `KV-ICLOUD-AUTOMATED-UPGRADE-001`  
COSV ID: `40000100100000`  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#215`  
Implementation PR: `#216`  
Implementation merge commit: `4c426925a354a5f2d71b8becd92896917247e74f`  
Status: `ACTIVE / SOURCE_MERGED_VALIDATED / RUNTIME_OWNER_SELECTION_PENDING`  
Updated: 2026-09-15  
Authority effect: `NONE_SOURCE_AND_COORDINATION_ONLY`

## Purpose

Reduce the owner's iPhone burden for upgrading the older iCloud KnowledgeVault from manual file-by-file comparison to one owner-selected source copy/archive followed by automated rollback preservation, deterministic planning, safe framework update, package verification, and durable receipts.

This is the admitted apply/rollback/verify successor to `CVK-LEGACY-KV-UPGRADE-174` and reuses `tools/plan_legacy_kv_upgrade.py`. It does not replace the legacy planner.

## Owner UX target

```text
owner selects/attaches one iCloud KnowledgeVault copy/archive
-> automation preserves rollback input before output mutation
-> inventories and hashes source
-> computes legacy-upgrade plan
-> builds an isolated updated copy
-> preserves owner-only/private and protected runtime bytes
-> applies bounded safe framework changes
-> stages unresolved conflicts instead of deleting owner bytes
-> emits update receipt + verification report
-> packages and independently re-reads the verified updated vault
-> owner promotes/replaces only after observing and accepting the verified result
```

No manual file-by-file comparison is part of the intended runtime path.

## Implemented source

- `tools/apply_legacy_kv_upgrade.py` accepts an owner-selected KnowledgeVault directory or ZIP and requires owner authorization at the CLI boundary.
- Safe ZIP extraction rejects absolute/traversal paths and symbolic links.
- Rollback evidence is created before constructing the updated output copy.
- ZIP inputs retain an exact input-archive rollback copy; directory inputs receive a deterministic file-byte rollback archive.
- The executor reuses `tools/plan_legacy_kv_upgrade.py` and never mutates the selected source in place.
- Owner-only/private paths and existing protected runtime state are exact-byte preserved.
- Incoming conflicts against personal/protected content are staged under `_System/Upgrade/Candidates/`.
- Bounded framework-managed replacements first preserve old bytes under `_System/Upgrade/Preserved/`.
- The updated copy emits `_System/Upgrade/latest-upgrade.receipt.json` and `_System/Upgrade/latest-upgrade.verification.json`.
- A deterministic updated ZIP and external verification sidecar are emitted.
- `tools/verify_legacy_kv_upgrade_package.py` independently checks updated ZIP SHA-256 and exact content-inventory SHA-256 after safe re-extraction.
- `tests/test_automated_legacy_kv_upgrade.py` covers non-destructive success, rollback presence, exact private/runtime preservation, conflict staging, pre-replacement preservation, repeat-output collision refusal, ZIP traversal refusal, independent verification, and tamper failure.
- `.github/workflows/automated-kv-upgrade-validation.yml` is read-only hosted validation; it grants no runtime or iCloud authority.
- `README.md` and `docs/IOS_VAULT_UPDATE_GUIDE.md` make this automated path the preferred update flow while preserving the runtime/non-authority boundary.

## Exact-head validation and merge evidence

The final implementation head was `89035d3f64d3864f7193d95434faab30285a05eb`. All observed pull-request workflow groups at that exact head completed successfully before merge:

- Automated KV Upgrade Validation run `34974590734`: SUCCESS.
- Release integrity run `34974590775`: SUCCESS.
- Security Baseline run `34974590761`: SUCCESS.
- Repository validation diagnostics run `34974590829`: SUCCESS.
- KV Guardrails run `34974590756`: SUCCESS.
- KV Historical Corpus Import run `34974590839`: SUCCESS.
- KV Historical Provenance run `34974590792`: SUCCESS.
- Validate KV AI Persistence Classes run `34974590785`: SUCCESS.
- KV Storage Endpoint v2 run `34974590735`: SUCCESS.

PR #216 was merged only after that exact-head green observation. Merge commit: `4c426925a354a5f2d71b8becd92896917247e74f`.

An earlier release-integrity run failed only because repository-wide hosted-workflow authority validation still expected 53 workflow files after the new read-only validation workflow made the actual count 54. `tests/test_global_hosted_workflow_authority.py` was reconciled to the new exact count; subsequent release-integrity validation passed. This was a repository inventory invariant, not an updater safety/runtime failure.

## Hard boundaries

- Never mutate or silently overwrite the live iCloud source vault in place.
- Never upload personal vault bytes to GitHub or repository artifacts.
- Never require provider credentials for file-only upgrade packaging.
- Never infer owner acceptance from source code, CI, merge, or package creation.
- Preserve legacy-only/private content.
- Preserve or stage conflicting owner-modified bytes before any framework replacement.
- Protect runtime identity, provider, receipt, continuity, execution, recovery, and SKAP state from generic template overwrite.
- Do not re-emit, replace, rename, or otherwise disturb pending Google Drive KV #2 request `SITE-CLOUD-KV-4347408852127319cbda574f02e03edb`.

## Canonical bindings

- predecessor handoff: `LEGACY_KV_UPGRADE_MIRROR_HANDOFF.md`;
- canonical coordination handoff: `StegVerse-Labs/.github/docs/KV_ICLOUD_AUTOMATED_UPGRADE_MIRROR_HANDOFF.md`;
- canonical Task Registry record: `StegVerse-Labs/.github/data/canonical-task-records/KV-ICLOUD-AUTOMATED-UPGRADE-001.json`;
- canonical COSV vector: `StegVerse-Labs/.github/control/task-vectors/KV-ICLOUD-AUTOMATED-UPGRADE-001.json`;
- coordination registration PR: `StegVerse-Labs/.github#1933`, merged as `4e71d5a193d545a2f51d6b91df286ff89968e2e1`.

## Remaining work

Repository implementation, documentation, validation, and merge are complete for the automated update source. The Goal remains ACTIVE because the private iCloud runtime predicate cannot be satisfied from repository evidence.

The next execution consumes one authentic owner-selected iCloud KnowledgeVault copy/archive. It must produce and retain the rollback archive, verified updated package, upgrade receipt, independent verification report, exact readback evidence, and owner acceptance. Only those runtime artifacts can support a claim that the iCloud KV was actually updated.

## Runtime completion boundary

Runtime completion requires authentic owner-selected iCloud KnowledgeVault bytes, execution of the merged executor against those bytes, retained rollback package, verified updated package, receipt/readback evidence, and owner acceptance. Source/CI/merge is insufficient.

## Manual work

Minimum unavoidable owner action: select or attach the private iCloud KnowledgeVault source copy/archive once. No manual file-by-file comparison, framework copying, rollback construction, or hash verification is required.
