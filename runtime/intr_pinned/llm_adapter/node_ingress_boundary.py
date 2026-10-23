"""The LLM-adapter's ingress boundary: where a signal arrives and becomes a node.

Establishing a healthy node *is* ingress, so this is where the recording starts.
Nothing upstream of here emitted anything: a device registered, standing was
resolved, instructions were issued, and the ecosystem kept no record that any of
it happened.

This is a boundary, not a route handler, and the distinction decides the shape.
A receipt minted inside the registration handler would be a property of that
handler and therefore of HTTP. The ingress record is a property of the crossing:
`transport` names how the signal arrived, and the record is the same record
whichever transport carried it. HTTP is the transport today. The next stage puts
an external ingress point -- an ephemeral StegBrowser, a StegNode, or a device
that already understands the manifest protocol -- on the far side of
Interlock/InTr with its egress at this boundary. That swaps the transport and
leaves this boundary, and this record, unchanged.

Every arrival is recorded, admitted or refused. A state transition is the
disposition of an intended action, not only a successful one: a signal that
arrived and was refused is a transition whose disposition is DENY, and the
intended action -- establish a healthy node -- is the same intended action in
both cases. An earlier version of this boundary resolved standing first and
minted only on success, so a refused registration left no trace at all. That is
the defect this ecosystem exists to catch: the chain then showed only the
arrivals that happened to succeed, and a dropped or held signal was
indistinguishable from one that never arrived. The two dispositions carry
different transition classes, so no reader can mistake a refusal for an
admission.

What an admitted record carries is what makes this the record of ingress -- the
node's declared identity and class, the chain position the boundary issued it,
the health it was told about, and the continuation it was instructed to use. A
reader of the chain can see which node arrived, over what, and what it was told
to do next. A refused record carries what arrived by digest and the refusal
verbatim, and names no node endpoint, because the boundary issued none.

Non-authorizing. Admission here is structural, not authenticated: the caller
still supplies its own identity, `attestation_owner_state` stays `NOT_PROVEN`,
and the receipt records that rather than letting a chain entry read as proof of
who arrived.

Healthy means evaluated, not told (LC-KV-13, LC-KV-14; Lane B G-8 successor of
#358/#360). The boundary used to write `healthy_node_established: true` on every
admitted record, whatever health it was given: an UNHEALTHY report, no report,
or a transport that is NOT_YET_ENABLED. The record must not say that. Now
`healthy_node_established` is true only when
`healthy_node_evaluator.evaluate` returns ALLOW, and it returns ALLOW only for the
current NODE_HEALTH_REPORTED receipt of the node, read back on this repository's
chain with its body hash matching its address and status exactly HEALTHY, over
an INSTALLED transport. The `health` callable is still accepted. Its result is
recorded as an unreceipted observation and decides nothing.

`admit` no longer raises. Every non-ALLOW, whether a refused standing, an
unsupported transport or a node that is not currently healthy, is recorded
under NODE_INGRESS_REFUSED first, then returned as a six-field disposition
with failure_code NODE_NOT_CURRENTLY_ADMITTED_HEALTHY and failed_predicate
REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE. Lane D's layer 1 treats anything
but ALLOW as its own KV_ACCESS_LAYER1_REFUSED. The return interface is
documented on `admit`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from . import healthy_node_evaluator, node_health_report_producer, node_standing

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = "LLM_ADAPTER_INGRESS_BOUNDARY"

#: The intended action every arrival at this boundary carries, whatever its
#: disposition. The transition is the disposition of this action.
INTENDED_ACTION = "ESTABLISH_A_HEALTHY_NODE"

#: The two dispositions, and the transition class each one is recorded under.
ALLOW = node_standing.ALLOW
DENY = node_standing.DENY
ADMITTED_CLASS = "NODE_INGRESS_ADMITTED"
REFUSED_CLASS = "NODE_INGRESS_REFUSED"
#: The admitted class under its original name, so a reader of the chain and a
#: caller of this module name the same thing.
TRANSITION_CLASS = ADMITTED_CLASS
RECORD_SCHEMA = "stegverse.node-ingress-record/v1"
ADMISSION_SCHEMA = "stegverse.node-ingress-admission/v1"
FAILURE_CODE = healthy_node_evaluator.FAILURE_CODE
PREDICATE = healthy_node_evaluator.PREDICATE
#: Where a refusal is decided: the transport, the node's standing, or its health.
STAGE_TRANSPORT = "TRANSPORT"
STAGE_STANDING = "NODE_STANDING"
STAGE_HEALTH = healthy_node_evaluator.GATE

#: The transports this boundary can be reached over. HTTP is installed;
#: Interlock/InTr is the next stage and is named so a reader can see that the
#: boundary is the constant and the transport is not.
HTTP = "HTTP"
INTERLOCK_INTR = "INTERLOCK_INTR"
TRANSPORTS = {HTTP: "INSTALLED", INTERLOCK_INTR: "NOT_YET_ENABLED"}


def _ledger():
    """This repository's own transition ledger, loaded as the module it is."""
    spec = importlib.util.spec_from_file_location(
        "repo_transition_emit", ROOT / ".stegverse/transition-ledger/emit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def transport_state(transport: str) -> str:
    state = TRANSPORTS.get(transport)
    if state is None:
        raise node_standing.StandingRefused(
            node_standing.FAIL_CLOSED, "unsupported ingress transport: " + str(transport))
    return state


def _arrival(signal: Mapping[str, Any], transport: str) -> dict[str, Any]:
    """What both dispositions record about the arrival itself."""
    return {
        "schema": RECORD_SCHEMA,
        "boundary": BOUNDARY,
        "transport": transport,
        "transport_state": TRANSPORTS.get(transport),
        "intended_action": INTENDED_ACTION,
        "transition_is_the_disposition_of_the_intended_action": True,
        # What arrived, by digest, without copying a caller's payload into the chain.
        "signal_sha256": _sha(dict(signal) if isinstance(signal, Mapping) else signal),
        # Recorded as declared and selecting nothing.
        **node_standing.declared_ingress(signal),
    }


def ingress_record(signal: Mapping[str, Any], disposition: Mapping[str, Any],
                   profile: str, node_class: str, transport: str,
                   evaluation: Mapping[str, Any] | None,
                   observed_health: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """What an admitted crossing recorded about the node that arrived.

    Boundary-issued fields are kept apart from caller-declared ones, because a
    caller writing `recognized` about itself is the fabricated-identity bypass
    and a chain that mixed the two would make the distinction unreadable.

    `healthy_node_established` comes only from an ALLOW of the healthy-node
    evaluator. Any other mapping, including a bare health observation, yields
    false.
    """
    issued = disposition["manifest_fields"]
    evaluation = evaluation if isinstance(evaluation, Mapping) else {}
    healthy = (evaluation.get("disposition") == ALLOW
               and evaluation.get("healthy_node_established") is True
               and evaluation.get("predicate") == PREDICATE)
    return {
        **_arrival(signal, transport),
        "disposition": ALLOW,
        "transition_class": ADMITTED_CLASS,
        # Who arrived, as the boundary recognized them.
        "node_endpoint": issued["node_endpoint"],
        "node_class": node_class,
        "node_standing_mode": issued["node_standing_mode"],
        "generation": issued["generation"],
        "predecessor": issued["predecessor"],
        "manifest_fields_are_boundary_issued_not_caller_asserted": True,
        # What the node was told, so the record shows what it was instructed to do.
        "continuation_profile": profile,
        "healthy_node_established": healthy,
        "node_health_status": evaluation.get("health_status") if healthy else None,
        "health_report_receipt_sha256": evaluation.get("health_report_receipt_sha256") if healthy else None,
        "healthy_node_determined_by": "healthy_node_evaluator.evaluate (receipted reports only)",
        "observed_health_unreceipted_status": (
            observed_health.get("status") if isinstance(observed_health, Mapping) else None),
        "observed_health_decides_nothing": True,
        # An admitted crossing is not an authenticated one.
        "structural_standing_is_authenticated_standing": False,
        "attestation_owner_state": disposition["attestation_owner_state"],
        "caller_supplied_identity_is_not_authenticated": True,
        "authority_effect": "NONE_INGRESS_RECORD_ONLY",
    }


def refusal_record(signal: Mapping[str, Any], error: node_standing.StandingRefused,
                   transport: str, *, stage: str = STAGE_STANDING,
                   evaluation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """What a refused crossing recorded about the signal that arrived.

    No node endpoint, class or continuation appears: the boundary issued none,
    and a record naming them would read as a node that was admitted. The
    refusal is kept verbatim, because it is how the caller learns what to
    declare and paraphrasing it would put this boundary between the caller and
    the authority on that shape.
    """
    return {
        **_arrival(signal, transport),
        "disposition": DENY,
        "transition_class": REFUSED_CLASS,
        "standing_disposition": error.disposition,
        "refusal_reason": error.reason,
        "refusal_is_verbatim": True,
        "refusal_stage": stage,
        "failure_code": FAILURE_CODE,
        "health_evaluation_reason": (evaluation or {}).get("reason"),
        # The node the health gate evaluated, so this refused registration is a
        # receipted NODE_REGISTRATION trigger for the health-report producer.
        # It is not an issued endpoint.
        "evaluated_node_id": (evaluation or {}).get("node_id") if stage == STAGE_HEALTH else None,
        "healthy_node_established": False,
        "node_endpoint_issued": False,
        "instructions_released": False,
        "retry_is_a_transition_not_a_lost_signal": True,
        "authority_effect": "NONE_INGRESS_RECORD_ONLY",
    }


def _record(reference: str, transition_class: str, record: Mapping[str, Any],
            hb_epoch: int | None) -> dict[str, Any]:
    return _ledger().append(
        reference, transition_class,
        # Before: the signal as it arrived. After: what this boundary resolved it to.
        record["signal_sha256"], _sha(record), record, "NONE", hb_epoch=hb_epoch)


def _non_allow(signal: Mapping[str, Any], transport: str, stage: str, disposition: str,
               reason: str, repair: str, hb_epoch: int | None,
               evaluation: Mapping[str, Any] | None = None,
               standing_refusal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Record the refusal under NODE_INGRESS_REFUSED, then return it with the six fields."""
    error = node_standing.StandingRefused(disposition, reason)
    record = refusal_record(signal, error, transport, stage=stage, evaluation=evaluation)
    receipt = _record(REFUSED_CLASS + ":" + record["signal_sha256"], REFUSED_CLASS, record, hb_epoch)
    production = None
    if stage == STAGE_HEALTH:
        # Event-driven, not polled: the refused registration receipt just
        # appended is itself the NODE_REGISTRATION trigger. The producer emits a
        # report only from receipted evidence and otherwise returns FAIL_CLOSED.
        # This admission is not re-evaluated; the node registers again.
        production = node_health_report_producer.produce(receipt["receipt_sha256"], ledger_root=_ledger().lr())
    return {
        "schema": ADMISSION_SCHEMA,
        "disposition": disposition,
        "failure_code": FAILURE_CODE,
        "failed_predicate": PREDICATE,
        "required_evidence_or_repair": repair,
        "retry_entrypoint": healthy_node_evaluator.RETRY_ENTRYPOINT,
        "owning_existing_goal": healthy_node_evaluator.OWNING_GOAL,
        "next_attempt": healthy_node_evaluator.NEXT_ATTEMPT,
        "failed_stage": stage,
        "reason": reason,
        "health_evaluation": dict(evaluation) if evaluation is not None else None,
        "standing_refusal": dict(standing_refusal) if standing_refusal is not None else None,
        "health_report_production": production,
        "healthy_node_established": False,
        "instructions_released": False,
        "ingress_record": record,
        "ingress_recorded_at_boundary": BOUNDARY,
        "ingress_transition_class": REFUSED_CLASS,
        "ingress_receipt_sha256": receipt["receipt_sha256"],
        "ingress_transition_id": receipt["transition_id"],
        "authority_effect": "NONE_INGRESS_RECORD_ONLY",
    }


def admit(signal: Mapping[str, Any], *, transport: str = HTTP,
          health: Callable[[], Mapping[str, Any]] | None = None,
          health_report_receipt_sha256: str | None = None,
          hb_epoch: int | None = None) -> dict[str, Any]:
    """Admit a signal at this boundary, record the crossing, and return its disposition.

    Never raises for a refusal. The returned mapping always has
    `disposition` in {ALLOW, DENY, FAIL_CLOSED}, `healthy_node_established`
    (true only on ALLOW), `ingress_record`, `ingress_receipt_sha256` and
    `ingress_transition_id`.

    ALLOW, only when standing resolves and `healthy_node_evaluator.evaluate`
    returns ALLOW for the node's current receipted HEALTHY report over an
    INSTALLED transport, adds: `standing` (the node-standing disposition),
    `node_class`, `continuation_profile`, `health_evaluation`,
    `ingress_recorded_at_boundary` and `ingress_ordering`.

    A non-ALLOW is recorded under NODE_INGRESS_REFUSED first, then returned with
    the six fields: failure_code NODE_NOT_CURRENTLY_ADMITTED_HEALTHY,
    failed_predicate REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE,
    required_evidence_or_repair, retry_entrypoint, owning_existing_goal and
    next_attempt. It also carries `failed_stage` (TRANSPORT, NODE_STANDING or
    CURRENT_NODE_HEALTH), `reason`, `standing_refusal` (the verbatim
    node-standing refusal, for a standing failure) and `health_evaluation` (for
    a health failure).

    `health_report_receipt_sha256` is the report the requester cites. Without
    it, the node's current report on the chain is used. `health` is recorded as
    an unreceipted observation and decides nothing.
    """
    state = TRANSPORTS.get(transport)
    if state is None:
        return _non_allow(signal, transport, STAGE_TRANSPORT, node_standing.FAIL_CLOSED,
                          "unsupported ingress transport: " + str(transport),
                          "arrive over a transport this boundary names: " + ", ".join(sorted(TRANSPORTS)),
                          hb_epoch)
    try:
        disposition = node_standing.resolve(signal)
        node_class = node_standing.node_class(signal)
        profile = node_standing.continuation_profile(signal)
    except node_standing.StandingRefused as error:
        mode = signal.get("mode") if isinstance(signal, Mapping) else None
        standing = node_standing.refusal(error, mode=mode)
        return _non_allow(signal, transport, STAGE_STANDING, error.disposition, error.reason,
                          standing["required_evidence_or_repair"], hb_epoch, standing_refusal=standing)

    node_id = disposition["manifest_fields"]["node_endpoint"]["node_id"]
    evaluation = healthy_node_evaluator.evaluate(
        node_id, ledger_root=_ledger().lr(), transport_state=state,
        report_receipt_sha256=health_report_receipt_sha256)
    if evaluation["disposition"] != ALLOW:
        return _non_allow(signal, transport, STAGE_HEALTH, evaluation["disposition"],
                          evaluation["reason"] + ": " + evaluation["detail"],
                          evaluation["required_evidence_or_repair"], hb_epoch, evaluation=evaluation)

    observed = health() if health is not None else None
    record = ingress_record(signal, disposition, profile, node_class, transport, evaluation, observed)
    receipt = _record(
        # The node's own reference names the transition, so the chain is
        # searchable by the node that arrived.
        ADMITTED_CLASS + ":" + record["node_endpoint"]["node_id"],
        ADMITTED_CLASS, record, hb_epoch)
    return {
        "schema": ADMISSION_SCHEMA,
        "disposition": ALLOW,
        "standing": disposition,
        "node_class": node_class,
        "continuation_profile": profile,
        "healthy_node_established": record["healthy_node_established"],
        "health_evaluation": evaluation,
        "ingress_record": record,
        # Returned so the node can cite its own ingress rather than assert it.
        "ingress_receipt_sha256": receipt["receipt_sha256"],
        "ingress_transition_id": receipt["transition_id"],
        "ingress_recorded_at_boundary": BOUNDARY,
        "ingress_ordering": receipt["ordering"],
    }


__all__ = ["ADMISSION_SCHEMA", "ADMITTED_CLASS", "ALLOW", "BOUNDARY", "DENY", "FAILURE_CODE", "HTTP",
           "INTENDED_ACTION", "PREDICATE", "STAGE_HEALTH", "STAGE_STANDING", "STAGE_TRANSPORT",
           "INTERLOCK_INTR", "RECORD_SCHEMA", "REFUSED_CLASS", "TRANSITION_CLASS",
           "TRANSPORTS", "admit", "ingress_record", "refusal_record", "transport_state"]
