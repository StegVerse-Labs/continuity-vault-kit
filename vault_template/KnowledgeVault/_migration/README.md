# Vault Migration and Replacement

This directory records changes that affect how an existing KnowledgeVault is upgraded, replaced, or reorganized.

## Baseline rule

A new kit version must not silently overwrite a user's existing vault.

Use this sequence instead:

1. Read the existing vault's `_Meta/vault.manifest.json` and local policy files.
2. Compare the existing version with the incoming kit version.
3. Copy the existing vault before changing structure.
4. Apply only documented migration steps.
5. Record the result in this directory or in `_System/Migration_Log.md`.
6. Keep unresolved or conflicting material in `00_Inbox/` for human review.

## Migration file naming

Migration instructions should use this format:

```text
from_<old-version>_to_<new-version>.md
```

For example:

```text
from_0.1.1_to_0.2.0.md
```

Each migration file should state:

- source version;
- target version;
- folders or files added, moved, renamed, or deprecated;
- whether the change is required or optional;
- rollback or recovery instructions;
- checks that confirm completion;
- any user decision that cannot be automated safely.

## Replacement is not authority

A newer kit version is not automatically authoritative over an existing vault. The user retains control over whether to adopt, adapt, or reject a replacement structure.

Release checksums prove package integrity only. They do not prove that a migration is appropriate for a particular user's data.

## Current state

No structural migration is required between the currently documented `0.1.x` releases. When a future release changes the vault format, its migration file must be added here before that release is tagged.

---

🔒 Layer: Vault Template | KV
