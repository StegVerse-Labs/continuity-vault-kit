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
    "provider_account_id", "raw_provider_account_identifier"
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
                if lower == "raw_provider_account_identifier_present" and child is False:
                    continue
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
    _assert_no_secrets(packet)
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
        "scope": ["provider_org_ref", "account_class", "account_status", "source_evidence_ref", "source_evidence_sha256"],
        "disclosure_mode": "OPAQUE_REFERENCE_AND_HASH_ONLY",
        "authority_ref": authority_ref,
        "candidate": validated,
        "destination": {"boundary": "SKAP_Vault", "operation": "SKAP_ACCOUNT_METADATA_ADMIT"},
    }
