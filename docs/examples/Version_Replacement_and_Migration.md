# Version Replacement and Migration Example

Use this packet when adopting a newer Continuity Vault Kit without allowing the new template to overwrite an existing vault silently.

## Versions

- **Current vault version:** `0.1.1`
- **Candidate kit version:** `0.1.2`
- **Current authority:** the existing owner-accepted vault

## Candidate changes

| Change | Required for existing vault? | Action |
|---|---|---|
| Expanded release manifest | No | Applies to packaged releases |
| Migration guidance file | No | Copy only if useful |
| New documentation examples | No | Optional reference material |

## Pre-adoption checks

- Back up the existing vault.
- Review `CHANGELOG.md` and `_migration/README.md`.
- Confirm whether any structural migration file applies.
- Compare files before replacing or merging them.

## Decision record

- **Decision:** adopt documentation additions only.
- **Rejected action:** replace the entire existing vault with the candidate template.
- **Reason:** no structural migration is required, and user-authored content remains authoritative.

## Verification

- Existing owner files remain present.
- New files are added without overwriting modified local files.
- Index links resolve after the merge.
- The prior backup remains available until owner acceptance.

## Next permitted action

Record owner acceptance, then retire the temporary candidate copy. If any difference remains unresolved, keep the prior vault authoritative and document the conflict.
