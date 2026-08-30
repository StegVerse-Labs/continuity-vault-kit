"""Prepare governed KnowledgeVault evidence for Publisher document rendering.

This module is deliberately transport- and renderer-neutral. It validates the
owner-authorized disclosure boundary, produces a hash-bound Publisher bundle,
and emits a deterministic preparation receipt. It does not publish, render,
transmit, or grant execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


REQUEST_SCHEMA = "stegverse.kv.document-export-request/v1"
BUNDLE_SCHEMA = "stegverse.kv.publisher-document-export/v1"
RECEIPT_SCHEMA = "stegverse.kv.document-export-preparation-receipt/v1"
REVOCATION_SCHEMA = "stegverse.kv.document-export-revocation-receipt/v1"
PUBLISHER_DESTINATION = "GCAT-BCAT-Engine/Publisher"
SOURCE_REPOSITORY = "StegVerse-Labs/continuity-vault-kit"
FORMATS = {"markdown", "html", "pdf", "docx", "json"}
CONTENT_CLASSES = {"RAW_SOURCE_EXCERPT", "OWNER_AUTHORED", "AI_DERIVED"}
FIDELITY = {"exact", "semantic_reconstruction", "inference", "integrity_only", "unavailable"}
RETENTION = {"integrity_only", "reconstructable", "full_fidelity"}
PROHIBITED_PREFIXES = (
    "03_Records/",
    "_Policy/",
    "_System/SKAP/",
    "_System/Secrets/",
    "_Vault/Secrets/",
)


class DocumentExportError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_uri(value: Any) -> str:
    return "sha256:" + sha256_hex(value)


def _is_sha256_uri(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value[7:])
    )


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise DocumentExportError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise DocumentExportError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _unique_nonempty_strings(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise DocumentExportError(f"{field} must be a non-empty list")
    if any(not isinstance(item, str) or not item for item in value):
        raise DocumentExportError(f"{field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise DocumentExportError(f"{field} must be unique")
    return value


def _validate_authority(request: dict[str, Any], now: datetime) -> None:
    auth = request.get("authorization")
    if not isinstance(auth, dict):
        raise DocumentExportError("authorization required")
    if auth.get("status") != "active" or auth.get("revoked") is not False:
        raise DocumentExportError("authorization is not active")
    if auth.get("revocable") is not True:
        raise DocumentExportError("authorization must remain revocable")
    if auth.get("destination") != PUBLISHER_DESTINATION:
        raise DocumentExportError("destination mismatch")
    if auth.get("authority_source") not in {"direct_instruction", "active_standing_delegation"}:
        raise DocumentExportError("authority source invalid")
    for field in ("authority_ref", "purpose"):
        if not isinstance(auth.get(field), str) or not auth[field]:
            raise DocumentExportError(f"authorization {field} required")
    _unique_nonempty_strings(auth.get("scope"), "authorization scope")
    allowed = set(_unique_nonempty_strings(auth.get("allowed_formats"), "allowed formats"))
    requested = set(_unique_nonempty_strings(request.get("requested_formats"), "requested formats"))
    if not allowed.issubset(FORMATS) or not requested.issubset(FORMATS):
        raise DocumentExportError("unsupported format")
    if not requested.issubset(allowed):
        raise DocumentExportError("requested format exceeds authorization")
    expires_at = auth.get("expires_at")
    if expires_at is not None and _parse_time(expires_at) <= now:
        raise DocumentExportError("authorization expired")


def _validate_evidence(request: dict[str, Any]) -> set[str]:
    evidence = request.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise DocumentExportError("evidence required")
    subjects: set[str] = set()
    for index, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise DocumentExportError(f"evidence[{index}] must be an object")
        subject = item.get("subject_id")
        if not isinstance(subject, str) or not subject or subject in subjects:
            raise DocumentExportError(f"evidence[{index}] subject invalid or duplicate")
        subjects.add(subject)
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise DocumentExportError(f"evidence[{index}] path required")
        if any(path.startswith(prefix) for prefix in PROHIBITED_PREFIXES):
            raise DocumentExportError(f"evidence[{index}] path prohibited")
        if item.get("restricted") is not False or item.get("contains_credentials") is not False:
            raise DocumentExportError(f"evidence[{index}] restricted content prohibited")
        fidelity = item.get("fidelity")
        retention = item.get("retention_class")
        if fidelity not in FIDELITY or retention not in RETENTION:
            raise DocumentExportError(f"evidence[{index}] fidelity or retention invalid")
        if item.get("superseded") is not False:
            raise DocumentExportError(f"evidence[{index}] superseded evidence prohibited")
        if fidelity == "exact" and item.get("payload_available") is not True:
            raise DocumentExportError(f"evidence[{index}] exact payload unavailable")
        if fidelity in {"integrity_only", "unavailable"} and item.get("payload_available") is True:
            raise DocumentExportError(f"evidence[{index}] payload availability contradiction")
        if item.get("derived_index") is not False:
            raise DocumentExportError(f"evidence[{index}] derived index is not canonical")
        if not _is_sha256_uri(item.get("content_hash")):
            raise DocumentExportError(f"evidence[{index}] content hash invalid")
    return subjects


def _validate_document(request: dict[str, Any], evidence_subjects: set[str]) -> None:
    document = request.get("document")
    if not isinstance(document, dict):
        raise DocumentExportError("document required")
    for field in ("document_id", "document_type", "title", "template_profile"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise DocumentExportError(f"document {field} required")
    document_id = document["document_id"]
    if len(document_id) > 128 or not document_id[0].isalnum() or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in document_id
    ):
        raise DocumentExportError("document id is not filesystem-safe")
    authors = document.get("authors")
    if not isinstance(authors, list) or not authors:
        raise DocumentExportError("document authors required")
    if any(not isinstance(author, dict) or not isinstance(author.get("name"), str) or not author["name"] for author in authors):
        raise DocumentExportError("document author invalid")
    sections = document.get("sections")
    if not isinstance(sections, list) or not sections:
        raise DocumentExportError("document sections required")
    section_ids: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise DocumentExportError(f"section[{index}] invalid")
        section_id = section.get("section_id")
        if not isinstance(section_id, str) or not section_id or section_id in section_ids:
            raise DocumentExportError(f"section[{index}] id invalid or duplicate")
        section_ids.add(section_id)
        for field in ("heading", "body", "content_class", "fidelity"):
            if not isinstance(section.get(field), str) or not section[field]:
                raise DocumentExportError(f"section[{index}] {field} required")
        refs = _unique_nonempty_strings(
            section.get("source_subject_ids"),
            f"section[{index}] source_subject_ids",
            allow_empty=section.get("content_class") == "OWNER_AUTHORED",
        )
        if not set(refs).issubset(evidence_subjects):
            raise DocumentExportError(f"section[{index}] source provenance missing")
        content_class = section.get("content_class")
        fidelity = section.get("fidelity")
        if content_class not in CONTENT_CLASSES or fidelity not in {"exact", "semantic_reconstruction", "inference"}:
            raise DocumentExportError(f"section[{index}] content class or fidelity invalid")
        if content_class != "OWNER_AUTHORED" and not refs:
            raise DocumentExportError(f"section[{index}] source provenance missing")
        if content_class == "AI_DERIVED" and fidelity == "exact":
            raise DocumentExportError(f"section[{index}] AI-derived content cannot claim exact fidelity")
        if content_class == "RAW_SOURCE_EXCERPT" and fidelity != "exact":
            raise DocumentExportError(f"section[{index}] raw excerpt must retain exact fidelity")
        confidence = section.get("confidence")
        if content_class == "AI_DERIVED" and not isinstance(confidence, (int, float)):
            raise DocumentExportError(f"section[{index}] AI-derived confidence required")
        if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
            raise DocumentExportError(f"section[{index}] confidence invalid")


def prepare_document_export(request: dict[str, Any], *, now: datetime | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate and prepare a bounded Publisher bundle and preparation receipt."""
    if not isinstance(request, dict) or request.get("schema_version") != REQUEST_SCHEMA:
        raise DocumentExportError("request schema mismatch")
    export_id = request.get("export_id")
    if not isinstance(export_id, str) or len(export_id) < 3 or len(export_id) > 128 or not export_id[0].isalnum() or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in export_id
    ):
        raise DocumentExportError("export id invalid")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    _parse_time(request.get("created_at"))
    source = request.get("source")
    if not isinstance(source, dict) or source.get("repository") != SOURCE_REPOSITORY:
        raise DocumentExportError("source repository mismatch")
    if not isinstance(source.get("release"), str) or not source["release"].startswith("v"):
        raise DocumentExportError("source release invalid")
    if not _is_sha256_uri(source.get("verification_root")):
        raise DocumentExportError("verification root invalid")
    _unique_nonempty_strings(source.get("event_ids"), "source event ids")
    _validate_authority(request, now)
    evidence_subjects = _validate_evidence(request)
    _validate_document(request, evidence_subjects)
    redaction = request.get("redaction")
    if (
        not isinstance(redaction, dict)
        or redaction.get("review_state") != "OWNER_APPROVED"
        or redaction.get("restricted_content_present") is not False
    ):
        raise DocumentExportError("owner-approved redaction required")

    auth = request["authorization"]
    bundle = {
        "schema_version": BUNDLE_SCHEMA,
        "export_id": request["export_id"],
        "created_at": request["created_at"],
        "source": copy.deepcopy(source),
        "authorization": {
            "authority_source": auth["authority_source"],
            "authority_ref": auth["authority_ref"],
            "status": auth["status"],
            "scope": copy.deepcopy(auth["scope"]),
            "purpose": auth["purpose"],
            "destination": auth["destination"],
            "receipt_id": auth["authority_ref"],
            "allowed_formats": copy.deepcopy(auth["allowed_formats"]),
            "expires_at": auth.get("expires_at"),
            "revocable": True,
            "revoked": False,
        },
        "document": copy.deepcopy(request["document"]),
        "evidence": copy.deepcopy(request["evidence"]),
        "redaction": copy.deepcopy(redaction),
        "requested_formats": copy.deepcopy(request["requested_formats"]),
        "authority_effect": "NONE",
        "publication_authorized": False,
        "release_authorized": False,
        "execution_authorized": False,
    }
    bundle["export_sha256"] = sha256_uri(bundle)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "receipt_type": "vault.document_export_prepared",
        "export_id": request["export_id"],
        "request_sha256": sha256_uri(request),
        "export_sha256": bundle["export_sha256"],
        "authority_ref": auth["authority_ref"],
        "destination": PUBLISHER_DESTINATION,
        "requested_formats": copy.deepcopy(request["requested_formats"]),
        "result": "PREPARED_NOT_TRANSMITTED",
        "prepared_at": request["created_at"],
        "authority_effect": "NONE",
        "publication_authorized": False,
        "release_authorized": False,
        "execution_authorized": False,
    }
    receipt["receipt_sha256"] = sha256_uri(receipt)
    return bundle, receipt


def revoke_document_export(*, export_id: str, export_sha256: str, authority_ref: str, revoked_at: str, reason: str) -> dict[str, Any]:
    """Create a deterministic revocation receipt; transport remains separate."""
    if not all(isinstance(value, str) and value for value in (export_id, authority_ref, reason)):
        raise DocumentExportError("revocation fields required")
    if not _is_sha256_uri(export_sha256):
        raise DocumentExportError("export hash invalid")
    _parse_time(revoked_at)
    receipt = {
        "schema_version": REVOCATION_SCHEMA,
        "receipt_type": "vault.document_export_revoked",
        "export_id": export_id,
        "export_sha256": export_sha256,
        "authority_ref": authority_ref,
        "revoked_at": revoked_at,
        "reason": reason,
        "result": "REVOKED",
        "authority_effect": "REVOKE_EXPORT_AUTHORITY_ONLY",
        "artifact_deletion_authorized": False,
        "publication_retraction_authorized": False,
    }
    receipt["receipt_sha256"] = sha256_uri(receipt)
    return receipt
