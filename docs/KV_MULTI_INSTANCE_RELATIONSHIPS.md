# KnowledgeVault Multi-Instance Relationship Model

## Scope

This document defines multiple KnowledgeVault instances belonging to one owner continuity set and the explicit relationship tier between them. It does not itself create provider authority, credentials, provider sessions, synchronization authority, or Interlock/InTr activation.

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

## KV #1 / #2 / #n identity

`KV #1` is the first numbered member of a KV set and retains the default `KnowledgeVault/` folder for backward compatibility. `KV #2` defaults to `KnowledgeVault-2/`. Every positive integer `n` can identify `KV #n` as an independently rooted member of the same continuity set when `kv_set_id` matches.

The ordinal is identity only. It is not authority, priority, freshness, trust, or replication rank. KV #2 does not inherit authority from KV #1.

```text
Owner continuity set S
  KV #1 -> medium A
  KV #2 -> medium A or B
  ...
  KV #n -> any owner-controlled storage medium admitted by the surrounding system
```

## Four relationship tiers

Relationship state is explicit. Sharing a `kv_set_id` does not imply communication, synchronization, or AI corpus unification.

### Tier 0 — NOT_CONNECTED

The instances are known to belong to the same continuity set but have no inter-instance communications.

```text
inter_comms: false
data_movement: false
replication: false
unified_ai_corpus: false
```

This is the default for a newly initialized KV instance.

### Tier 1 — CONNECTED

The instances are mutually relationship-aware and may exchange or move admitted data between their separately rooted stores.

```text
inter_comms: true
data_movement: true
replication: false
unified_ai_corpus: false
```

Connected does not mean synchronized. A record can exist in only one KV and can be deliberately moved or copied through an admitted operation.

### Tier 2 — SYNCED

The connected instances additionally participate in a replication relationship.

```text
inter_comms: true
data_movement: true
replication: true
unified_ai_corpus: false
```

Synced means designated replicated state is maintained across the participating KV instances. It does not require every physical byte or provider-specific artifact to be identical unless the admitted sync policy says so.

### Tier 3 — AI_INTERACTION

The participating KV instances are exposed to an admitted AI interaction as one logical information corpus.

```text
inter_comms: true
data_movement: true
replication: true
unified_ai_corpus: true
```

For AI reasoning and retrieval, data across the participating instances is considered one source boundary for the authorized interaction. Physical roots remain distinct, provenance remains instance-specific, and contradictory records must not be silently collapsed. AI Interaction does not turn an AI system into canonical authority over the data.

## Capability ordering

The tiers are cumulative in capability:

```text
NOT_CONNECTED
    < CONNECTED
    < SYNCED
    < AI_INTERACTION
```

A higher tier includes the lower-tier capabilities, but changing tiers is a governed transition once Interlock/InTr is active. The source model can represent desired/current tier state now without claiming the runtime transition occurred.

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

## Relationship versus role

Relationship tier and operational role are separate dimensions.

Possible future roles include:

- PRIMARY
- REPLICA
- MIRROR
- BACKUP
- ARCHIVE
- READ_ONLY
- RECOVERY_SOURCE

For example, two KVs may be `SYNCED` while one is designated `PRIMARY` and another `BACKUP`, or both may remain equal peers. Ordinal numbering never assigns these roles.

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

Each root receives a different `instance_id`, its own installation receipt, and begins at `NOT_CONNECTED` even though both may share the same storage provider and `kv_set_id`.

## Future MyKV mapping

MyKV should project each KV instance and its relationship tier separately. At minimum it should allow the owner to see:

- storage binding and health;
- `NOT_CONNECTED`, `CONNECTED`, `SYNCED`, or `AI_INTERACTION` state;
- the instances participating in each relationship;
- add/remove drive or instance operations;
- requested tier changes and their governed status.

Provider connection/admission remains an Interlock/InTr adapter concern. Instance identity and the four-tier relationship model are intentionally representable before runtime authority is available.
