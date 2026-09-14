# KV AI Persistence Layouts

Canonical goal: `SV-KV-AI-PERSISTENCE-001`

This document describes the concrete logical persistence layouts for the four canonical KV authority classes. These are provider-neutral state organizations, not storage-provider products and not execution authority.

## Class map

| KV class | Authority domain | AI role | Logical root |
| --- | --- | --- | --- |
| `PERSONAL_KV` | `PERSON` | `PERSONAL_ASSISTANT_AI` | existing KnowledgeVault root |
| `ORGANIZATIONAL_KV` | `ORGANIZATION` | `ORGANIZATIONAL_AI` | `_Organization/` |
| `STEGVERSE_KV` | `STEGVERSE_ECOSYSTEM` | `STEGVERSE_AI` | `_StegVerse/` |
| `MACHINE_KV` | `MACHINE_EXECUTION_ENTITY` | `EXECUTION_AGENT` | `_Machine/` |

Canonical machine-readable source is `specs/kv-ai-persistence-layouts.v1.json`.

## Organizational KV

The Organizational-KV layout separates policy, roles, delegations, shared resources, workflows, institutional memory, receipts, and capability references. Organizational AI may consume or propose state only within the authority granted by the organization and the applicable transition. An individual Personal-KV does not gain organizational mutation authority by sharing context, and an Organizational-KV does not inherit personal authority.

## StegVerse KV

The StegVerse-KV layout contains ecosystem state, service registry, governance-state references, worker-state projections, evidence, recovery, receipts, and capability references. `STEGVERSE_AI` may reason over admitted ecosystem state, but the AI is not the governance authority. Governance artifacts remain evidence/input to the applicable governance mechanism; their presence in StegVerse-KV does not allow AI to govern AI, humans, or other digital action systems.

## Machine KV

Machine-KV preserves node identity, workloads, assignments, execution state, liveness observations, checkpoints, reconstruction state, receipts, and capability references. Machine-KV is durable state for a machine execution entity; it is not a credential vault and does not turn a storage provider, HeartBeat, or execution agent into state authority.

`runtime/machine_kv_reconstruction.py` evaluates provider-neutral reconstruction evidence. A valid proof requires:

- distinct source and target providers;
- the same `machine_kv_id`;
- one exact canonical state-manifest hash observed at both providers;
- separately observed source and target InTr `ALLOW` receipts;
- no credential material in the evidence;
- provider authority fixed false;
- provider session identity transfer fixed false.

The verifier performs no provider I/O and grants no transition authority. Passing source tests proves the reconstruction decision contract only. Authentic cross-provider reconstruction remains a runtime evidence predicate until observations from two real provider executions exist.

## HeartBeat observation

`runtime/kv_heartbeat_receipt_observer.py` binds timing/freshness/correlation observations to an already-verified KV receipt hash. It can classify an observation as `FRESH`, `STALE`, or `UNKNOWN`, but it cannot:

- admit a transition;
- mutate KV state;
- mint a transition receipt;
- grant execution, transition, or state authority;
- turn liveness into completion evidence.

The verified KV transition exists first. HeartBeat observes that receipt second.

```text
verified KV receipt
-> receipt hash
-> HB observation of exact receipt hash
-> freshness/correlation projection
-> authority effect NONE_OBSERVATION_ONLY
```

## Cross-class movement

All 12 directed source→target class combinations are represented in `specs/kv-cross-class-intr-transition-fixtures.v1.json`. Every transfer requires Interlock/InTr, exact source-state and target-admission bindings, and a receipt. Direct state mutation, authority transfer, model/provider authority, and secret plaintext in receipts are forbidden.

```text
source KV class
-> source state hash
-> Interlock/InTr
-> target admission hash
-> target KV class independently admits
-> receipt
```

Context transfer is not authority transfer. Receipt observation is not authority transfer. Storage-provider location is not authority transfer.

## Shared invariant

For every class:

```text
provider != authority
model != authority
HeartBeat != state authority
context != authority
SKAP remains secret/capability custody
Interlock/InTr remains governed transition authority
cross-class mutation requires target admission
direct cross-class mutation is forbidden
ambiguous authority fails closed
```
