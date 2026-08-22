"""Connector-neutral KnowledgeVault recoverable execution host.

KnowledgeVault persists execution continuity; extensions perform the actual external
operation. Recovery never creates authority, mutates an admitted envelope, or turns
an uncertain outcome into success.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .adapter import ExecutionEnvelopeError, canonical_sha256, validate_envelope


STATES = ("STARTED", "DISPATCHED", "OBSERVING", "TERMINAL", "ABANDONED")
ALLOWED_TRANSITIONS = {
    "STARTED": {"DISPATCHED", "ABANDONED"},
    "DISPATCHED": {"OBSERVING", "TERMINAL", "ABANDONED"},
    "OBSERVING": {"OBSERVING", "TERMINAL", "ABANDONED"},
    "TERMINAL": set(),
    "ABANDONED": set(),
}


class RecoveryJournalError(ExecutionEnvelopeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_record(record: dict[str, Any]) -> str:
    return canonical_sha256({k: v for k, v in record.items() if k != "record_sha256"})


def start_attempt(
    envelope: dict[str, Any],
    *,
    attempt_id: str,
    lease_owner: str | None = None,
    lease_epoch: int = 0,
    lease_expires_at: str | None = None,
) -> dict[str, Any]:
    validate_envelope(envelope)
    if not attempt_id:
        raise RecoveryJournalError("attempt_id is required")
    record = {
        "schema_version": "0.1",
        "attempt_id": attempt_id,
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": canonical_sha256(envelope),
        "idempotency_key": envelope["idempotency"]["key"],
        "state": "STARTED",
        "sequence": 0,
        "recorded_at": _now(),
        "result": None,
        "side_effect_absence_confirmed": False,
        "receipt_refs": [],
        "lease": {"owner": lease_owner, "epoch": lease_epoch, "expires_at": lease_expires_at},
        "previous_record_sha256": None,
    }
    record["record_sha256"] = _hash_record(record)
    return record


def advance_attempt(
    prior: dict[str, Any],
    *,
    state: str,
    result: str | None = None,
    side_effect_absence_confirmed: bool = False,
    receipt_refs: list[str] | None = None,
    lease_owner: str | None = None,
    lease_epoch: int | None = None,
    lease_expires_at: str | None = None,
) -> dict[str, Any]:
    if prior.get("record_sha256") != _hash_record(prior):
        raise RecoveryJournalError("prior journal record hash does not verify")
    current = prior.get("state")
    if current not in STATES or state not in ALLOWED_TRANSITIONS[current]:
        raise RecoveryJournalError(f"non-monotonic transition rejected: {current} -> {state}")

    old_lease = prior.get("lease") or {}
    old_epoch = int(old_lease.get("epoch", 0))
    next_epoch = old_epoch if lease_epoch is None else int(lease_epoch)
    if next_epoch < old_epoch:
        raise RecoveryJournalError("lease epoch may not move backward")
    if lease_owner is not None and old_lease.get("owner") not in {None, lease_owner} and next_epoch <= old_epoch:
        raise RecoveryJournalError("concurrent worker requires a newer lease epoch")

    if state == "TERMINAL" and result not in {"EXECUTED", "FAILED", "INDETERMINATE"}:
        raise RecoveryJournalError("terminal state requires a terminal result")
    if result == "INDETERMINATE" and side_effect_absence_confirmed:
        raise RecoveryJournalError("indeterminate result cannot confirm side-effect absence")
    if result == "EXECUTED" and side_effect_absence_confirmed:
        raise RecoveryJournalError("executed result cannot claim side-effect absence")

    record = {
        "schema_version": "0.1",
        "attempt_id": prior["attempt_id"],
        "envelope_id": prior["envelope_id"],
        "envelope_sha256": prior["envelope_sha256"],
        "idempotency_key": prior["idempotency_key"],
        "state": state,
        "sequence": int(prior["sequence"]) + 1,
        "recorded_at": _now(),
        "result": result,
        "side_effect_absence_confirmed": bool(side_effect_absence_confirmed),
        "receipt_refs": list(receipt_refs or []),
        "lease": {
            "owner": lease_owner if lease_owner is not None else old_lease.get("owner"),
            "epoch": next_epoch,
            "expires_at": lease_expires_at if lease_expires_at is not None else old_lease.get("expires_at"),
        },
        "previous_record_sha256": prior["record_sha256"],
    }
    record["record_sha256"] = _hash_record(record)
    return record


def verify_journal(records: list[dict[str, Any]]) -> None:
    if not records:
        raise RecoveryJournalError("attempt journal is empty")
    first = records[0]
    if first.get("state") != "STARTED" or first.get("sequence") != 0 or first.get("previous_record_sha256") is not None:
        raise RecoveryJournalError("journal must begin with STARTED sequence 0")
    attempt_id = first.get("attempt_id")
    envelope_hash = first.get("envelope_sha256")
    previous = None
    for index, record in enumerate(records):
        if record.get("record_sha256") != _hash_record(record):
            raise RecoveryJournalError(f"journal record hash mismatch at sequence {index}")
        if record.get("sequence") != index:
            raise RecoveryJournalError("journal sequence is not contiguous")
        if record.get("attempt_id") != attempt_id or record.get("envelope_sha256") != envelope_hash:
            raise RecoveryJournalError("attempt or envelope binding changed")
        if previous is not None:
            if record.get("previous_record_sha256") != previous.get("record_sha256"):
                raise RecoveryJournalError("journal hash chain is broken")
            if record.get("state") not in ALLOWED_TRANSITIONS.get(previous.get("state"), set()):
                raise RecoveryJournalError("journal contains an illegal state transition")
        previous = record


def recovery_decision(records: list[dict[str, Any]], *, lease_stale: bool = False) -> dict[str, Any]:
    verify_journal(records)
    latest = records[-1]
    state = latest["state"]
    result = latest.get("result")

    if state == "TERMINAL" and result == "EXECUTED":
        decision, reason = "STOP", "executed receipt is terminal and suppresses duplicate dispatch"
    elif state == "TERMINAL" and result == "FAILED" and latest.get("side_effect_absence_confirmed"):
        decision, reason = "RETRY_EXACT", "failure confirms no side effect; only the identical envelope may retry"
    elif state == "TERMINAL" and result == "INDETERMINATE":
        decision, reason = "VERIFY_EXTERNALLY", "completion state remains indeterminate"
    elif state == "OBSERVING":
        decision, reason = "RESUME_OBSERVATION", "an already-dispatched attempt remains under observation"
    elif state == "DISPATCHED":
        decision, reason = "VERIFY_EXTERNALLY", "dispatch occurred without a terminal outcome"
    elif state == "STARTED" and lease_stale:
        decision, reason = "RETRY_EXACT", "dispatch was not recorded and the prior lease is stale"
    elif state == "STARTED":
        decision, reason = "ASK", "another current lease may still own the undispatched attempt"
    else:
        decision, reason = "STOP", "attempt was abandoned or cannot safely continue"

    output = {
        "schema_version": "0.1",
        "attempt_id": latest["attempt_id"],
        "envelope_sha256": latest["envelope_sha256"],
        "journal_sequence": latest["sequence"],
        "decision": decision,
        "reason": reason,
        "exact_envelope_required": decision == "RETRY_EXACT",
        "new_authority_granted": False,
        "recorded_at": _now(),
    }
    output["decision_sha256"] = canonical_sha256(output)
    return output
