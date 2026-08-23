"""Durable KnowledgeVault journal for selected-edge communication execution.

This module is transport-neutral. It accepts already-produced StegTalk selection,
lease, and edge execution evidence, validates their bindings, and persists one
recoverable attempt stream through KnowledgeVaultExecutionStore. It does not
select a bearer, execute a transport, or create authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .adapter import canonical_sha256
from .vault_store import KnowledgeVaultExecutionStore, VaultStoreError


class CommunicationRuntimeJournalError(VaultStoreError):
    pass


@dataclass(frozen=True)
class RecoveredCommunicationAttempt:
    attempt_id: str
    selection: Dict[str, Any]
    lease: Dict[str, Any]
    execution_receipt: Optional[Dict[str, Any]]
    recovery_records: list[Dict[str, Any]]


def _stegtalk_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stegtalk_selection_sha256(value: Any) -> str:
    """Return the raw 64-hex profile emitted by ST-031 portable *_sha256 fields."""
    return _stegtalk_digest(value)


def stegtalk_communication_sha256(value: Any) -> str:
    """Return the prefixed stable-hash profile emitted by ST-032 receipts.

    ST-031 and ST-032 deliberately expose different representations at their
    existing schema boundaries. KnowledgeVault verifies each producer contract
    exactly rather than rewriting either representation into a local form.
    """
    return "sha256:" + _stegtalk_digest(value)


def _require(record: Dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if record.get(key) in (None, "")]
    if missing:
        raise CommunicationRuntimeJournalError("communication runtime record missing: %s" % ", ".join(missing))


def _selection_binding(selection: Dict[str, Any]) -> None:
    _require(selection, "attempt_id", "selection_sha256", "selected_edge_id", "selected_bearer")
    claimed = str(selection["selection_sha256"])
    body = dict(selection)
    body.pop("selection_sha256", None)
    calculated = stegtalk_selection_sha256(body)
    if claimed != calculated:
        raise CommunicationRuntimeJournalError("selection receipt hash mismatch")


def _lease_binding(selection: Dict[str, Any], lease: Dict[str, Any]) -> None:
    _require(lease, "attempt_id", "edge_id", "lease_epoch", "expires_at")
    if lease["attempt_id"] != selection["attempt_id"]:
        raise CommunicationRuntimeJournalError("lease attempt does not match selection")
    if lease["edge_id"] != selection["selected_edge_id"]:
        raise CommunicationRuntimeJournalError("lease edge does not match selection")
    if int(lease["lease_epoch"]) < 1:
        raise CommunicationRuntimeJournalError("lease epoch must be positive")


def _execution_binding(selection: Dict[str, Any], lease: Dict[str, Any], receipt: Dict[str, Any]) -> None:
    _require(
        receipt,
        "attempt_id",
        "selection_sha256",
        "edge_id",
        "bearer",
        "idempotency_key",
        "lease_epoch",
        "dispatch_state",
        "outcome",
        "receipt_sha256",
    )
    if receipt["attempt_id"] != selection["attempt_id"]:
        raise CommunicationRuntimeJournalError("execution attempt does not match selection")
    if receipt["selection_sha256"] != selection["selection_sha256"]:
        raise CommunicationRuntimeJournalError("execution selection hash mismatch")
    if receipt["edge_id"] != selection["selected_edge_id"]:
        raise CommunicationRuntimeJournalError("execution edge does not match selection")
    if receipt["bearer"] != selection["selected_bearer"]:
        raise CommunicationRuntimeJournalError("execution bearer does not match selection")
    if int(receipt["lease_epoch"]) != int(lease["lease_epoch"]):
        raise CommunicationRuntimeJournalError("execution lease epoch mismatch")
    body = dict(receipt)
    claimed = str(body.pop("receipt_sha256"))
    calculated = stegtalk_communication_sha256(body)
    if claimed != calculated:
        raise CommunicationRuntimeJournalError("edge execution receipt hash mismatch")
    if receipt["outcome"] in {"INDETERMINATE", "TIMEOUT_AFTER_DISPATCH", "UNKNOWN_AFTER_DISPATCH"} and bool(receipt.get("side_effect_absence_confirmed")):
        raise CommunicationRuntimeJournalError("ambiguous dispatch cannot confirm side-effect absence")


class CommunicationRuntimeJournal:
    """One durable KV interface for selection, lease, dispatch and recovery state."""

    def __init__(self, store: KnowledgeVaultExecutionStore):
        self.store = store

    @staticmethod
    def stream_id(attempt_id: str) -> str:
        return "comm-" + canonical_sha256(attempt_id)[:32]

    def begin(self, *, selection: Dict[str, Any], lease: Dict[str, Any]) -> str:
        _selection_binding(selection)
        _lease_binding(selection, lease)
        stream_id = self.stream_id(str(selection["attempt_id"]))
        existing = self.store.read_stream("Attempts", stream_id)
        if existing:
            first = existing[0]
            if (
                first.get("selection_sha256") != selection["selection_sha256"]
                or first.get("selected_edge_id") != selection["selected_edge_id"]
                or int(first.get("lease_epoch", 0)) != int(lease["lease_epoch"])
            ):
                raise CommunicationRuntimeJournalError("attempt stream already bound to different selection/lease")
            return stream_id

        self.store.append_receipt(stream_id, selection)
        self.store.append_attempt(
            stream_id,
            {
                "record_type": "COMMUNICATION_ATTEMPT_BOUND",
                "attempt_id": selection["attempt_id"],
                "selection_sha256": selection["selection_sha256"],
                "selected_edge_id": selection["selected_edge_id"],
                "selected_bearer": selection["selected_bearer"],
                "lease_epoch": int(lease["lease_epoch"]),
                "lease_expires_at": lease["expires_at"],
                "state": "LEASED",
                "authority_created": False,
            },
        )
        return stream_id

    def record_execution(self, *, selection: Dict[str, Any], lease: Dict[str, Any], receipt: Dict[str, Any]) -> str:
        _selection_binding(selection)
        _lease_binding(selection, lease)
        _execution_binding(selection, lease, receipt)
        stream_id = self.begin(selection=selection, lease=lease)

        attempts = self.store.read_stream("Attempts", stream_id)
        prior_execution_hashes = {
            row.get("edge_execution_receipt_sha256")
            for row in attempts
            if row.get("record_type") == "EDGE_EXECUTION_OBSERVED"
        }
        if receipt["receipt_sha256"] in prior_execution_hashes:
            return stream_id

        for row in attempts:
            if row.get("record_type") != "EDGE_EXECUTION_OBSERVED":
                continue
            if row.get("idempotency_key") == receipt["idempotency_key"] and row.get("edge_execution_receipt_sha256") != receipt["receipt_sha256"]:
                raise CommunicationRuntimeJournalError("idempotency key already bound to different execution receipt")

        self.store.append_receipt(stream_id, receipt)
        self.store.append_attempt(
            stream_id,
            {
                "record_type": "EDGE_EXECUTION_OBSERVED",
                "attempt_id": receipt["attempt_id"],
                "selection_sha256": receipt["selection_sha256"],
                "selected_edge_id": receipt["edge_id"],
                "selected_bearer": receipt["bearer"],
                "lease_epoch": int(receipt["lease_epoch"]),
                "idempotency_key": receipt["idempotency_key"],
                "dispatch_state": receipt["dispatch_state"],
                "outcome": receipt["outcome"],
                "side_effect_absence_confirmed": bool(receipt.get("side_effect_absence_confirmed", False)),
                "edge_execution_receipt_sha256": receipt["receipt_sha256"],
                "state": "TERMINAL" if receipt["outcome"] in {"DELIVERED", "ACKNOWLEDGED", "EXECUTED", "FAILED"} else "OBSERVING",
                "authority_created": False,
            },
        )
        return stream_id

    def record_recovery(self, *, attempt_id: str, decision: Dict[str, Any]) -> str:
        _require(decision, "action", "reason")
        if bool(decision.get("new_authority_granted", False)):
            raise CommunicationRuntimeJournalError("recovery cannot grant new authority")
        stream_id = self.stream_id(attempt_id)
        self.store.append_recovery(
            stream_id,
            {
                "record_type": "COMMUNICATION_RECOVERY_DECISION",
                "attempt_id": attempt_id,
                "action": decision["action"],
                "reason": decision["reason"],
                "fallback": decision.get("fallback"),
                "new_authority_granted": False,
            },
        )
        return stream_id

    def recover(self, attempt_id: str) -> RecoveredCommunicationAttempt:
        stream_id = self.stream_id(attempt_id)
        receipts = self.store.read_stream("Receipts", stream_id)
        attempts = self.store.read_stream("Attempts", stream_id)
        recovery = self.store.read_stream("Recovery", stream_id)
        if not receipts or not attempts:
            raise CommunicationRuntimeJournalError("communication attempt is not durably bound")
        selection = receipts[0]
        if selection.get("attempt_id") != attempt_id:
            raise CommunicationRuntimeJournalError("recovered selection attempt mismatch")
        bound = attempts[0]
        lease = {
            "attempt_id": attempt_id,
            "edge_id": bound["selected_edge_id"],
            "lease_epoch": bound["lease_epoch"],
            "expires_at": bound["lease_expires_at"],
        }
        execution_receipt = receipts[-1] if len(receipts) > 1 else None
        if execution_receipt is not None:
            _execution_binding(selection, lease, execution_receipt)
        return RecoveredCommunicationAttempt(
            attempt_id=attempt_id,
            selection=selection,
            lease=lease,
            execution_receipt=execution_receipt,
            recovery_records=recovery,
        )
