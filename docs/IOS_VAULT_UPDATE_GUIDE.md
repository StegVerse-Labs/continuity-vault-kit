# 📱 iOS Guide — Updating Your KnowledgeVault Safely

This guide describes the minimum-burden iPhone/iPad path for updating a private KnowledgeVault without manually comparing or copying framework files.

## Preferred path: automated, rollback-safe update

The current updater is `tools/apply_legacy_kv_upgrade.py`, with independent verification in `tools/verify_legacy_kv_upgrade_package.py`.

The owner-facing path is intentionally small:

1. In Files, select the existing iCloud KnowledgeVault copy or a ZIP of that vault.
2. Hand that owner-selected source to the trusted local/package execution surface.
3. The updater automatically creates rollback evidence **before** building an updated copy, computes the deterministic legacy-upgrade plan, preserves owner-only/private and protected runtime bytes, applies only bounded framework-managed changes, stages unsafe conflicts instead of deleting owner bytes, emits an upgrade receipt and verification report, packages the result, and re-reads the package to verify its hashes.
4. Replace or promote a live vault only after the verified result is observed and explicitly accepted by the owner.

No manual file-by-file comparison is required by this path.

## Important safety boundaries

- Never unzip a kit or update package directly over a live personal vault without the verified updater/acceptance path.
- The selected source is never mutated in place by the updater.
- A rollback archive is created before output mutation.
- Owner-only/private content is preserved exact-byte.
- Existing protected runtime state such as instance identity, execution/continuity state, provider state, receipts, recovery state, SKAP state, and the installation receipt is not generically overwritten by incoming template bytes.
- If an incoming framework file conflicts with personal/protected content, the incoming version is staged under `_System/Upgrade/Candidates/` instead of replacing the owner bytes.
- If a bounded framework-managed file is replaced, the pre-update bytes are first preserved under `_System/Upgrade/Preserved/`.
- Provider credentials are not required for this file-only update package flow.
- Personal vault bytes must not be uploaded to GitHub or repository artifacts.

## Outputs

A successful run produces:

- a rollback ZIP;
- an isolated updated vault directory;
- a verified updated vault ZIP;
- `_System/Upgrade/latest-upgrade.receipt.json` inside the updated copy;
- `_System/Upgrade/latest-upgrade.verification.json` inside the updated copy;
- an external verification sidecar binding the updated ZIP hash and exact content inventory hash.

The package can be independently checked with:

```bash
python3 tools/verify_legacy_kv_upgrade_package.py \
  KnowledgeVault-updated-<timestamp>.zip \
  KnowledgeVault-updated-<timestamp>.verification.json
```

## Command-line execution

For an owner-selected folder or ZIP:

```bash
python3 tools/apply_legacy_kv_upgrade.py \
  /path/to/owner-selected-KnowledgeVault-or.zip \
  /path/to/output \
  --owner-authorized
```

`--owner-authorized` is required so private-source access is never inferred merely because a path is technically reachable.

## Manual fallback

If the automated updater is unavailable, do not overwrite the private vault with a release ZIP. Preserve a full rollback copy first, use `tools/plan_legacy_kv_upgrade.py` to classify the delta, and apply only reviewed framework changes while preserving owner data. The automated path is preferred because it performs those checks and receipts consistently and eliminates manual file-by-file work.

## Why this matters

The KnowledgeVault is intended to remain continuous for years while the public framework evolves. The update process therefore treats the kit and the owner’s data as different authority/custody classes: framework evolution may propose changes, but it cannot silently replace private history or runtime identity.

See `KV_ICLOUD_AUTOMATED_UPGRADE_MIRROR_HANDOFF.md` and `LEGACY_KV_UPGRADE_MIRROR_HANDOFF.md` for the current source/runtime completion boundaries.
