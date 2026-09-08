# KV MyKV Instance Projection

This document defines the bounded status contract by which MyKV can display multiple KnowledgeVault instances without receiving private vault content or provider credentials.

## Source

`runtime/kv_my_kv_projection.py`

## Projection purpose

MyKV may display, per KV instance:

- instance identity and ordinal;
- KV set membership;
- storage medium and explicitly non-secret locator metadata;
- current relationship tier;
- relationship governance state;
- pending relationship request identifiers;
- whether governed connect, disconnect, and tier-change requests can be initiated.

The projection is status-only. It cannot authorize or execute provider mutation, relationship mutation, data movement, replication, AI corpus exposure, credential access, or runtime activation.

## Required safety posture

```text
private_content_included = false
credential_material_included = false
provider_mutation_authorized = false
relationship_mutation_authorized = false
authority_effect = NONE_STATUS_ONLY
activation_effect = false
```

A MyKV consumer must fail closed if those fixed values are not present.

## Relationship tiers

The projection carries one of:

- `NOT_CONNECTED`
- `CONNECTED`
- `SYNCED`
- `AI_INTERACTION`

The tier is read from durable relationship state when present. Pending requests are projected separately and do not alter the current tier.

## Multi-instance set projection

A set projection may aggregate multiple roots only when every projected instance carries the same `kv_set_id`. Mixed-set aggregation is rejected.

Instance entries are deterministically ordered by `instance_number`, then `instance_id`.

## Consumer boundary

Site/MyKV may render the projection and produce governed request intents. It must not infer that request support means provider or relationship execution authority. Actual mutation remains subject to Interlock/InTr and the corresponding provider/runtime path.
