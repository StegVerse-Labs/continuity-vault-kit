from __future__ import annotations

import hashlib
import json
import os
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SkapResolutionError(RuntimeError):
    pass


class SkapCryptoVault:
    """In-memory cryptographic SKAP proof runtime.

    The wrapping key and plaintext exist only inside this process. Metadata and grants are
    secret-free. This implementation is suitable for synthetic runtime proof and contract
    integration; it deliberately does not claim production key custody.
    """

    def __init__(self, wrapping_key: bytes | None = None) -> None:
        key = wrapping_key or AESGCM.generate_key(bit_length=256)
        if len(key) != 32:
            raise ValueError("SKAP wrapping key must be 256 bits")
        self._aead = AESGCM(key)
        self._records: dict[str, dict[str, Any]] = {}
        self._sealed: dict[str, bytes] = {}
        self._grants: dict[str, dict[str, Any]] = {}

    def _aad(self, record: dict[str, Any]) -> bytes:
        return canonical_bytes({
            "object_id": record["object_id"],
            "secret_class": record["secret_class"],
            "provider": record.get("provider"),
            "credential_version": record["credential_version"],
            "allowed_purposes": record.get("allowed_purposes", []),
            "allowed_endpoint_refs": record.get("allowed_endpoint_refs", []),
        })

    def _rehash(self, record: dict[str, Any]) -> dict[str, Any]:
        body = {k: v for k, v in record.items() if k != "object_hash"}
        record["object_hash"] = sha256_uri(canonical_bytes(body))
        return record

    def seal(
        self,
        plaintext: bytes,
        *,
        object_id: str,
        secret_class: str = "API_CREDENTIAL",
        provider: str | None = None,
        account_ref: str | None = None,
        credential_version: int = 1,
        allowed_purposes: list[str] | None = None,
        allowed_endpoint_refs: list[str] | None = None,
        supersedes_object_hash: str | None = None,
    ) -> dict[str, Any]:
        if not object_id.startswith("skap://"):
            raise ValueError("object_id must use skap://")
        if not plaintext:
            raise ValueError("plaintext must be non-empty")
        if object_id in self._records:
            raise ValueError("object_id already exists")

        record: dict[str, Any] = {
            "schema": "stegverse.skap.sealed_object/v1",
            "object_id": object_id,
            "secret_class": secret_class,
            "provider": provider,
            "account_ref": account_ref,
            "lifecycle_state": "SEALED",
            "credential_version": credential_version,
            "supersedes_object_hash": supersedes_object_hash,
            "sealed_material_ref": f"skap-memory://{hashlib.sha256(object_id.encode()).hexdigest()[:24]}",
            "sealed_material_hash": "",
            "wrapping_policy_ref": "tvc://skap/aes-256-gcm/synthetic-runtime-v1",
            "allowed_purposes": list(allowed_purposes or []),
            "allowed_endpoint_refs": list(allowed_endpoint_refs or []),
            "plaintext_persisted": False,
            "kv_decryption_authority": False,
            "device_secret_custody_authority": False,
            "model_secret_access": False,
            "created_at": now_iso(),
            "activated_at": None,
            "rotated_at": None,
            "revoked_at": None,
            "recovery_only_at": None,
        }
        nonce = secrets.token_bytes(12)
        ciphertext = self._aead.encrypt(nonce, plaintext, self._aad(record))
        sealed_blob = nonce + ciphertext
        record["sealed_material_hash"] = sha256_uri(sealed_blob)
        self._records[object_id] = self._rehash(record)
        self._sealed[object_id] = sealed_blob
        return deepcopy(self._records[object_id])

    def activate(self, object_id: str) -> dict[str, Any]:
        record = self._require_record(object_id)
        if record["lifecycle_state"] != "SEALED":
            raise SkapResolutionError("only SEALED object may activate")
        record["lifecycle_state"] = "ACTIVE"
        record["activated_at"] = now_iso()
        return deepcopy(self._rehash(record))

    def issue_grant(self, object_id: str, *, purpose: str, endpoint_ref: str) -> dict[str, Any]:
        record = self._require_record(object_id)
        if record["lifecycle_state"] != "ACTIVE":
            raise SkapResolutionError("NO_NEW_GRANTS")
        if purpose not in record.get("allowed_purposes", []):
            raise SkapResolutionError("purpose_not_authorized")
        if endpoint_ref not in record.get("allowed_endpoint_refs", []):
            raise SkapResolutionError("endpoint_not_authorized")
        grant_id = "skap-grant-" + secrets.token_hex(12)
        body = {
            "schema": "stegverse.skap.synthetic_grant/v1",
            "grant_id": grant_id,
            "secret_ref": object_id,
            "sealed_object_hash": record["object_hash"],
            "credential_version": record["credential_version"],
            "purpose": purpose,
            "endpoint_ref": endpoint_ref,
            "status": "ACTIVE",
            "issued_at": now_iso(),
            "authority_ref": "TVC",
            "secret_plaintext_present": False,
            "authority_transfer": False,
        }
        body["grant_hash"] = sha256_uri(canonical_bytes(body))
        self._grants[grant_id] = body
        return deepcopy(body)

    def resolve_transient(
        self,
        grant: dict[str, Any],
        *,
        endpoint_ref: str,
        endpoint_session_verified: bool,
        revocation_rechecked_immediately_before_resolution: bool,
    ) -> bytes:
        stored = self._grants.get(str(grant.get("grant_id")))
        if not stored or stored.get("grant_hash") != grant.get("grant_hash"):
            raise SkapResolutionError("grant_mismatch")
        record = self._require_record(stored["secret_ref"])
        if stored["status"] != "ACTIVE":
            raise SkapResolutionError("grant_revoked")
        if record["lifecycle_state"] != "ACTIVE":
            raise SkapResolutionError("credential_not_active")
        if record["object_hash"] != stored["sealed_object_hash"]:
            raise SkapResolutionError("sealed_object_changed")
        if endpoint_ref != stored["endpoint_ref"]:
            raise SkapResolutionError("endpoint_mismatch")
        if not endpoint_session_verified:
            raise SkapResolutionError("endpoint_session_not_verified")
        if not revocation_rechecked_immediately_before_resolution:
            raise SkapResolutionError("revocation_not_rechecked")
        sealed = self._sealed[record["object_id"]]
        if sha256_uri(sealed) != record["sealed_material_hash"]:
            raise SkapResolutionError("sealed_material_integrity_failed")
        nonce, ciphertext = sealed[:12], sealed[12:]
        return self._aead.decrypt(nonce, ciphertext, self._aad(record))

    def rotate(self, object_id: str, *, replacement_object_id: str, new_plaintext: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
        old = self._require_record(object_id)
        if old["lifecycle_state"] != "ACTIVE":
            raise SkapResolutionError("rotation_requires_active_object")
        old_hash = old["object_hash"]
        old["lifecycle_state"] = "ROTATED"
        old["rotated_at"] = now_iso()
        self._rehash(old)
        self._invalidate_grants(object_id)
        replacement = self.seal(
            new_plaintext,
            object_id=replacement_object_id,
            secret_class=old["secret_class"],
            provider=old.get("provider"),
            account_ref=old.get("account_ref"),
            credential_version=int(old["credential_version"]) + 1,
            allowed_purposes=list(old.get("allowed_purposes", [])),
            allowed_endpoint_refs=list(old.get("allowed_endpoint_refs", [])),
            supersedes_object_hash=old_hash,
        )
        return deepcopy(old), replacement

    def revoke(self, object_id: str) -> dict[str, Any]:
        record = self._require_record(object_id)
        if record["lifecycle_state"] not in {"ACTIVE", "SEALED"}:
            raise SkapResolutionError("credential_not_revokeable")
        record["lifecycle_state"] = "REVOKED"
        record["revoked_at"] = now_iso()
        self._invalidate_grants(object_id)
        return deepcopy(self._rehash(record))

    def _invalidate_grants(self, object_id: str) -> None:
        for grant in self._grants.values():
            if grant["secret_ref"] == object_id and grant["status"] == "ACTIVE":
                grant["status"] = "INVALIDATED"
                grant["invalidated_at"] = now_iso()
                body = {k: v for k, v in grant.items() if k != "grant_hash"}
                grant["grant_hash"] = sha256_uri(canonical_bytes(body))

    def _require_record(self, object_id: str) -> dict[str, Any]:
        try:
            return self._records[object_id]
        except KeyError as exc:
            raise SkapResolutionError("unknown_secret_ref") from exc

    def metadata(self, object_id: str) -> dict[str, Any]:
        return deepcopy(self._require_record(object_id))

    def export_non_secret_state(self) -> dict[str, Any]:
        return {
            "records": [deepcopy(v) for v in self._records.values()],
            "grants": [deepcopy(v) for v in self._grants.values()],
            "plaintext_persisted": False,
            "wrapping_key_exported": False,
            "sealed_blob_exported": False,
        }
