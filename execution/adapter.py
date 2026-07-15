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


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


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
    if not _valid_sha256(decision.get("decision_sha256", "")):
        raise ExecutionEnvelopeError("invalid decision_sha256")

    payload_hash = envelope["payload"].get("content_sha256", "")
    if not _valid_sha256(payload_hash):
        raise ExecutionEnvelopeError("invalid payload.content_sha256")
    if not envelope["idempotency"].get("key"):
        raise ExecutionEnvelopeError("idempotency key required")
    if envelope["idempotency"].get("duplicate_policy") not in {
        "suppress", "verify_before_retry", "never_retry_automatically"
    }:
        raise ExecutionEnvelopeError("unsupported duplicate policy")


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


def assert_request_matches_envelope(envelope: dict[str, Any], request: dict[str, Any]) -> None:
    """Reject connector-side destination, payload, operation, or resource substitution."""
    expected = prepare_connector_request(envelope)
    for field in (
        "connector_id", "operation", "credential_ref", "action", "resource",
        "destination", "payload", "idempotency_key", "envelope_sha256",
    ):
        if request.get(field) != expected[field]:
            raise ExecutionEnvelopeError(f"connector request changed bound field: {field}")


def resolve_duplicate_attempt(
    envelope: dict[str, Any],
    prior_receipts: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return a prior receipt or block unsafe duplicate execution.

    EXECUTED receipts are returned as the authoritative prior result. INDETERMINATE
    receipts block automatic replay. A confirmed FAILED receipt may permit the exact
    same envelope to be retried; it never permits a widened or altered request.
    """
    validate_envelope(envelope)
    envelope_hash = canonical_sha256(envelope)
    matching = [r for r in prior_receipts if r.get("envelope_sha256") == envelope_hash]
    if not matching:
        return None

    latest = matching[-1]
    result = latest.get("result")
    if result == "EXECUTED":
        return latest
    if result == "INDETERMINATE":
        raise ExecutionEnvelopeError("indeterminate prior attempt blocks automatic retry")
    if result == "FAILED" and latest.get("retry_admissibility") != "MAY_RETRY_SAME_ENVELOPE":
        raise ExecutionEnvelopeError("prior failure requires verification before retry")
    if result == "PREPARED":
        raise ExecutionEnvelopeError("prepared attempt already exists without terminal receipt")
    return None


def make_receipt(envelope: dict[str, Any], result: ConnectorResult, *, receipt_id: str) -> dict[str, Any]:
    """Classify a connector outcome without claiming more certainty than returned."""
    validate_envelope(envelope)
    if result.status not in {"PREPARED", "EXECUTED", "FAILED", "INDETERMINATE"}:
        raise ExecutionEnvelopeError("unrecognized connector result")
    if result.status == "EXECUTED" and (not result.platform_object_id or not result.confirmation):
        raise ExecutionEnvelopeError("EXECUTED requires platform identity and confirmation")
    if result.status == "FAILED" and not result.failure_code:
        raise ExecutionEnvelopeError("FAILED requires a failure code")
    if result.status == "INDETERMINATE" and result.side_effect_absence_confirmed:
        raise ExecutionEnvelopeError("INDETERMINATE cannot confirm side-effect absence")

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
        "authority_decision_sha256": envelope["authority_decision"]["decision_sha256"],
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
