"""KnowledgeVault communication-extension host boundary.

KnowledgeVault is the durable continuity/authority host. StegTalk and StegWhisper
remain specialized execution extensions. A handset or edge device may transport or
present communication, but does not become continuity authority by doing so.
"""

from __future__ import annotations

from typing import Any

from .adapter import ExecutionEnvelopeError, canonical_sha256


EXTENSION_TYPES = {"StegTalk", "StegWhisper"}
OPERATIONS = {"SEND_MESSAGE", "RECEIVE_MESSAGE", "PRESENT_AUDIO", "CAPTURE_RESPONSE"}


def validate_communication_extension(request: dict[str, Any]) -> None:
    required = {
        "schema_version", "extension_id", "extension_type", "vault_subject_ref",
        "operation", "destination", "payload_ref", "authority_ref",
        "idempotency_key", "device_role", "receipt_required",
    }
    missing = sorted(required - request.keys())
    if missing:
        raise ExecutionEnvelopeError(f"missing communication-extension fields: {missing}")
    if request["schema_version"] != "0.1":
        raise ExecutionEnvelopeError("communication extension schema_version must be 0.1")
    if request["extension_type"] not in EXTENSION_TYPES:
        raise ExecutionEnvelopeError("unsupported communication extension")
    if request["operation"] not in OPERATIONS:
        raise ExecutionEnvelopeError("unsupported communication operation")
    if request["device_role"] != "EPHEMERAL_TRANSPORT_EDGE":
        raise ExecutionEnvelopeError("device may only act as an ephemeral transport edge")
    if request.get("device_authority", False) is not False:
        raise ExecutionEnvelopeError("device cannot become action authority")
    if request.get("device_continuity_authority", False) is not False:
        raise ExecutionEnvelopeError("device cannot become continuity authority")
    if request.get("vault_continuity_authority", True) is not True:
        raise ExecutionEnvelopeError("KnowledgeVault must remain continuity authority")
    if request["receipt_required"] is not True:
        raise ExecutionEnvelopeError("communication extension operations require receipts")
    if request.get("credential_material") is not None:
        raise ExecutionEnvelopeError("credential material may not be embedded in a vault extension request")
    if not request["authority_ref"] or not request["payload_ref"] or not request["destination"]:
        raise ExecutionEnvelopeError("authority, payload, and destination references are required")


def host_extension_request(request: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable KV-hosted execution record for an extension request."""
    validate_communication_extension(request)
    return {
        "schema_version": "0.1",
        "host": "KnowledgeVault",
        "continuity_authority": "KnowledgeVault",
        "extension_type": request["extension_type"],
        "extension_id": request["extension_id"],
        "operation": request["operation"],
        "vault_subject_ref": request["vault_subject_ref"],
        "destination": request["destination"],
        "payload_ref": request["payload_ref"],
        "payload_sha256": request.get("payload_sha256"),
        "authority_ref": request["authority_ref"],
        "idempotency_key": request["idempotency_key"],
        "device_role": "EPHEMERAL_TRANSPORT_EDGE",
        "device_authority": False,
        "device_continuity_authority": False,
        "receipt_required": True,
        "request_sha256": canonical_sha256(request),
    }


def assert_extension_execution_matches(hosted: dict[str, Any], execution: dict[str, Any]) -> None:
    """Prevent an edge/extension from widening the KV-hosted operation."""
    immutable = (
        "extension_type", "extension_id", "operation", "vault_subject_ref",
        "destination", "payload_ref", "payload_sha256", "authority_ref",
        "idempotency_key", "device_role", "device_authority",
        "device_continuity_authority", "request_sha256",
    )
    for field in immutable:
        if execution.get(field) != hosted.get(field):
            raise ExecutionEnvelopeError(f"extension execution changed KV-bound field: {field}")
