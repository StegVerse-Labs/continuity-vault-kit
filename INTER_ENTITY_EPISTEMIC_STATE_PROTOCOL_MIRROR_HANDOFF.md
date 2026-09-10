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
receipt != interpretation
interpretation != applicability
applicability != evidence acceptance
evidence acceptance != agreement
agreement != incorporation
incorporation != truth
assertion != authority
successful subsystem != end-to-end readiness
unknown != false
unknown != ignorable
newly discovered condition != automatically applicable
sender scope hypothesis != receiver applicability decision
not-applicable requires explicit receiver disposition
stale epistemic evidence != current state
correction/supersession != historical rewrite
```

InTr remains the bidirectional transport/interlock relation. This protocol adds a mandatory epistemic-state binding to state-relevant communications while allowing lightweight informational carriage.

## Universal communication lifecycle

```text
Entity A forms message
-> states known/unknown/ambiguous/disputed items explicitly
-> assigns consequence class
-> sends InTr-bound epistemic envelope
-> Entity B receives envelope
-> B acknowledges receipt without implying understanding/agreement
-> B interprets and independently evaluates applicability
-> B incorporates, establishes NOT_APPLICABLE, disputes/rejects with evidence, or enters PROBE_REQUIRED
-> B emits durable acknowledgement at the achieved level
-> discovered unknowns are communicated as new DISCOVERY messages with scope hypotheses
-> affected Entities independently resolve applicability and acknowledge
-> dependent state/readiness is recomputed
-> corrections/supersessions preserve lineage rather than erase history
```

Receipt of a discovery does not prove the discovery true or applicable. It does prevent an affected receiver from silently acting as though the discovered condition does not exist.

## Epistemic and acknowledgement states

Epistemic item states:

```text
KNOWN
UNKNOWN
AMBIGUOUS
DISCOVERED_UNKNOWN
DISPUTED
```

Acknowledgement depth:

```text
RECEIVED
-> INTERPRETED
-> APPLICABILITY_RESOLVED
-> EVIDENCE_ACCEPTED
-> AGREED
-> INCORPORATED
```

These levels are not interchangeable. Receipt alone never implies agreement or incorporation.

Consequence classes scale required ceremony:

```text
INFORMATIONAL     -> RECEIVED
STATE_RELEVANT    -> INTERPRETED
STATE_CHANGING    -> APPLICABILITY_RESOLVED
HIGH_CONSEQUENCE  -> INCORPORATED
```

Unknown applicability, ambiguity, dispute, stale evidence, or missing required receiver acknowledgement prevents dependent state from being treated as resolved.

## Unknowns and unknown unknowns

An ordinary unknown is already represented and may be `UNKNOWN` or `AMBIGUOUS`.

An unknown unknown cannot be represented before discovery. Once any Entity obtains evidence sufficient to identify the previously unrepresented condition, it becomes `DISCOVERED_UNKNOWN`, receives a durable `discovery_id`, preserves provenance, and carries a `scope_hypothesis`. The scope hypothesis is not authority over other Entities; each receiver independently determines applicability.

The receiver must then choose one of:

```text
INCORPORATED
NOT_APPLICABLE
PROBE_REQUIRED
REJECTED_AS_INVALID
DISPUTED
```

Until all affected receiver dispositions relevant to a transition/readiness decision satisfy the consequence-required acknowledgement depth, that decision cannot be promoted to READY solely from narrower successful evidence.

## Freshness and lineage

Epistemic items may carry `valid_until`. Expired evidence cannot support a current dependent transition. Corrections and supersessions create new append-only items with `supersedes_item_id`; prior state remains reconstructable.

## InTr transport binding

`runtime/intr_epistemic_packet_binding.py` binds an epistemic envelope to transport through canonical SHA-256 plus message identity, consequence class, acknowledgement requirement, and required acknowledgement depth. The binding has `authority_effect=NONE`.

State-relevant, state-changing, and high-consequence InTr communication fails closed if the epistemic binding is absent or its consequence class conflicts with transport expectations. Informational traffic may remain lightweight.

## Source implementation

```text
schemas/intr-epistemic-state-envelope.schema.json
runtime/intr_epistemic_state.py
runtime/intr_epistemic_packet_binding.py
tests/test_intr_epistemic_state.py
tests/test_intr_epistemic_packet_binding.py
```

The implementation now provides universal vocabulary, receiver incorporation/probe classification, separated acknowledgement semantics, consequence-scaled acknowledgement requirements, discovered-unknown promotion, sender-only scope hypotheses, disputed-state handling, freshness checks, append-only correction/supersession lineage, multi-recipient acknowledgement aggregation, InTr hash/reference binding, and readiness guards.

## Required integrations

This protocol is intended to become a shared invariant across every inter-Entity edge, including but not limited to AI <-> AI, AI <-> human, agent <-> agent, service <-> service, KV <-> KV, KV <-> StegOS/device, StegOS/device <-> network/endpoint, SDK/external framework <-> StegVerse processor, governance/evaluator <-> execution entity, and future StegVerse Entity boundaries carried through Interlock/InTr.

`SDK-READINESS-PROBE-DISCIPLINE-004` is a downstream consumer: its local readiness set must incorporate communicated discoveries and unresolved acknowledgements rather than invent a parallel protocol.

## Remaining implementation

- validate exact branch head and repair any regressions;
- add one executable cross-Entity round-trip proof: discovery -> receiver incorporation/probe -> acknowledgement -> dependent-state recomputation;
- add SDK readiness adapter consuming this protocol;
- reconcile architecture artifact(s) where applicable;
- merge source only after validation evidence;
- reconcile/merge canonical Task Registry state after validation;
- create downstream propagation verification tasks after release-ready source merge.

## Completion boundary

Source/schema/tests are not runtime activation. COMPLETE requires validated source merge, canonical Task Registry state, integration with InTr transport semantics, at least one cross-Entity round-trip proof showing discovery -> receiver incorporation/probe -> acknowledgement -> dependent-state recomputation, and propagation tasks for applicable downstream repositories.
