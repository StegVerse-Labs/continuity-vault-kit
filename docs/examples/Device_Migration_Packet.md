# Device Migration Packet Example

Use this packet when moving a private KnowledgeVault from one device or storage location to another. It is designed to preserve continuity without treating the destination copy as authoritative until verification is complete.

## Migration objective

Move the current vault from `Old Device / Current Vault` to `New Device / KnowledgeVault` without losing files, silently overwriting a newer copy, or exposing sensitive material through an unnecessary cloud or AI service.

## Source of truth before migration

- Source location: `Old Device / Current Vault`
- Source vault version: `0.1.1`
- Source manifest: `_Meta/vault.manifest.json`
- Last owner-reviewed index: `_Index/Master_Index.md`
- Migration initiated by: vault owner
- Migration date: `YYYY-MM-DD`

The source remains authoritative until the destination passes the checks below and the owner explicitly accepts the destination.

## Pre-migration checks

- [ ] Confirm the source vault opens normally.
- [ ] Record the source file count or produce a local inventory.
- [ ] Confirm the destination has enough free space.
- [ ] Review `DO_NOT_STORE_HERE.md` and remove material that should not be copied.
- [ ] Close applications that may still be writing to the source vault.
- [ ] Preserve a rollback copy when practical.

## Transfer method

- Method: direct cable, encrypted local transfer, removable storage, or another owner-approved method
- Encryption in transit: `yes / no / not applicable`
- Third-party service used: `none` or name the service
- Temporary copies created: list locations or state `none`

Do not place credentials, recovery codes, private keys, or unrelated sensitive exports into this packet.

## Destination verification

- [ ] Expected top-level folders are present.
- [ ] `_Meta/vault.manifest.json` is present and readable.
- [ ] `_Index/Master_Index.md` is present and readable.
- [ ] File count matches the source inventory, or every difference is explained.
- [ ] A sample of important files opens correctly.
- [ ] No unexpected duplicate vault root was created.
- [ ] No destination file silently replaced a newer owner-approved file.
- [ ] Device-specific paths or links have been reviewed.

## Differences found

| Difference | Source state | Destination state | Resolution |
|---|---|---|---|
| Example: attachment link | relative path works | path broken | update after owner review |

An unexplained difference blocks acceptance. A successful copy operation alone does not prove continuity.

## Owner acceptance

- Destination accepted as current vault: `yes / no`
- Acceptance date: `YYYY-MM-DD`
- Accepted by: vault owner
- Source disposition: retained temporarily, archived, or securely removed
- Rollback deadline, if any: `YYYY-MM-DD`

Until owner acceptance is recorded, automation and AI systems must not assume the destination is the current authoritative vault.

## Next permitted action

After acceptance, update device-specific references and record the migration in `_System/` or `_migration/`. If verification fails, stop, preserve both copies, and reconcile differences before retrying.

## Completion condition

Migration is complete only when the destination is verified, differences are resolved or explicitly accepted, the owner designates the destination as current, and rollback handling is recorded.
