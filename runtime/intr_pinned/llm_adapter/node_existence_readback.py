"""Read a StegOS reciprocal-existence observation back onto this repository's chain.

Class B piece (1) of the LC-KV-13 inventory (StegVerse-org/.github#162).

The writer is StegOS's `observe_reciprocal_node_existence`, run as the broker
capability `observe-reciprocal-node-existence` on `NodeEventExecutionBroker`
(EVENT_EPHEMERAL). It returns a hash-sealed broker receipt,
`stegos.node-event-execution-broker.receipt/v3`, that nothing appends to a
ledger. This adapter is that missing read-back. It turns one such broker receipt
into an AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE receipt on this repository's
chain, with evidence `{node_id, disposition}`, which is the shape
node_health_report_producer (#429) reads.

Field mapping. The observation itself carries no node identifier, so `node_id`
is the broker receipt's `node_ref`: the retained StegOS Node (`SV-NODE-...`)
whose lease ran the observation. No mapping table, no default.

Trigger: the arrival of a broker receipt (`produce(broker_receipt, ...)`). Never a
timer or a poll. This module does not run the observation, so it makes no
network read; it verifies what the broker sealed.

FAIL_CLOSED, with six fields and nothing appended, when any of these is true:
* the broker receipt's schema, state or authority invariants differ;
* `receipt_hash` or `result_hash` doesn't match the canonical body;
* the capability isn't the existence observer;
* the observation isn't an ALLOW from an independent public HTTPS read with no
  credential;
* `node_ref` isn't a retained Node reference;
* the observation carries no well-formed `node_identity_key` public-key reference
  naming `node_ref`. Every node read back here seeks KV standing, so the key is
  REQUIRED (the same rule StegOS enforces at its read-back for KV standing);
* the chain doesn't read back.

The broker hash proves integrity, not authenticity, so the receipt records
`read_back_authenticated` NOT_PROVEN_BEYOND_BROKER_RECEIPT_HASH.

`plan()` is the deterministic core: no clock, network or randomness, and it never
writes. `produce()` appends through `.stegverse/transition-ledger/emit.py`. The
same broker receipt read back twice is NOOP_ALREADY_CURRENT.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from llm_adapter import healthy_node_evaluator as hne
from llm_adapter import node_receipt_common as common

ALLOW = common.ALLOW
REPOSITORY = common.REPOSITORY
TRANSITION_CLASS = common.EXISTENCE_CLASS
EVIDENCE_SCHEMA = "stegverse.node-existence-readback/v1"
RESULT_SCHEMA = "stegverse.node-existence-readback-result/v1"
BROKER_RECEIPT_SCHEMA = "stegos.node-event-execution-broker.receipt/v3"
BROKER_STATE = "CANONICAL_RUNTIME_CAPABILITY_EXECUTION_OBSERVED"
CAPABILITY = "observe-reciprocal-node-existence"
OBSERVATION_SCHEMA = "stegverse.node-exchange-reciprocal-existence/v0.1"
OBSERVATION_ORIGIN = "INDEPENDENT_PUBLIC_HTTPS"
FAILURE_CODE = "NODE_EXISTENCE_NOT_READ_BACK"
RETRY_ENTRYPOINT = "llm_adapter.node_existence_readback.produce(broker_receipt, ledger_root=...)"
NEXT_ATTEMPT = ("fires again when StegOS delivers a new broker receipt from observe-reciprocal-node-existence "
                "for this node. Never on a timer.")

#: Broker invariants copied from StegOS stegos/node_event_execution_broker.py (e63f7e89).
BROKER_INVARIANTS = {
    "bridge_owns_runtime_lifecycle": False,
    "runtime_class": "EVENT_EPHEMERAL",
    "claim_or_fence_minted_by_broker": False,
    "runtime_lease_opened_by_broker": False,
    "intr_transition_admission_minted_by_broker": False,
    "transition_authority": "Interlock/InTr",
    "credential_authority": "TV/TVC",
    "github_runtime_authority": "NONE",
    "authority_effect": "NONE_EXECUTION_EVIDENCE_ONLY",
}

REASONS: dict[str, tuple[str, str]] = {
    "BROKER_RECEIPT_INVALID": ("BROKER_RECEIPT_SEALED", f"a {BROKER_RECEIPT_SCHEMA} object in state {BROKER_STATE} "
                               "with the StegOS broker authority invariants"),
    "BROKER_RECEIPT_HASH_MISMATCH": ("BROKER_RECEIPT_SEALED", "receipt_hash and result_hash must equal sha256 of "
                                     "the canonical body and result (StegOS sha256_uri)"),
    "CAPABILITY_NOT_EXISTENCE_OBSERVER": ("BROKER_RECEIPT_SEALED", f"a broker receipt from capability {CAPABILITY}"),
    "OBSERVATION_INVALID": (TRANSITION_CLASS, f"an {OBSERVATION_SCHEMA} observation for gate {TRANSITION_CLASS} "
                            f"from {OBSERVATION_ORIGIN}, credential_used false, with a profile URL and profile_sha256"),
    "OBSERVATION_NOT_ALLOW": (TRANSITION_CLASS, "a reciprocal-existence observation whose disposition is ALLOW"),
    "NODE_REF_INVALID": (TRANSITION_CLASS, "a broker receipt whose node_ref names a retained Node (SV-NODE-...)"),
    "NODE_IDENTITY_KEY_NOT_PUBLISHED": (
        "NODE_IDENTITY_KEY_REFERENCE_PUBLISHED_FOR_KV_STANDING",
        "an observation of a profile that publishes node_identity_key with exactly {algorithm: Ed25519, key_id, "
        "node_id equal to the broker node_ref, public_key_b64: a 32-byte Ed25519 public key, custody: TV/TVC}, "
        "a public key reference only, observed by StegOS with standing_request KV_STANDING or a declared "
        "KV_STANDING purpose"),
}

_HEX = re.compile(r"^[0-9a-f]{64}$")


def _stegos_sha256_uri(value: Any) -> str:
    """StegOS universal_intr_transport.sha256_uri, reproduced without importing StegOS."""
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _fail(reason: str, detail: str, node_id: Any = None) -> dict[str, Any]:
    return common.non_allow(schema=RESULT_SCHEMA, failure_code=FAILURE_CODE, reasons=REASONS, reason=reason,
                            detail=detail, retry_entrypoint=RETRY_ENTRYPOINT, next_attempt=NEXT_ATTEMPT,
                            node_id=node_id)


def _check_broker_receipt(receipt: Any) -> tuple[str | None, str]:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != BROKER_RECEIPT_SCHEMA \
            or receipt.get("state") != BROKER_STATE:
        return "BROKER_RECEIPT_INVALID", "not a sealed broker receipt"
    for key, expected in BROKER_INVARIANTS.items():
        if receipt.get(key) != expected:
            return "BROKER_RECEIPT_INVALID", f"broker invariant {key} is {receipt.get(key)!r}"
    body = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    try:
        sealed = _stegos_sha256_uri(body) == receipt.get("receipt_hash")
        result_sealed = _stegos_sha256_uri(receipt.get("result")) == receipt.get("result_hash")
    except (TypeError, ValueError):
        sealed = result_sealed = False
    if not (sealed and result_sealed):
        return "BROKER_RECEIPT_HASH_MISMATCH", "receipt_hash or result_hash does not match"
    if receipt.get("capability_adapter") != CAPABILITY:
        return "CAPABILITY_NOT_EXISTENCE_OBSERVER", f"capability {receipt.get('capability_adapter')!r}"
    return None, ""


def _check_observation(result: Any) -> tuple[str | None, str]:
    if not isinstance(result, Mapping) or result.get("schema") != OBSERVATION_SCHEMA \
            or result.get("gate") != TRANSITION_CLASS:
        return "OBSERVATION_INVALID", "not a reciprocal-existence observation"
    if result.get("disposition") != ALLOW or result.get("status") != "RECIPROCAL_NODE_EXISTENCE_OBSERVED":
        return "OBSERVATION_NOT_ALLOW", f"observation disposition {result.get('disposition')!r}"
    url = result.get("observed_profile_url")
    if (result.get("observation_origin") != OBSERVATION_ORIGIN or result.get("credential_used") is not False
            or not isinstance(url, str) or not url.startswith("https://") or not url.endswith("/intr/profile")
            or not isinstance(result.get("profile_sha256"), str) or not _HEX.match(result["profile_sha256"])
            or not isinstance(result.get("required_profile"), str) or not result["required_profile"]):
        return "OBSERVATION_INVALID", "origin, credential use, profile URL, profile_sha256 or required_profile"
    return None, ""


def plan(broker_receipt: Any, *, ledger_root: Any, repository: str = REPOSITORY) -> dict[str, Any]:
    """Deterministic core: decide, from the broker receipt and the chain, the existence receipt to append."""
    reason, detail = _check_broker_receipt(broker_receipt)
    if reason:
        return _fail(reason, detail)
    result = broker_receipt["result"]
    reason, detail = _check_observation(result)
    node_ref = broker_receipt.get("node_ref")
    if reason:
        return _fail(reason, detail, node_ref)
    if not isinstance(node_ref, str) or not node_ref.startswith("SV-NODE-") or len(node_ref) <= len("SV-NODE-"):
        return _fail("NODE_REF_INVALID", f"node_ref {node_ref!r}")
    key = result.get("node_identity_key")
    key_failure = "node_identity_key_required_for_kv_standing" if key is None else common.node_identity_key_failure(key)
    if key_failure is None and key["node_id"] != node_ref:
        key_failure = "node_identity_key_node_id_not_broker_node_ref"
    if key_failure:
        return _fail("NODE_IDENTITY_KEY_NOT_PUBLISHED", key_failure, node_ref)
    chain, failure, detail = common.read_chain(ledger_root, repository, allow_empty=True)
    if failure:
        return _fail(failure, detail, node_ref)
    epoch = common.chain_epoch(chain)
    if epoch is None:
        return _fail("LEDGER_HEAD_UNREADABLE", "the HEAD receipt has no integer heartbeat epoch", node_ref)

    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "node_id": node_ref,
        "disposition": ALLOW,
        "gate": TRANSITION_CLASS,
        "node_id_source": "BROKER_RECEIPT_NODE_REF",
        "source_broker_receipt": {
            "schema": BROKER_RECEIPT_SCHEMA,
            "receipt_hash": broker_receipt["receipt_hash"],
            "result_hash": broker_receipt["result_hash"],
            "capability_adapter": CAPABILITY,
            "task_id": broker_receipt.get("task_id"),
            "cosv": broker_receipt.get("cosv"),
            "node_genesis_hash": broker_receipt.get("node_genesis_hash"),
            "node_state_generation": broker_receipt.get("node_state_generation"),
            "node_state_commitment": broker_receipt.get("node_state_commitment"),
            "runtime_lease_id": broker_receipt.get("runtime_lease_id"),
            "worker_claim_id": broker_receipt.get("worker_claim_id"),
            "worker_fence": broker_receipt.get("worker_fence"),
        },
        "observation": {
            "schema": OBSERVATION_SCHEMA,
            "observation_origin": OBSERVATION_ORIGIN,
            "observed_profile_url": result["observed_profile_url"],
            "profile_sha256": result["profile_sha256"],
            "required_profile": result["required_profile"],
            "credential_used": False,
            "standing_request": common.KV_STANDING,
            "node_identity_key": dict(key),
        },
        "identity_established": False,
        "health_established": False,
        "read_back_authenticated": "NOT_PROVEN_BEYOND_BROKER_RECEIPT_HASH",
        "authority_effect": "NONE",
    }
    previous = next((r for r in chain if r.get("transition_class") == TRANSITION_CLASS
                     and common.evidence(r).get("node_id") == node_ref), None)
    already = next((r["receipt_sha256"] for r in chain if r.get("transition_class") == TRANSITION_CLASS
                    and common.evidence(r).get("source_broker_receipt", {}).get("receipt_hash")
                    == broker_receipt["receipt_hash"]), None)
    return {
        "schema": RESULT_SCHEMA,
        "disposition": ALLOW,
        "node_id": node_ref,
        "receipt_evidence": evidence,
        "transition_id": f"{TRANSITION_CLASS}:{node_ref}:{broker_receipt['receipt_hash']}",
        "predecessor_state_sha256": (previous["receipt_sha256"] if previous
                                     else hne.sha({"node_id": node_ref, "existence": None})),
        "successor_state_sha256": hne.sha(evidence),
        "hb_epoch": epoch,
        "already_current_receipt_sha256": already,
        "authority_effect": "NONE",
    }


def produce(broker_receipt: Any, *, ledger_root: Any, repository: str = REPOSITORY) -> dict[str, Any]:
    """Plan, then append the existence receipt (or return NOOP / FAIL_CLOSED)."""
    planned = plan(broker_receipt, ledger_root=ledger_root, repository=repository)
    return common.produce(planned, TRANSITION_CLASS, ledger_root, lambda: _fail(
        "LEDGER_ROOT_MISMATCH", "the emitter's ledger root is not the ledger root that was read", planned.get("node_id")))


__all__ = ["BROKER_RECEIPT_SCHEMA", "CAPABILITY", "EVIDENCE_SCHEMA", "FAILURE_CODE", "REASONS", "TRANSITION_CLASS",
           "plan", "produce"]
