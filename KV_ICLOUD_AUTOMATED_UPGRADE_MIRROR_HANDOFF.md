# Automated iCloud KnowledgeVault Upgrade Mirror Handoff

Goal Task ID: `KV-ICLOUD-AUTOMATED-UPGRADE-001`  
COSV ID: `40000100100000`  
Repository: `StegVerse-Labs/continuity-vault-kit`  
Issue: `#215`  
Pull request: `#216`  
Branch: `feature/kv-icloud-automated-upgrade-215`  
Status: `ACTIVE / SOURCE_IMPLEMENTED / HOSTED_VALIDATION_PASS / RUNTIME_NOT_EXECUTED`  
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
- `docs/IOS_VAULT_UPDATE_GUIDE.md` now makes this automated path the preferred iOS flow and retains the manual path only as a fallback.

## Validation evidence

At commit `5044e17d66571f81013882ec337a4e1be6999170`, the following hosted workflow groups completed successfully:

- Automated KV Upgrade Validation run `34974111606`: SUCCESS.
- Release integrity run `34974111617`: SUCCESS.
- Security Baseline run `34974111648`: SUCCESS.
- Repository validation diagnostics run `34974111591`: SUCCESS.
- KV Guardrails run `34974111596`: SUCCESS.
- KV Historical Corpus Import run `34974111578`: SUCCESS.
- KV Historical Provenance run `34974111647`: SUCCESS.

The immediately preceding release-integrity run failed only because repository-wide hosted-workflow authority validation still expected 53 workflow files after the new read-only validation workflow made the actual count 54. `tests/test_global_hosted_workflow_authority.py` was reconciled to the new exact count; the subsequent release-integrity run above passed. This was a repository inventory invariant, not an updater safety/runtime failure.

Any commits after `5044e17...` require a new exact-head validation observation before merge.

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
- coordination registration PR: `StegVerse-Labs/.github#1933`.

## Remaining source/integration work

- Maintain root `README.md` with the automated update surface and non-runtime boundary.
- Re-run exact-head validation after documentation/handoff reconciliation.
- Merge PR #216 only after preserved green exact-head validation.
- Merge `.github` PR #1933 after canonical registration reconciliation.
- Reconcile merged commit evidence into this handoff and canonical coordination handoff.

## Runtime completion boundary

Runtime completion requires authentic owner-selected iCloud KnowledgeVault bytes, execution of the merged executor against those bytes, retained rollback package, verified updated package, receipt/readback evidence, and owner acceptance. Source/CI/merge is insufficient.

## Manual work

None for source implementation. Private iCloud bytes cannot be selected by repository automation; after source completion, the minimum unavoidable owner action is one source selection/attachment from iCloud Drive.
