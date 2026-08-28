# StegDB Overlay Hosted Writeback Retirement Mirror Handoff

Updated: 2026-08-27
Repository: `StegVerse-Labs/continuity-vault-kit`
Issue: #97
Branch: `fix/stegdb-overlay-hosted-writeback`
State: CLAIMED_FOR_IMPLEMENTATION

## Goal

Retire hosted canonical repository writeback from both StegDB overlay sync workflows while preserving exact machine-generated sync candidates.

## Affected workflows

- `.github/workflows/sync-knowledgevault-overlay-from-stegdb.yml`
- `.github/workflows/sync-overlay-from-stegdb.yml`

## Required state

```text
GitHub Actions role: VALIDATION_TRANSPORT_ONLY
contents: read
persist-credentials: false
repository mutation: false
git commit/push: false
StegDB mutation: false
candidate overlay generation: allowed
candidate hash inventory: allowed
candidate patch artifact: allowed
canonical_next_transition: NON_HOSTED_REPOSITORY_SYNC_REQUIRED
authority_effect: NONE
```

The hosted workflows may build deterministic candidate trees in temporary/report directories and compare them with current canonical targets. They must not make those candidate trees canonical.

## Non-claims

No canonical overlay sync, repository mutation, deployment, runtime activation, or credential authority is produced.

## Next executable boundary

Convert both workflows to read-only delta/patch generation, add regression enforcement, validate exact head, merge only on green evidence, then inspect KV format-branch mutation separately.
