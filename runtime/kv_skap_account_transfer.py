from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


class KVSKAPTransferError(ValueError):
    pass


SECRET_TOKENS = (
    "password", "secret", "token", "private_key", "access_key", "refresh_token",
    "client_secret", "authorization", "cookie", "session_key", "account_id",
    "provider_account_id"
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_uri(value: Any) -> str:
    raw = value if isinstance(value, str) else canonical_json(value)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _assert_no_secrets(value: Any, path: str = "packet") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lower = str(key).lower()
            if any(token in lower for token in SECRET_TOKENS):
                raise KVSKAPTransferError(f"secret_or_raw_identifier_field_prohibited:{path}.{key}")
            _assert_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _assert_no_secrets(child, f"{path}[{idx}]")


def build_transfer_packet(*, owner_selection_ref: str, provider_org_ref: str,
                          account_class: str, account_status: str,
                          source_evidence_ref: str, source_evidence_sha256: str) -> dict[str, Any]:
    payload = {
        "owner_selection_ref": owner_selection_ref,
        "provider_org_ref": provider_org_ref,
        "account_class": account_class,
        "account_status": account_status,
        "source_evidence_ref": source_evidence_ref,
        "source_evidence_sha256": source_evidence_sha256,
    }
    _assert_no_secrets(payload)
    payload_hash = sha256_uri(payload)
    transfer_id = "kvskap_" + hashlib.sha256((owner_selection_ref + "\n" + payload_hash).encode("utf-8")).hexdigest()[:24]
    packet = {
        "schema": "stegverse.kv-skap.account-metadata-transfer/v1",
        "transfer_id": transfer_id,
        "direction": "KNOWLEDGEVAULT_TO_SKAP_VAULT",
        "source_boundary": "KnowledgeVault",
        "destination_boundary": "SKAP_Vault",
        **payload,
        "payload_sha256": payload_hash,
        "contains_secret_material": False,
        "raw_provider_account_identifier_present": False,
        "requested_transition": "SKAP_ACCOUNT_METADATA_ADMIT",
    }
    validate_transfer_packet(packet)
    return packet


def validate_transfer_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise KVSKAPTransferError("packet_not_object")
    _assert_no_secrets({k: v for k, v in packet.items() if k != "raw_provider_account_identifier_present"})
    required = {
        "schema": "stegverse.kv-skap.account-metadata-transfer/v1",
        "direction": "KNOWLEDGEVAULT_TO_SKAP_VAULT",
        "source_boundary": "KnowledgeVault",
        "destination_boundary": "SKAP_Vault",
        "contains_secret_material": False,
        "raw_provider_account_identifier_present": False,
        "requested_transition": "SKAP_ACCOUNT_METADATA_ADMIT",
    }
    for key, expected in required.items():
        if packet.get(key) != expected:
            raise KVSKAPTransferError(f"invalid_{key}")
    if packet.get("account_class") not in {"social", "financial", "identity", "email", "cloud", "other"}:
        raise KVSKAPTransferError("invalid_account_class")
    if packet.get("account_status") not in {"ACTIVE", "INACTIVE", "CLOSED", "UNKNOWN"}:
        raise KVSKAPTransferError("invalid_account_status")
    evidence_hash = str(packet.get("source_evidence_sha256") or "")
    if not evidence_hash.startswith("sha256:") or len(evidence_hash) != 71:
        raise KVSKAPTransferError("invalid_source_evidence_sha256")
    projection = {
        "owner_selection_ref": packet.get("owner_selection_ref"),
        "provider_org_ref": packet.get("provider_org_ref"),
        "account_class": packet.get("account_class"),
        "account_status": packet.get("account_status"),
        "source_evidence_ref": packet.get("source_evidence_ref"),
        "source_evidence_sha256": evidence_hash,
    }
    if packet.get("payload_sha256") != sha256_uri(projection):
        raise KVSKAPTransferError("payload_hash_mismatch")
    expected_transfer_id = "kvskap_" + hashlib.sha256((str(packet.get("owner_selection_ref")) + "\n" + str(packet.get("payload_sha256"))).encode("utf-8")).hexdigest()[:24]
    if packet.get("transfer_id") != expected_transfer_id:
        raise KVSKAPTransferError("transfer_id_mismatch")
    return deepcopy(packet)


def build_intr_request(packet: dict[str, Any], *, request_id: str, authority_ref: str) -> dict[str, Any]:
    validated = validate_transfer_packet(packet)
    return {
        "schema_version": "kv.interlock.request.v1",
        "operation": "COMMIT_CANDIDATE",
        "request_id": request_id,
        "requester": {"module": "KnowledgeVault", "component": "SKAPAccountMetadataTransfer"},
        "purpose": "Transfer owner-selected non-secret account metadata from KnowledgeVault to the internal SKAP Vault boundary.",
        "record_class": "SKAP_ACCOUNT_METADATA_TRANSFER",
        "requested_scope": ["provider_org_ref", "account_class", "account_status", "source_evidence_ref", "source_evidence_sha256"],
        "minimum_necessary_justification": "Only provider class/status and evidence references are required to establish an internal SKAP account binding without exporting provider identifiers or secrets.",
        "authority_ref": authority_ref,
        "disclosure_mode": "SOURCE_REFERENCE_ONLY",
        "candidate_writeback": {
            "candidate_type": "SKAP_ACCOUNT_METADATA_TRANSFER",
            "payload_ref": validated["payload_sha256"],
            "requested_destination": "skap://internal/account-metadata"
        }
    }


def build_intr_boundary_envelope(packet: dict[str, Any], request: dict[str, Any], *, intr_receipt_ref: str | None = None) -> dict[str, Any]:
    validated = validate_transfer_packet(packet)
    if request.get("schema_version") != "kv.interlock.request.v1" or request.get("operation") != "COMMIT_CANDIDATE":
        raise KVSKAPTransferError("invalid_kv_interlock_request")
    if request.get("candidate_writeback", {}).get("payload_ref") != validated["payload_sha256"]:
        raise KVSKAPTransferError("request_packet_binding_mismatch")
    envelope = {
        "schema": "stegverse.intr.boundary-transfer/v1",
        "direction": "KNOWLEDGEVAULT_TO_SKAP_VAULT",
        "source_boundary": "KnowledgeVault",
        "destination_boundary": "SKAP_Vault",
        "request_id": request["request_id"],
        "request_sha256": sha256_uri(request),
        "transfer_id": validated["transfer_id"],
        "transfer_packet_sha256": sha256_uri(validated),
        "payload_sha256": validated["payload_sha256"],
        "intr_receipt_ref": intr_receipt_ref,
        "canonical_state_changed": False,
        "credential_material_transferred": False,
    }
    return envelope
