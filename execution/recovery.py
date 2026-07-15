"""Recoverable governed execution orchestration.

This module reconstructs connector-attempt state without creating authority,
changing the authorized envelope, or converting uncertainty into success.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class RecoveryError(ValueError):
    """Raised when an attempt journal or recovery transition is inadmissible."""


@dataclass(frozen=True)
class RecoveryDecision:
    decision: str
    reason: str


_ALLOWED_TRANSITIONS = {
    "STARTED": {"DISPATCHED", "ABANDONED"},
    "DISPATCHED": {"OBSERVING", "TERMINAL", "ABANDONED"},
    "OBSERVING": {"TERMINAL", "ABANDONED"},
    "TERMINAL": set(),
    "ABANDONED": set(),
}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def validate_journal(journal: dict[str, Any]) -> None:
    required = {
        "schema_version", "journal_id", "envelope_id", "envelope_sha256",
        "idempotency_key", "state", "revision", "lease", "events",
        "authority_note",
    }
    missing = sorted(required - journal.keys())
    if missing:
        raise RecoveryError(f"missing fields: {missing}")
    if journal["schema_version"] != "0.1":
        raise RecoveryError("schema_version must be 0.1")
    if journal["state"] not in _ALLOWED_TRANSITIONS:
        raise RecoveryError("invalid journal state")
    if journal["revision"] < 0:
        raise RecoveryError("revision must be non-negative")
    events = journal["events"]
    if not isinstance(events, list) or not events:
        raise RecoveryError("events must be non-empty")
    sequences = [event.get("sequence") for event in events]
    if sequences != list(range(len(events))):
        raise RecoveryError("event sequences must be contiguous and monotonic")
    if journal["authority_note"] != (
        "Recovery restores execution state only; it does not grant or expand authority."
    ):
        raise RecoveryError("authority boundary missing")


def acquire_lease(
    journal: dict[str, Any], *, owner: str, acquired_at: str, expires_at: str,
    expected_revision: int,
) -> dict[str, Any]:
    validate_journal(journal)
    if journal["revision"] != expected_revision:
        raise RecoveryError("stale journal revision")
    current_expiry = _parse_time(journal["lease"]["expires_at"])
    requested_start = _parse_time(acquired_at)
    if requested_start < current_expiry and journal["lease"]["owner"] != owner:
        raise RecoveryError("active lease held by another worker")
    updated = deepcopy(journal)
    updated["lease"] = {
        "owner": owner,
        "acquired_at": acquired_at,
        "expires_at": expires_at,
    }
    updated["revision"] += 1
    return updated


def transition(
    journal: dict[str, Any], *, new_state: str, event: str, actor: str,
    recorded_at: str, receipt_sha256: str, expected_revision: int,
    terminal_receipt_ref: str | None = None,
) -> dict[str, Any]:
    validate_journal(journal)
    if journal["revision"] != expected_revision:
        raise RecoveryError("stale journal revision")
    if new_state not in _ALLOWED_TRANSITIONS[journal["state"]]:
        raise RecoveryError(f"invalid transition {journal['state']} -> {new_state}")
    updated = deepcopy(journal)
    updated["state"] = new_state
    updated["revision"] += 1
    updated["events"].append({
        "sequence": len(updated["events"]),
        "event": event,
        "recorded_at": recorded_at,
        "actor": actor,
        "receipt_sha256": receipt_sha256,
    })
    if new_state == "TERMINAL":
        if not terminal_receipt_ref:
            raise RecoveryError("terminal transition requires receipt reference")
        updated["terminal_receipt_ref"] = terminal_receipt_ref
    return updated


def decide_recovery(
    journal: dict[str, Any], *, receipt_result: str | None,
    side_effect_absence_confirmed: bool = False,
    connector_supports_observation: bool = False,
    authority_still_current: bool = True,
) -> RecoveryDecision:
    validate_journal(journal)
    if journal["state"] in {"TERMINAL", "ABANDONED"}:
        return RecoveryDecision("STOP", "attempt is already terminal")
    if not authority_still_current:
        return RecoveryDecision("ASK", "current authority must be re-established")
    if receipt_result == "EXECUTED":
        return RecoveryDecision("STOP", "executed receipt suppresses duplicate dispatch")
    if receipt_result == "FAILED" and side_effect_absence_confirmed:
        return RecoveryDecision("RETRY_EXACT", "confirmed absence permits exact-envelope retry")
    if receipt_result in {"INDETERMINATE", "FAILED"}:
        return RecoveryDecision("VERIFY_EXTERNALLY", "side effect remains uncertain")
    if journal["state"] in {"DISPATCHED", "OBSERVING"} and connector_supports_observation:
        return RecoveryDecision("RESUME_OBSERVATION", "connector observation can continue")
    if journal["state"] == "STARTED":
        return RecoveryDecision("RETRY_EXACT", "no dispatch has been recorded")
    return RecoveryDecision("ASK", "recovery cannot safely determine the next action")
