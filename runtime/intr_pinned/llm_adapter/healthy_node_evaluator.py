"""LC-KV-13: decide REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE from receipted health reports only.

This is the E0 evaluator for gate CURRENT_NODE_HEALTH (StegVerse-Labs/.github
data/node-exchange/first-executable-conformance-v0.1.json, order 3, on_unknown
FAIL_CLOSED). It is deterministic and pure: it reads a transition-ledger directory
(HEAD.json plus receipts/<hex>.json) and nothing else. It uses no clock, no
network, no randomness and no LLM, and it never writes.

A health report counts only when all of these hold:
  * it is a receipt of class NODE_HEALTH_REPORTED with evidence schema
    stegverse.node-health-report/v1 for the requested node_id;
  * it is read back on the chain walked from HEAD.json to genesis;
  * every receipt on that walk hashes to its address: the file name, the
    receipt_sha256 field and sha256 of the canonical body without receipt_sha256
    all agree, and each link names the next one;
  * it belongs to the expected repository;
  * it is the newest NODE_HEALTH_REPORTED receipt for that node on the chain.
    "Currently" means chain position, not a timestamp; a newer non-HEALTHY report
    supersedes an older HEALTHY one.
ALLOW needs that report's status to be exactly HEALTHY and the requester's
transport to be INSTALLED. Anything else is a six-field non-ALLOW,
NODE_NOT_CURRENTLY_ADMITTED_HEALTHY:
  * DENY: the receipted report says something other than HEALTHY.
  * FAIL_CLOSED: the report is missing, unreceipted, forged, superseded, or the
    chain is unreadable, or the transport is not installed.

Interface for consumers such as layer 1 (KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE,
Lane D):

    evaluate(node_id, *, ledger_root, transport_state="INSTALLED",
             report_receipt_sha256=None, require_admission=False,
             repository=REPOSITORY) -> dict

  * The result always has "disposition" in {"ALLOW", "DENY", "FAIL_CLOSED"},
    "predicate", "node_id" and "healthy_node_established" (True only on ALLOW).
  * ALLOW adds "health_report_receipt_sha256", "health_status" = "HEALTHY",
    "chain_head_receipt_sha256" and "chain_length".
  * A non-ALLOW adds the six fields (failure_code, failed_predicate,
    required_evidence_or_repair, retry_entrypoint, owning_existing_goal,
    next_attempt) plus "reason", one of REASONS.
  * report_receipt_sha256: a report the requester cites. It must be on the chain
    and must be the current report.
  * require_admission=True (layer 1 and later stages): the newest
    NODE_INGRESS_* receipt for the node must also be NODE_INGRESS_ADMITTED with
    healthy_node_established true, citing that same current report. The ingress
    boundary itself evaluates with require_admission=False, because it is the
    admission.

A receipt is not an authentication. health_report_authenticated is
NOT_PROVEN here: AUTHENTICATED_RECIPROCAL_NODE_EXISTENCE and NODE_IDENTITY_BINDING
are earlier gates and are not observed by this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

ALLOW = "ALLOW"
DENY = "DENY"
FAIL_CLOSED = "FAIL_CLOSED"

PREDICATE = "REQUESTER_IS_CURRENTLY_ADMITTED_HEALTHY_NODE"
GATE = "CURRENT_NODE_HEALTH"
FAILURE_CODE = "NODE_NOT_CURRENTLY_ADMITTED_HEALTHY"
REPOSITORY = "StegVerse-org/LLM-adapter"
RESULT_SCHEMA = "stegverse.healthy-node-evaluation/v1"
HEALTH_REPORT_CLASS = "NODE_HEALTH_REPORTED"
HEALTH_REPORT_SCHEMA = "stegverse.node-health-report/v1"
HEALTHY = "HEALTHY"
INSTALLED = "INSTALLED"
INGRESS_ADMITTED_CLASS = "NODE_INGRESS_ADMITTED"
INGRESS_REFUSED_CLASS = "NODE_INGRESS_REFUSED"

RETRY_ENTRYPOINT = ("llm_adapter.healthy_node_evaluator.evaluate (via llm_adapter.node_ingress_boundary.admit, "
                    "POST /api/node-standing)")
OWNING_GOAL = ("KV-SKAP-VAULT-FUNCTIONAL-001 (StegVerse-Labs/.github#3324) via LC-KV-13/LC-KV-14, "
               "InTr and Mesh Destinations lane StegVerse-org/.github#162")
NEXT_ATTEMPT = ("re-evaluate when a new NODE_HEALTH_REPORTED receipt for this node is on the ledger chain; "
                "the evaluation is event-driven, never on a timer")

#: reason -> (disposition, required evidence or repair)
REASONS: dict[str, tuple[str, str]] = {
    "NODE_ID_INVALID": (FAIL_CLOSED, "a non-empty node_id"),
    "TRANSPORT_NOT_INSTALLED": (FAIL_CLOSED, "the requester's transport must be INSTALLED; a NOT_YET_ENABLED or "
                                "unknown transport establishes no healthy node"),
    "LEDGER_HEAD_UNREADABLE": (FAIL_CLOSED, "a readable HEAD.json naming a receipt on this repository's ledger"),
    "RECEIPT_MISSING_ON_CHAIN": (FAIL_CLOSED, "every receipt named by the chain must be present to read back"),
    "RECEIPT_HASH_MISMATCH": (FAIL_CLOSED, "every receipt on the chain must hash to its address "
                              "(sha256 of the body without receipt_sha256 equals the address)"),
    "RECEIPT_REPOSITORY_MISMATCH": (FAIL_CLOSED, "every receipt on the chain must belong to the expected repository"),
    "CHAIN_CYCLE": (FAIL_CLOSED, "a chain from HEAD.json to a genesis receipt without cycles"),
    "HEALTH_REPORT_MISSING": (FAIL_CLOSED, "a NODE_HEALTH_REPORTED receipt for this node on the chain from HEAD.json"),
    "HEALTH_REPORT_NOT_RECEIPTED": (FAIL_CLOSED, "the cited health report must be read back on the chain from "
                                    "HEAD.json with its body hash matching its address"),
    "HEALTH_REPORT_NOT_FOR_NODE": (FAIL_CLOSED, "the cited receipt must be a NODE_HEALTH_REPORTED report for this node"),
    "HEALTH_REPORT_SUPERSEDED": (FAIL_CLOSED, "cite the newest NODE_HEALTH_REPORTED receipt for this node"),
    "HEALTH_REPORTED_NOT_HEALTHY": (DENY, "a newer receipted report whose status is exactly HEALTHY"),
    "NODE_NOT_ADMITTED": (FAIL_CLOSED, "the newest NODE_INGRESS_* receipt for this node must be NODE_INGRESS_ADMITTED "
                          "with healthy_node_established true, citing the current health report"),
}

_HEX = re.compile(r"^[0-9a-f]{64}$")


def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canon(value)).hexdigest()


def _non_allow(node_id: Any, reason: str, detail: str, **extra: Any) -> dict[str, Any]:
    disposition, repair = REASONS[reason]
    return {
        "schema": RESULT_SCHEMA,
        "disposition": disposition,
        "predicate": PREDICATE,
        "gate": GATE,
        "node_id": node_id if isinstance(node_id, str) else None,
        "healthy_node_established": False,
        "reason": reason,
        "detail": detail,
        "failure_code": FAILURE_CODE,
        "failed_predicate": PREDICATE,
        "required_evidence_or_repair": repair,
        "retry_entrypoint": RETRY_ENTRYPOINT,
        "owning_existing_goal": OWNING_GOAL,
        "next_attempt": NEXT_ATTEMPT,
        "health_report_authenticated": "NOT_PROVEN",
        "authority_effect": "NONE_EVALUATION_ONLY",
        **extra,
    }


def read_chain(ledger_root: Any, repository: str = REPOSITORY) -> tuple[list[dict[str, Any]], str | None, str]:
    """Walk HEAD.json to genesis and return (receipts newest first, failure reason, detail)."""
    root = Path(ledger_root) if ledger_root is not None else None
    try:
        head = json.loads((root / "HEAD.json").read_text(encoding="utf-8"))
        cursor = head["receipt_sha256"]
    except Exception as exc:  # any unreadable HEAD is the same refusal
        return [], "LEDGER_HEAD_UNREADABLE", f"HEAD.json unreadable: {type(exc).__name__}"
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    while cursor is not None:
        if not isinstance(cursor, str) or not cursor.startswith("sha256:") or not _HEX.match(cursor[7:]):
            return chain, "RECEIPT_HASH_MISMATCH", f"malformed receipt address {cursor!r}"
        if cursor in seen:
            return chain, "CHAIN_CYCLE", f"cycle at {cursor}"
        seen.add(cursor)
        path = root / "receipts" / (cursor[7:] + ".json")
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return chain, "RECEIPT_MISSING_ON_CHAIN", f"{cursor} not readable: {type(exc).__name__}"
        if not isinstance(receipt, dict):
            return chain, "RECEIPT_HASH_MISMATCH", f"{cursor} is not an object"
        body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        if receipt.get("receipt_sha256") != cursor or sha(body) != cursor:
            return chain, "RECEIPT_HASH_MISMATCH", f"{cursor} does not hash to its address"
        if receipt.get("repository") != repository:
            return chain, "RECEIPT_REPOSITORY_MISMATCH", f"{cursor} names {receipt.get('repository')!r}"
        chain.append(receipt)
        cursor = receipt.get("previous_receipt_sha256")
    return chain, None, ""


def _is_report_for(receipt: Mapping[str, Any], node_id: str) -> bool:
    evidence = receipt.get("evidence")
    return (receipt.get("transition_class") == HEALTH_REPORT_CLASS and isinstance(evidence, Mapping)
            and evidence.get("schema") == HEALTH_REPORT_SCHEMA and evidence.get("node_id") == node_id)


def _ingress_node(receipt: Mapping[str, Any]) -> Any:
    evidence = receipt.get("evidence") if isinstance(receipt.get("evidence"), Mapping) else {}
    endpoint = evidence.get("node_endpoint") if isinstance(evidence.get("node_endpoint"), Mapping) else {}
    return endpoint.get("node_id")


def evaluate(node_id: Any, *, ledger_root: Any, transport_state: Any = INSTALLED,
             report_receipt_sha256: Any = None, require_admission: bool = False,
             repository: str = REPOSITORY) -> dict[str, Any]:
    """Return ALLOW only for the current, read-back, hash-verified HEALTHY report of node_id."""
    if not isinstance(node_id, str) or not node_id:
        return _non_allow(node_id, "NODE_ID_INVALID", "node_id must be a non-empty string")
    if transport_state != INSTALLED:
        return _non_allow(node_id, "TRANSPORT_NOT_INSTALLED", f"transport_state is {transport_state!r}")
    chain, failure, detail = read_chain(ledger_root, repository)
    if failure:
        return _non_allow(node_id, failure, detail)
    reports = [r for r in chain if _is_report_for(r, node_id)]
    if report_receipt_sha256 is not None:
        cited = next((r for r in chain if r["receipt_sha256"] == report_receipt_sha256), None)
        if cited is None:
            return _non_allow(node_id, "HEALTH_REPORT_NOT_RECEIPTED",
                              f"{report_receipt_sha256!r} is not on the chain from HEAD.json")
        if not _is_report_for(cited, node_id):
            return _non_allow(node_id, "HEALTH_REPORT_NOT_FOR_NODE", f"{report_receipt_sha256} is not a report for {node_id}")
    if not reports:
        return _non_allow(node_id, "HEALTH_REPORT_MISSING", f"no {HEALTH_REPORT_CLASS} receipt for {node_id} on the chain")
    current = reports[0]
    if report_receipt_sha256 is not None and current["receipt_sha256"] != report_receipt_sha256:
        return _non_allow(node_id, "HEALTH_REPORT_SUPERSEDED", f"current report is {current['receipt_sha256']}",
                          current_health_report_receipt_sha256=current["receipt_sha256"])
    status = current["evidence"].get("status")
    if status != HEALTHY:
        return _non_allow(node_id, "HEALTH_REPORTED_NOT_HEALTHY", f"current receipted report says {status!r}",
                          health_report_receipt_sha256=current["receipt_sha256"], health_status=status)
    if require_admission:
        ingress = next((r for r in chain if r.get("transition_class") in (INGRESS_ADMITTED_CLASS, INGRESS_REFUSED_CLASS)
                        and _ingress_node(r) == node_id), None)
        evidence = (ingress or {}).get("evidence") or {}
        if (ingress is None or ingress["transition_class"] != INGRESS_ADMITTED_CLASS
                or evidence.get("healthy_node_established") is not True
                or evidence.get("health_report_receipt_sha256") != current["receipt_sha256"]):
            return _non_allow(node_id, "NODE_NOT_ADMITTED", "no current healthy admission for this node on the chain",
                              health_report_receipt_sha256=current["receipt_sha256"])
    return {
        "schema": RESULT_SCHEMA,
        "disposition": ALLOW,
        "predicate": PREDICATE,
        "gate": GATE,
        "node_id": node_id,
        "healthy_node_established": True,
        "health_status": HEALTHY,
        "health_report_receipt_sha256": current["receipt_sha256"],
        "chain_head_receipt_sha256": chain[0]["receipt_sha256"],
        "chain_length": len(chain),
        "admission_required": bool(require_admission),
        "health_report_authenticated": "NOT_PROVEN",
        "authority_effect": "NONE_EVALUATION_ONLY",
    }


__all__ = ["ALLOW", "DENY", "FAIL_CLOSED", "FAILURE_CODE", "GATE", "HEALTH_REPORT_CLASS", "HEALTH_REPORT_SCHEMA",
           "HEALTHY", "INSTALLED", "PREDICATE", "REASONS", "REPOSITORY", "RESULT_SCHEMA", "evaluate", "read_chain"]
