"""Connector-neutral governed action execution helpers.

This module prepares bounded connector calls and classifies connector outcomes. It
never derives authority and never performs a live external action by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class ExecutionEnvelopeError(ValueError):
    """Raised when an execution envelope violates mandatory invariants."""


@dataclass(frozen=True)
class ConnectorResult:
    status: str
    platform_object_id: str | None = None
    platform_url: str | None = None
    confirmation: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    side_effect_absence_confirmed: bool = False


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_envelope(envelope: dict[str, Any]) -> None:
    required = {
        "schema_version", "envelope_id", "instruction_ref", "authority_decision",
        "action", "resource", "destination", "payload", "connector",
        "idempotency", "receipt_required", "state",
    }
    missing = sorted(required - envelope.keys())
    if missing:
        raise ExecutionEnvelopeError(f"missing fields: {missing}")
    if envelope["schema_version"] != "0.1":
        raise ExecutionEnvelopeError("schema_version must be 0.1")
    if envelope["state"] != "PREPARED":
        raise ExecutionEnvelopeError("new envelopes must be PREPARED")
    if envelope["receipt_required"] is not True:
        raise ExecutionEnvelopeError("every external attempt requires a receipt")
    decision = envelope["authority_decision"]
    if decision.get("outcome") != "ACT":
        raise ExecutionEnvelopeError("only ACT decisions may produce executable envelopes")
    for field in ("decision_sha256",):
        value = decision.get(field, "")
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ExecutionEnvelopeError(f"invalid {field}")
    payload_hash = envelope["payload"].get("content_sha256", "")
    if len(payload_hash) != 64 or any(c not in "0123456789abcdef" for c in payload_hash):
        raise ExecutionEnvelopeError("invalid payload.content_sha256")
    if not envelope["idempotency"].get("key"):
        raise ExecutionEnvelopeError("idempotency key required")


def prepare_connector_request(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return the exact connector request bound by the admitted envelope."""
    validate_envelope(envelope)
    return {
        "connector_id": envelope["connector"]["connector_id"],
        "operation": envelope["connector"]["operation"],
        "credential_ref": envelope["connector"]["credential_ref"],
        "action": envelope["action"],
        "resource": envelope["resource"],
        "destination": envelope["destination"],
        "payload": envelope["payload"],
        "idempotency_key": envelope["idempotency"]["key"],
        "envelope_sha256": canonical_sha256(envelope),
    }


def make_receipt(envelope: dict[str, Any], result: ConnectorResult, *, receipt_id: str) -> dict[str, Any]:
    """Classify a connector outcome without claiming more certainty than returned."""
    validate_envelope(envelope)
    if result.status not in {"PREPARED", "EXECUTED", "FAILED", "INDETERMINATE"}:
        raise ExecutionEnvelopeError("unrecognized connector result")

    retry = "NOT_APPLICABLE"
    if result.status == "FAILED":
        retry = "MAY_RETRY_SAME_ENVELOPE" if result.side_effect_absence_confirmed else "VERIFY_BEFORE_RETRY"
    elif result.status == "INDETERMINATE":
        retry = "DO_NOT_RETRY_AUTOMATICALLY"

    receipt: dict[str, Any] = {
        "schema_version": "0.1",
        "receipt_id": receipt_id,
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": canonical_sha256(envelope),
        "attempted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "result": result.status,
        "connector_id": envelope["connector"]["connector_id"],
        "idempotency_key": envelope["idempotency"]["key"],
        "retry_admissibility": retry,
        "platform_result": None,
        "failure": None,
    }
    if result.status == "EXECUTED":
        receipt["platform_result"] = {
            "platform_object_id": result.platform_object_id,
            "platform_url": result.platform_url,
            "confirmation_sha256": hashlib.sha256((result.confirmation or "").encode("utf-8")).hexdigest(),
        }
    elif result.status in {"FAILED", "INDETERMINATE"}:
        receipt["failure"] = {
            "code": result.failure_code,
            "message": result.failure_message,
            "side_effect_absence_confirmed": result.side_effect_absence_confirmed,
        }
    return receipt
