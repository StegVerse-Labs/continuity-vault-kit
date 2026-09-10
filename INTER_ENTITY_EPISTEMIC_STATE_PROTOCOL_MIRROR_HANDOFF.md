# Inter-Entity Epistemic State Protocol Mirror Handoff

Goal Task ID: `INTER-ENTITY-EPISTEMIC-STATE-PROTOCOL-001`
Repository: `StegVerse-Labs/continuity-vault-kit`
Status: `ACTIVE`
Protocol layer: `Interlock/InTr`
Authority effect: `NONE`

## Purpose

Define a universal protocol for epistemic state carried in **all inter-Entity communications**, not merely human-to-AI clarification or SDK readiness. Every sovereign Entity must be able to communicate what it knows, does not know, finds ambiguous, discovers after prior communication, disputes, probes, corrects, and supersedes without silently promoting uncertainty into fact or readiness.

## Architectural rule

```text
transport != understanding
receipt != incorporation
incorporation != truth
assertion != authority
successful subsystem != end-to-end readiness
unknown != false
unknown != ignorable
newly discovered condition != automatically applicable
not-applicable requires an explicit receiver disposition
```

InTr remains the bidirectional transport/interlock relation. This protocol adds a mandatory epistemic-state envelope to communications whose interpretation can affect a decision, transition, readiness claim, action, or downstream Entity state.

## Universal communication lifecycle

```text
Entity A forms message
-> states known/unknown/ambiguous/disputed items explicitly
-> sends InTr epistemic envelope
-> Entity B receives envelope
-> B evaluates applicability of each item to B's current state
-> B incorporates, establishes NOT_APPLICABLE, or enters PROBE_REQUIRED
-> B emits durable acknowledgement
-> discovered unknowns are communicated as new DISCOVERY messages
-> affected Entities incorporate/probe and recompute dependent state
-> corrections/supersessions preserve lineage rather than erase history
```

Receipt of a discovery does not prove the discovery true or applicable. It does prevent an affected receiver from silently acting as though the discovered condition does not exist.

## Unknowns and unknown unknowns

An ordinary unknown is already represented and may be `UNKNOWN` or `AMBIGUOUS`.

An unknown unknown cannot be represented before discovery. Once any Entity obtains evidence sufficient to identify the previously unrepresented condition, it becomes `DISCOVERED_UNKNOWN`, receives a durable `discovery_id`, preserves provenance, and is transmitted to affected Entities. The receiver must then choose one of:

```text
INCORPORATED
NOT_APPLICABLE
PROBE_REQUIRED
REJECTED_AS_INVALID
```

Until all affected receiver dispositions relevant to a transition/readiness decision are resolved, that decision cannot be promoted to READY solely from narrower successful evidence.

## Source implementation

```text
schemas/intr-epistemic-state-envelope.schema.json
runtime/intr_epistemic_state.py
tests/test_intr_epistemic_state.py
```

The initial source implementation provides the universal envelope vocabulary, receiver-side incorporation classification, discovered-unknown promotion, durable acknowledgement representation, and a readiness guard over unresolved acknowledgements.

## Required integrations

This protocol is intended to become a shared invariant across every inter-Entity edge, including but not limited to:

- AI <-> AI
- AI <-> human
- human <-> AI
- agent <-> agent
- service <-> service
- KV <-> KV
- KV <-> StegOS/device
- StegOS/device <-> network/endpoint
- SDK/external framework <-> StegVerse processor
- governance/evaluator <-> execution entity
- any future StegVerse Entity boundary carried through Interlock/InTr

`SDK-READINESS-PROBE-DISCIPLINE-004` becomes a downstream consumer: its local readiness set must incorporate communicated discoveries and unresolved acknowledgements rather than invent a parallel protocol.

## Remaining implementation

- bind the epistemic envelope into the existing generic InTr packet/boundary-transfer semantics without transferring authority;
- add message lineage validation for acknowledgement, correction, and supersession;
- require evidence provenance for DISCOVERY/PROBE_RESULT/CORRECTION classes;
- add multi-recipient acknowledgement aggregation and affected-entity completion rules;
- add adapter/helper for SDK readiness consumption;
- audit other inter-Entity communication producers and consumers for propagation targets;
- reconcile README and architecture documentation;
- obtain repository validation and canonical Task Registry registration;
- propagate only after source contract is validated and merged.

## Completion boundary

Source/schema/tests are not runtime activation. COMPLETE requires validated source merge, canonical Task Registry state, integration with existing InTr packet semantics, at least one cross-Entity round-trip proof showing discovery -> receiver incorporation/probe -> acknowledgement -> dependent-state recomputation, and propagation tasks for applicable downstream repositories.
