"""LC-KV-13 producer: emit stegverse.node-health-report/v1 receipts from receipted evidence only.

This is the producer that `llm_adapter.healthy_node_evaluator` reads. Each report
is a manifest state transition of class NODE_HEALTH_REPORTED, appended through
this repository's own transition-ledger emitter, so it lands on the chain from
HEAD.json with a body hash equal to its address. That is exactly the shape the
evaluator accepts.

Trigger events
--------------
The producer fires on an event, never on a timer, cron or poll. The event is
always an existing receipt on the chain, cited by its address:

* NODE_REGISTRATION: a NODE_INGRESS_REFUSED receipt refused at
  CURRENT_NODE_HEALTH (carrying `evaluated_node_id`), or a NODE_INGRESS_ADMITTED
  receipt (carrying `node_endpoint.node_id`). `node_ingress_boundary.admit` fires
  this itself after recording a health-stage refusal.
* NODE_IDENTITY_BOUND: a NODE_IDENTITY_BINDING receipt.
* HEALTH_CHECK_RECEIPTED: a NODE_HEALTH_CHECK_OBSERVED receipt.

Evidence required on the same chain (all read back and hash-verified)
---------------------------------------------------------------------
1. AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE for the node, with evidence
   `disposition` ALLOW.
2. NODE_IDENTITY_BINDING for the node, with evidence `disposition` ALLOW,
   newer than and citing that existence receipt through
   `existence_receipt_sha256`.
3. The node's newest NODE_HEALTH_CHECK_OBSERVED receipt, with evidence schema
   `stegverse.node-health-check/v1`. Its `status` decides the report: exactly
   HEALTHY yields HEALTHY, and anything else yields UNHEALTHY with the observed
   value kept verbatim.

Anything that isn't receipted is a six-field FAIL_CLOSED, and nothing is
emitted. That covers a trigger off the chain, a forged or broken chain, a
missing prerequisite or a missing health check. HEALTHY is never derived from a
live callback, a caller's claim or a default.

Determinism
-----------
`plan()` is the deterministic core. It reads only the ledger directory, with no
clock, network, randomness or LLM, and it never writes. The same chain and
trigger always produce the same planned report. `produce()` appends the plan
through `.stegverse/transition-ledger/emit.py`, the repository's existing
emitter. The heartbeat epoch is taken from the trigger receipt, so no clock is
sampled for ordering. The emitter's descriptive `observed_at` field is its own
and is explicitly non-ordering.

Idempotence: if the node's newest report already rests on the same health-check
receipt, `produce()` returns it as `NOOP_ALREADY_CURRENT` and appends nothing.

A receipt is not an authentication. This module checks that the prerequisites
are receipted on this repository's chain. It does not verify them
cryptographically, so the report carries `health_report_authenticated`
`NOT_PROVEN_BEYOND_RECEIPTED_PREREQUISITES`.

Interface:

    plan(trigger_receipt_sha256, *, ledger_root, repository=REPOSITORY) -> dict
    produce(trigger_receipt_sha256, *, ledger_root, repository=REPOSITORY) -> dict

The result has `disposition` set to ALLOW (a report was planned or emitted, or
the current one already rests on this evidence) or FAIL_CLOSED with the six
fields and a `reason` from REASONS. On ALLOW, `report_status` says whether the
report is HEALTHY or UNHEALTHY. An UNHEALTHY report is still a successful
production, and the evaluator will DENY it.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Mapping

from llm_adapter import healthy_node_evaluator as hne

ALLOW = hne.ALLOW
FAIL_CLOSED = hne.FAIL_CLOSED
REPOSITORY = hne.REPOSITORY
HEALTHY = hne.HEALTHY
UNHEALTHY = "UNHEALTHY"
REPORT_CLASS = hne.HEALTH_REPORT_CLASS
REPORT_SCHEMA = hne.HEALTH_REPORT_SCHEMA
RESULT_SCHEMA = "stegverse.node-health-report-production/v1"
TRANSITION_MANIFEST_SCHEMA = "stegverse.node-health-report-transition/v1"
PRODUCER = "llm_adapter.node_health_report_producer"
PRODUCER_VERSION = "1"
INTENDED_ACTION = "REPORT_NODE_HEALTH_FROM_RECEIPTED_EVIDENCE"

EXISTENCE_CLASS = "AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE"
BINDING_CLASS = "NODE_IDENTITY_BINDING"
HEALTH_CHECK_CLASS = "NODE_HEALTH_CHECK_OBSERVED"
HEALTH_CHECK_SCHEMA = "stegverse.node-health-check/v1"

NODE_REGISTRATION = "NODE_REGISTRATION"
NODE_IDENTITY_BOUND = "NODE_IDENTITY_BOUND"
HEALTH_CHECK_RECEIPTED = "HEALTH_CHECK_RECEIPTED"
TRIGGER_EVENTS = (NODE_REGISTRATION, NODE_IDENTITY_BOUND, HEALTH_CHECK_RECEIPTED)

FAILURE_CODE = "NODE_HEALTH_REPORT_NOT_PRODUCED"
RETRY_ENTRYPOINT = ("llm_adapter.node_health_report_producer.produce(trigger_receipt_sha256, ledger_root=...) "
                    "on the next receipted trigger event (registration, identity binding or health check)")
OWNING_GOAL = hne.OWNING_GOAL
NEXT_ATTEMPT = ("fires again on the next receipted trigger event for this node: a registration, an identity "
                "binding or a NODE_HEALTH_CHECK_OBSERVED receipt. Never on a timer.")

#: reason -> (failed_predicate, required evidence or repair)
REASONS: dict[str, tuple[str, str]] = {
    "LEDGER_HEAD_UNREADABLE": ("TRIGGER_EVENT_RECEIPTED", "a readable HEAD.json on this repository's ledger"),
    "RECEIPT_MISSING_ON_CHAIN": ("TRIGGER_EVENT_RECEIPTED", "every receipt named by the chain must be present"),
    "RECEIPT_HASH_MISMATCH": ("TRIGGER_EVENT_RECEIPTED", "every receipt on the chain must hash to its address"),
    "RECEIPT_REPOSITORY_MISMATCH": ("TRIGGER_EVENT_RECEIPTED", "every receipt must belong to this repository"),
    "CHAIN_CYCLE": ("TRIGGER_EVENT_RECEIPTED", "a chain from HEAD.json to genesis without cycles"),
    "LEDGER_ROOT_MISMATCH": ("TRIGGER_EVENT_RECEIPTED", "produce() must append to the same ledger root it read"),
    "TRIGGER_NOT_RECEIPTED": ("TRIGGER_EVENT_RECEIPTED", "cite a trigger receipt that is read back on the chain "
                              "from HEAD.json"),
    "TRIGGER_NOT_RECOGNISED": ("TRIGGER_EVENT_RECEIPTED", "a NODE_INGRESS_REFUSED (at CURRENT_NODE_HEALTH), "
                               "NODE_INGRESS_ADMITTED, NODE_IDENTITY_BINDING or NODE_HEALTH_CHECK_OBSERVED receipt "
                               "naming a node"),
    "TRIGGER_EPOCH_UNREADABLE": ("TRIGGER_EVENT_RECEIPTED", "a trigger receipt whose hb_reference.epoch is an integer"),
    "EXISTENCE_NOT_RECEIPTED": (EXISTENCE_CLASS, "an AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE receipt for the node "
                                "with disposition ALLOW on the chain"),
    "IDENTITY_BINDING_NOT_RECEIPTED": (BINDING_CLASS, "a NODE_IDENTITY_BINDING receipt for the node with "
                                       "disposition ALLOW on the chain, newer than and citing its existence receipt "
                                       "(existence_receipt_sha256)"),
    "HEALTH_CHECK_NOT_RECEIPTED": ("HEALTH_CHECK_RECEIPTED", "a NODE_HEALTH_CHECK_OBSERVED receipt "
                                   "(stegverse.node-health-check/v1) for the node on the chain"),
}


def _non_allow(node_id: Any, reason: str, detail: str, **extra: Any) -> dict[str, Any]:
    predicate, repair = REASONS[reason]
    return {
        "schema": RESULT_SCHEMA,
        "disposition": FAIL_CLOSED,
        "node_id": node_id if isinstance(node_id, str) else None,
        "reason": reason,
        "detail": detail,
        "report_emitted": False,
        "failure_code": FAILURE_CODE,
        "failed_predicate": predicate,
        "required_evidence_or_repair": repair,
        "retry_entrypoint": RETRY_ENTRYPOINT,
        "owning_existing_goal": OWNING_GOAL,
        "next_attempt": NEXT_ATTEMPT,
        "authority_effect": "NONE",
        **extra,
    }


def _evidence(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    evidence = receipt.get("evidence")
    return evidence if isinstance(evidence, Mapping) else {}


def _trigger(receipt: Mapping[str, Any]) -> tuple[str | None, Any]:
    """(trigger event, node_id) for a receipt, or (None, None)."""
    cls, evidence = receipt.get("transition_class"), _evidence(receipt)
    if cls == hne.INGRESS_REFUSED_CLASS and evidence.get("refusal_stage") == hne.GATE:
        return NODE_REGISTRATION, evidence.get("evaluated_node_id")
    if cls == hne.INGRESS_ADMITTED_CLASS:
        endpoint = evidence.get("node_endpoint")
        return NODE_REGISTRATION, endpoint.get("node_id") if isinstance(endpoint, Mapping) else None
    if cls == BINDING_CLASS:
        return NODE_IDENTITY_BOUND, evidence.get("node_id")
    if cls == HEALTH_CHECK_CLASS and evidence.get("schema") == HEALTH_CHECK_SCHEMA:
        return HEALTH_CHECK_RECEIPTED, evidence.get("node_id")
    return None, None


def _for_node(receipt: Mapping[str, Any], cls: str, node_id: str) -> bool:
    evidence = _evidence(receipt)
    return receipt.get("transition_class") == cls and evidence.get("node_id") == node_id


def plan(trigger_receipt_sha256: Any, *, ledger_root: Any, repository: str = REPOSITORY) -> dict[str, Any]:
    """Deterministic core: decide, from the chain alone, the report a trigger produces."""
    chain, failure, detail = hne.read_chain(ledger_root, repository)
    if failure:
        return _non_allow(None, failure, detail)
    index = {r["receipt_sha256"]: position for position, r in enumerate(chain)}  # 0 is newest
    if not isinstance(trigger_receipt_sha256, str) or trigger_receipt_sha256 not in index:
        return _non_allow(None, "TRIGGER_NOT_RECEIPTED", f"{trigger_receipt_sha256!r} is not on the chain from HEAD.json")
    trigger = chain[index[trigger_receipt_sha256]]
    event, node_id = _trigger(trigger)
    if event is None or not isinstance(node_id, str) or not node_id:
        return _non_allow(None, "TRIGGER_NOT_RECOGNISED",
                          f"{trigger_receipt_sha256} ({trigger.get('transition_class')}) names no trigger event and node")
    epoch = (trigger.get("hb_reference") or {}).get("epoch") if isinstance(trigger.get("hb_reference"), Mapping) else None
    if not isinstance(epoch, int) or isinstance(epoch, bool):
        return _non_allow(node_id, "TRIGGER_EPOCH_UNREADABLE", f"{trigger_receipt_sha256} has no integer epoch")

    existence = next((r for r in chain if _for_node(r, EXISTENCE_CLASS, node_id)
                      and _evidence(r).get("disposition") == ALLOW), None)
    if existence is None:
        return _non_allow(node_id, "EXISTENCE_NOT_RECEIPTED", f"no receipted {EXISTENCE_CLASS} ALLOW for {node_id}")
    binding = next((r for r in chain if _for_node(r, BINDING_CLASS, node_id)), None)
    if (binding is None or _evidence(binding).get("disposition") != ALLOW
            or _evidence(binding).get("existence_receipt_sha256") != existence["receipt_sha256"]
            or index[binding["receipt_sha256"]] >= index[existence["receipt_sha256"]]):
        return _non_allow(node_id, "IDENTITY_BINDING_NOT_RECEIPTED",
                          f"no current receipted {BINDING_CLASS} ALLOW for {node_id} citing "
                          f"{existence['receipt_sha256']} after it")
    check = next((r for r in chain if _for_node(r, HEALTH_CHECK_CLASS, node_id)
                  and _evidence(r).get("schema") == HEALTH_CHECK_SCHEMA), None)
    if check is None:
        return _non_allow(node_id, "HEALTH_CHECK_NOT_RECEIPTED", f"no receipted {HEALTH_CHECK_CLASS} for {node_id}")

    observed = _evidence(check).get("status")
    status = HEALTHY if observed == HEALTHY else UNHEALTHY
    previous = next((r for r in chain if hne._is_report_for(r, node_id)), None)
    evidence = {
        "schema": REPORT_SCHEMA,
        "node_id": node_id,
        "status": status,
        "observed_health_check_status": observed,
        "trigger": {"event": event, "receipt_sha256": trigger_receipt_sha256,
                    "transition_class": trigger.get("transition_class")},
        "evidence_receipts": {
            "authenticated_reciprocal_node_existence": existence["receipt_sha256"],
            "node_identity_binding": binding["receipt_sha256"],
            "health_check": check["receipt_sha256"],
        },
        "previous_health_report_receipt_sha256": previous["receipt_sha256"] if previous else None,
        "transition_manifest": {
            "schema": TRANSITION_MANIFEST_SCHEMA,
            "intended_action": INTENDED_ACTION,
            "transition_class": REPORT_CLASS,
            "inputs_are_receipts_on_chain": True,
            "producer": PRODUCER,
            "producer_version": PRODUCER_VERSION,
        },
        "intended_action": INTENDED_ACTION,
        "transition_is_the_disposition_of_the_intended_action": True,
        "disposition": ALLOW,
        "health_report_authenticated": "NOT_PROVEN_BEYOND_RECEIPTED_PREREQUISITES",
        "authority_effect": "NONE",
    }
    already = (previous is not None and _evidence(previous).get("evidence_receipts", {}).get("health_check")
               == check["receipt_sha256"] and _evidence(previous).get("status") == status)
    return {
        "schema": RESULT_SCHEMA,
        "disposition": ALLOW,
        "node_id": node_id,
        "trigger_event": event,
        "report_status": status,
        "report_evidence": evidence,
        "transition_id": f"{REPORT_CLASS}:{node_id}:{trigger_receipt_sha256}",
        "predecessor_state_sha256": (previous["receipt_sha256"] if previous
                                     else hne.sha({"node_id": node_id, "health_report": None})),
        "successor_state_sha256": hne.sha(evidence),
        "hb_epoch": epoch,
        "already_current_receipt_sha256": previous["receipt_sha256"] if already else None,
        "authority_effect": "NONE",
    }


def _emitter():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("repo_transition_emit_for_health_report",
                                                  root / ".stegverse/transition-ledger/emit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def produce(trigger_receipt_sha256: Any, *, ledger_root: Any, repository: str = REPOSITORY) -> dict[str, Any]:
    """Plan, then append the report through the repository emitter (or return NOOP / FAIL_CLOSED)."""
    planned = plan(trigger_receipt_sha256, ledger_root=ledger_root, repository=repository)
    if planned["disposition"] != ALLOW:
        return planned
    if planned["already_current_receipt_sha256"]:
        return {**planned, "outcome": "NOOP_ALREADY_CURRENT", "report_emitted": False,
                "health_report_receipt_sha256": planned["already_current_receipt_sha256"]}
    emit = _emitter()
    if Path(ledger_root).expanduser().resolve() != emit.lr():
        return _non_allow(planned["node_id"], "LEDGER_ROOT_MISMATCH",
                          "the emitter's ledger root is not the ledger root that was read")
    receipt = emit.append(planned["transition_id"], REPORT_CLASS, planned["predecessor_state_sha256"],
                          planned["successor_state_sha256"], planned["report_evidence"], "NONE",
                          hb_epoch=planned["hb_epoch"])
    return {**planned, "outcome": "EMITTED", "report_emitted": True,
            "health_report_receipt_sha256": receipt["receipt_sha256"]}


__all__ = ["BINDING_CLASS", "EXISTENCE_CLASS", "FAILURE_CODE", "HEALTH_CHECK_CLASS", "HEALTH_CHECK_SCHEMA",
           "HEALTH_CHECK_RECEIPTED", "NODE_IDENTITY_BOUND", "NODE_REGISTRATION", "REASONS", "REPORT_CLASS",
           "REPORT_SCHEMA", "RESULT_SCHEMA", "TRIGGER_EVENTS", "UNHEALTHY", "plan", "produce"]
