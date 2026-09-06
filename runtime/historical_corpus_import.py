"""Deterministic historical-corpus import, custody-request, and bounded status helpers.

This module performs no provider access, network access, Master Records write, Site
publication, or vault migration. It validates caller-supplied evidence references
and exact bytes against the canonical historical provenance record.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from runtime.historical_provenance import assert_artifact_record

IMPORT_SCHEMA = "stegverse.kv.historical-import-receipt/v1"
CUSTODY_SCHEMA = "stegverse.kv.historical-custody-request/v1"
STATUS_SCHEMA = "stegverse.kv.historical-status-projection/v1"

FORBIDDEN_REF_FRAGMENTS = (
    "access_token=",
    "refresh_token=",
    "password=",
    "api_key=",
    "secret=",
    "private_key=",
    "bearer ",
)


class HistoricalCorpusImportError(ValueError):
    pass


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalCorpusImportError(f"{name} is required")
    text = value.strip()
    lowered = text.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_REF_FRAGMENTS):
        raise HistoricalCorpusImportError(f"{name} may not contain reusable credential material")
    return text


def _canonical_sha256(value: Dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_import_receipt(
    *,
    artifact_record: Dict[str, Any],
    exact_bytes: bytes,
    owner_authorization_ref: str,
    intr_admission_receipt_ref: str,
    persistence_receipt_ref: str,
    imported_at: str,
    direct_source_receipt_ref: str | None = None,
) -> Dict[str, Any]:
    """Build a receipt for an already-admitted/persisted historical import event.

    The caller must supply the real authorization/admission/persistence evidence at
    runtime. Source validation uses synthetic references only and does not establish
    a live import.
    """
    if not isinstance(exact_bytes, (bytes, bytearray)):
        raise HistoricalCorpusImportError("exact_bytes must be bytes")
    try:
        assert_artifact_record(artifact_record, exact_bytes=bytes(exact_bytes))
    except Exception as exc:  # preserve the provenance validator as canonical
        raise HistoricalCorpusImportError(str(exc)) from exc

    auth_ref = _required_text(owner_authorization_ref, "owner_authorization_ref")
    intr_ref = _required_text(intr_admission_receipt_ref, "intr_admission_receipt_ref")
    persist_ref = _required_text(persistence_receipt_ref, "persistence_receipt_ref")
    imported_at = _required_text(imported_at, "imported_at")
    source_ref = None if direct_source_receipt_ref is None else _required_text(
        direct_source_receipt_ref, "direct_source_receipt_ref"
    )

    core = {
        "schema_version": IMPORT_SCHEMA,
        "artifact_id": artifact_record["artifact_id"],
        "artifact_sha256": artifact_record["exact_sha256"],
        "artifact_receipt_id": artifact_record["receipt_id"],
        "relationship_kind": artifact_record["relationship"]["kind"],
        "contradiction_state": artifact_record["contradiction_state"],
        "owner_authorization_ref": auth_ref,
        "direct_source_receipt_ref": source_ref,
        "intr_admission_receipt_ref": intr_ref,
        "persistence_receipt_ref": persist_ref,
        "imported_at": imported_at,
        "state": "ADMITTED_PERSISTED",
        "truth_certified": False,
        "private_content_included": False,
        "authority_posture": {
            "execution": False,
            "governance": False,
            "publication": False,
            "doctrine": False,
            "provider_write": False,
            "migration": False,
            "master_records_destination": False,
        },
    }
    digest = _canonical_sha256(core)
    return {**core, "receipt_sha256": digest, "receipt_id": f"kvhistimport:{artifact_record['artifact_id']}:{digest}"}


def assert_import_receipt(
    receipt: Dict[str, Any], *, artifact_record: Dict[str, Any] | None = None
) -> None:
    if not isinstance(receipt, dict) or receipt.get("schema_version") != IMPORT_SCHEMA:
        raise HistoricalCorpusImportError("import receipt schema mismatch")
    if receipt.get("state") != "ADMITTED_PERSISTED":
        raise HistoricalCorpusImportError("historical import receipt must be admitted and persisted")
    for key in (
        "artifact_id",
        "artifact_sha256",
        "artifact_receipt_id",
        "owner_authorization_ref",
        "intr_admission_receipt_ref",
        "persistence_receipt_ref",
        "imported_at",
    ):
        _required_text(receipt.get(key), key)
    if receipt.get("direct_source_receipt_ref") is not None:
        _required_text(receipt.get("direct_source_receipt_ref"), "direct_source_receipt_ref")
    if receipt.get("truth_certified") is not False or receipt.get("private_content_included") is not False:
        raise HistoricalCorpusImportError("import receipt may not certify truth or contain private content")
    posture = receipt.get("authority_posture")
    required_false = {
        "execution",
        "governance",
        "publication",
        "doctrine",
        "provider_write",
        "migration",
        "master_records_destination",
    }
    if not isinstance(posture, dict) or any(posture.get(key) is not False for key in required_false):
        raise HistoricalCorpusImportError("import receipt may not grant authority")

    core = dict(receipt)
    receipt_id = core.pop("receipt_id", None)
    digest = core.pop("receipt_sha256", None)
    expected = _canonical_sha256(core)
    if digest != expected or receipt_id != f"kvhistimport:{receipt['artifact_id']}:{expected}":
        raise HistoricalCorpusImportError("import receipt canonical hash mismatch")

    if artifact_record is not None:
        try:
            assert_artifact_record(artifact_record)
        except Exception as exc:
            raise HistoricalCorpusImportError(str(exc)) from exc
        if receipt["artifact_id"] != artifact_record["artifact_id"]:
            raise HistoricalCorpusImportError("artifact id mismatch")
        if receipt["artifact_sha256"] != artifact_record["exact_sha256"]:
            raise HistoricalCorpusImportError("artifact hash mismatch")
        if receipt["artifact_receipt_id"] != artifact_record["receipt_id"]:
            raise HistoricalCorpusImportError("artifact receipt mismatch")
        if receipt.get("relationship_kind") != artifact_record["relationship"]["kind"]:
            raise HistoricalCorpusImportError("relationship kind mismatch")
        if receipt.get("contradiction_state") != artifact_record["contradiction_state"]:
            raise HistoricalCorpusImportError("contradiction state mismatch")


def build_master_records_custody_request(*, import_receipt: Dict[str, Any], requested_at: str) -> Dict[str, Any]:
    assert_import_receipt(import_receipt)
    requested_at = _required_text(requested_at, "requested_at")
    return {
        "schema_version": CUSTODY_SCHEMA,
        "source_repository": "StegVerse-Labs/continuity-vault-kit",
        "artifact_id": import_receipt["artifact_id"],
        "artifact_sha256": import_receipt["artifact_sha256"],
        "import_receipt_id": import_receipt["receipt_id"],
        "import_receipt_sha256": import_receipt["receipt_sha256"],
        "requested_at": requested_at,
        "custody_requested": True,
        "destination_repository": "master-records/core-lite",
        "destination_custody_accepted": False,
        "destination_acknowledgement_minted": False,
        "independent_validation_complete": False,
        "runtime_activation": False,
        "execution_authority_granted": False,
        "continuity_receipt_minted": False,
        "publication_authority_granted": False,
        "authority_effect": "NONE_CUSTODY_REQUEST_ONLY",
    }


def assert_master_records_custody_request(request: Dict[str, Any]) -> None:
    if not isinstance(request, dict) or request.get("schema_version") != CUSTODY_SCHEMA:
        raise HistoricalCorpusImportError("custody request schema mismatch")
    if request.get("source_repository") != "StegVerse-Labs/continuity-vault-kit":
        raise HistoricalCorpusImportError("custody source repository mismatch")
    if request.get("destination_repository") != "master-records/core-lite":
        raise HistoricalCorpusImportError("custody destination repository mismatch")
    if request.get("custody_requested") is not True:
        raise HistoricalCorpusImportError("custody request must declare custody_requested=true")
    for key in (
        "destination_custody_accepted",
        "destination_acknowledgement_minted",
        "independent_validation_complete",
        "runtime_activation",
        "execution_authority_granted",
        "continuity_receipt_minted",
        "publication_authority_granted",
    ):
        if request.get(key) is not False:
            raise HistoricalCorpusImportError(f"custody request may not assert {key}")
    if request.get("authority_effect") != "NONE_CUSTODY_REQUEST_ONLY":
        raise HistoricalCorpusImportError("custody request authority effect mismatch")
    for key in ("artifact_id", "artifact_sha256", "import_receipt_id", "import_receipt_sha256", "requested_at"):
        _required_text(request.get(key), key)


def build_site_status_projection(
    *, import_receipt: Dict[str, Any], custody_request: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    assert_import_receipt(import_receipt)
    if custody_request is not None:
        assert_master_records_custody_request(custody_request)
        if custody_request["import_receipt_id"] != import_receipt["receipt_id"]:
            raise HistoricalCorpusImportError("custody request/import receipt mismatch")
    return {
        "schema_version": STATUS_SCHEMA,
        "artifact_id": import_receipt["artifact_id"],
        "artifact_sha256": import_receipt["artifact_sha256"],
        "import_receipt_id": import_receipt["receipt_id"],
        "import_state": import_receipt["state"],
        "relationship_kind": import_receipt["relationship_kind"],
        "contradiction_state": import_receipt["contradiction_state"],
        "custody_requested": bool(custody_request and custody_request["custody_requested"]),
        "destination_custody_accepted": False,
        "destination_acknowledgement_minted": False,
        "private_content_included": False,
        "publication_authority_granted": False,
        "authority_effect": "NONE_STATUS_ONLY",
    }


def assert_site_status_projection(projection: Dict[str, Any]) -> None:
    if not isinstance(projection, dict) or projection.get("schema_version") != STATUS_SCHEMA:
        raise HistoricalCorpusImportError("status projection schema mismatch")
    for key in ("artifact_id", "artifact_sha256", "import_receipt_id", "import_state"):
        _required_text(projection.get(key), key)
    if projection.get("private_content_included") is not False:
        raise HistoricalCorpusImportError("status projection may not include private content")
    if projection.get("publication_authority_granted") is not False:
        raise HistoricalCorpusImportError("status projection may not grant publication authority")
    if projection.get("destination_custody_accepted") is not False:
        raise HistoricalCorpusImportError("source status may not assert Master Records acceptance")
    if projection.get("destination_acknowledgement_minted") is not False:
        raise HistoricalCorpusImportError("source status may not assert Master Records acknowledgement")
    if projection.get("authority_effect") != "NONE_STATUS_ONLY":
        raise HistoricalCorpusImportError("status projection authority effect mismatch")
