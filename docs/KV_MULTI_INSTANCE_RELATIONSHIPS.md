# KnowledgeVault Multi-Instance Relationship Model

## Scope

This document defines multiple KnowledgeVault instances belonging to one owner continuity set. It does not create provider authority, credentials, provider sessions, synchronization authority, or Interlock/InTr activation.

## Instance identity

Each installed KnowledgeVault root has:

- a unique `instance_id`;
- a positive `instance_number` used for human-readable `KV #n` naming;
- a `kv_set_id` grouping related instances;
- a storage-medium description and optional non-secret locator;
- an installation receipt bound to the instance ID.

The canonical instance-local record is:

```text
_System/Instances/instance.json
```

## Relationship rules

### KV #1

`KV #1` is the first numbered member of a KV set. Its default folder is `KnowledgeVault/` for backward compatibility.

KV #1 is **not automatically authoritative**, canonical, primary, writable, or privileged merely because its ordinal is 1.

### KV #2

`KV #2` is a separately rooted peer instance. Its default folder is `KnowledgeVault-2/`.

KV #2 may reside on the same storage medium as KV #1 or on a different one. Creating KV #2 never overwrites KV #1 and does not inherit authority from KV #1.

### KV #n

For every positive integer `n`, `KV #n` is an independently identified member of the same continuity set when its `kv_set_id` matches the other members.

`n` is an instance ordinal only. It is not a priority, authority, freshness, trust, or replication rank.

```text
Owner continuity set S
  KV #1 -> medium A
  KV #2 -> medium A or B
  ...
  KV #n -> any owner-controlled storage medium admitted by the surrounding system
```

## Storage relationship

Storage is metadata about where an instance root is materialized. The instance model is provider-neutral.

Examples include:

- `icloud-drive`
- `google-drive`
- `onedrive`
- `dropbox`
- `local-disk`
- `removable-encrypted-volume`
- future storage mediums

The storage-medium field does not prove that a provider adapter, login session, credential, or governed transition exists.

## Peer relationship versus governed roles

All instances sharing a `kv_set_id` are `PEER` members by default.

Roles such as the following are deliberately separate from instance numbering:

- PRIMARY
- REPLICA
- MIRROR
- BACKUP
- ARCHIVE
- READ_ONLY
- RECOVERY_SOURCE

Those roles may later be admitted by Interlock/InTr policy and recorded through a separate governed relationship/receipt. The baseline initializer does not assign them.

## Same-provider multi-instance example

Two isolated iCloud-backed roots can be initialized without any new cloud adapter:

```bash
python3 tools/init_vault.py /iCloud/StegVerse --instance 1 --storage-medium icloud-drive
python3 tools/init_vault.py /iCloud/StegVerse --instance 2 --storage-medium icloud-drive
```

Result:

```text
/iCloud/StegVerse/KnowledgeVault/
/iCloud/StegVerse/KnowledgeVault-2/
```

Each root receives a different `instance_id` and its own installation receipt.

## Future MyKV mapping

MyKV can project the KV set as a list of connected instance roots/drives. Add/remove operations should operate on a specific `instance_id` and storage binding rather than assuming a single global `KnowledgeVault` root.

Provider connection/admission remains an Interlock/InTr adapter concern. Instance identity is intentionally usable before that runtime authority is available.
