"""Deterministic, provider-neutral historical provenance helpers for KnowledgeVault."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable

SCHEMA_VERSION = "stegverse.kv.historical-artifact-record/v1"
RELATIONSHIP_KINDS = {"ORIGINAL", "COPY", "MIRROR", "DERIVED", "UNKNOWN"}
CONTRADICTION_STATES = {"NONE", "UNRESOLVED", "CONFLICTING_SOURCE", "UNKNOWN"}
FORBIDDEN_LOCATOR_FRAGMENTS = (
    "access_token=",
    "refresh_token=",
    "password=",
    "api_key=",
    "secret=",
    "private_key=",
)


class HistoricalProvenanceError(ValueError):
    pass


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalProvenanceError(f"{name} is required")
    return value.strip()


def _clean_refs(values: Iterable[str] | None, name: str) -> list[str]:
    result: list[str] = []
    for value in values or []:
        ref = _required_text(value, name)
        if ref not in result:
            result.append(ref)
    return result


def _validate_locator(locator_ref: str) -> str:
    locator = _required_text(locator_ref, "source_locator_ref")
    lowered = locator.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_LOCATOR_FRAGMENTS):
        raise HistoricalProvenanceError("source locator may not contain reusable credential material")
    return locator


def build_artifact_record(
    *,
    artifact_id: str,
    exact_bytes: bytes,
    original_filename: str,
    source_provider: str,
    source_storage_class: str,
    source_locator_ref: str,
    first_observed_at: str,
    ingested_at: str,
    relationship_kind: str = "UNKNOWN",
    parent_artifact_refs: Iterable[str] | None = None,
    media_type: str | None = None,
    source_observed_at: str | None = None,
    interpretation_refs: Iterable[str] | None = None,
    contradiction_state: str = "UNKNOWN",
) -> Dict[str, Any]:
    """Build a source-only historical record from exact caller-supplied bytes.

    This function performs no provider access, network access, migration, or publication.
    """
    if not isinstance(exact_bytes, (bytes, bytearray)):
        raise HistoricalProvenanceError("exact_bytes must be bytes")

    relationship_kind = _required_text(relationship_kind, "relationship_kind").upper()
    if relationship_kind not in RELATIONSHIP_KINDS:
        raise HistoricalProvenanceError("unsupported relationship kind")

    parents = _clean_refs(parent_artifact_refs, "parent_artifact_ref")
    if relationship_kind == "ORIGINAL" and parents:
        raise HistoricalProvenanceError("ORIGINAL artifacts may not claim parent artifact refs")
    if relationship_kind in {"COPY", "MIRROR", "DERIVED"} and not parents:
        raise HistoricalProvenanceError(f"{relationship_kind} requires at least one parent artifact ref")

    contradiction_state = _required_text(contradiction_state, "contradiction_state").upper()
    if contradiction_state not in CONTRADICTION_STATES:
        raise HistoricalProvenanceError("unsupported contradiction state")

    artifact_id = _required_text(artifact_id, "artifact_id")
    digest = hashlib.sha256(bytes(exact_bytes)).hexdigest()

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "exact_sha256": digest,
        "byte_size": len(exact_bytes),
        "original_filename": _required_text(original_filename, "original_filename"),
        "media_type": media_type.strip() if isinstance(media_type, str) and media_type.strip() else None,
        "source": {
            "provider": _required_text(source_provider, "source_provider"),
            "storage_class": _required_text(source_storage_class, "source_storage_class"),
            "locator_ref": _validate_locator(source_locator_ref),
            "first_observed_at": _required_text(first_observed_at, "first_observed_at"),
            "source_observed_at": source_observed_at.strip() if isinstance(source_observed_at, str) and source_observed_at.strip() else None,
        },
        "relationship": {
            "kind": relationship_kind,
            "parent_artifact_refs": parents,
        },
        "ingested_at": _required_text(ingested_at, "ingested_at"),
        "interpretation_refs": _clean_refs(interpretation_refs, "interpretation_ref"),
        "contradiction_state": contradiction_state,
        "authority_posture": {
            "execution": False,
            "governance": False,
            "publication": False,
            "doctrine": False,
            "provider_write": False,
            "migration": False,
        },
        "receipt_id": f"kvhist:{artifact_id}:{digest}",
    }


def assert_artifact_record(record: Dict[str, Any], *, exact_bytes: bytes | None = None) -> None:
    if not isinstance(record, dict):
        raise HistoricalProvenanceError("record must be an object")
    if record.get("schema_version") != SCHEMA_VERSION:
        raise HistoricalProvenanceError("record schema mismatch")

    _required_text(record.get("artifact_id"), "artifact_id")
    digest = record.get("exact_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise HistoricalProvenanceError("exact_sha256 must be lowercase SHA-256 hex")
    if exact_bytes is not None and hashlib.sha256(bytes(exact_bytes)).hexdigest() != digest:
        raise HistoricalProvenanceError("exact bytes do not match recorded SHA-256")

    source = record.get("source")
    if not isinstance(source, dict):
        raise HistoricalProvenanceError("source object required")
    _required_text(source.get("provider"), "source.provider")
    _required_text(source.get("storage_class"), "source.storage_class")
    _validate_locator(source.get("locator_ref"))
    _required_text(source.get("first_observed_at"), "source.first_observed_at")

    relationship = record.get("relationship")
    if not isinstance(relationship, dict):
        raise HistoricalProvenanceError("relationship object required")
    kind = _required_text(relationship.get("kind"), "relationship.kind").upper()
    if kind not in RELATIONSHIP_KINDS:
        raise HistoricalProvenanceError("unsupported relationship kind")
    parents = _clean_refs(relationship.get("parent_artifact_refs"), "parent_artifact_ref")
    if kind == "ORIGINAL" and parents:
        raise HistoricalProvenanceError("ORIGINAL artifacts may not claim parents")
    if kind in {"COPY", "MIRROR", "DERIVED"} and not parents:
        raise HistoricalProvenanceError(f"{kind} requires a parent artifact ref")

    posture = record.get("authority_posture")
    required_false = {"execution", "governance", "publication", "doctrine", "provider_write", "migration"}
    if not isinstance(posture, dict) or any(posture.get(key) is not False for key in required_false):
        raise HistoricalProvenanceError("historical artifact record may not grant authority")

    expected_receipt = f"kvhist:{record['artifact_id']}:{digest}"
    if record.get("receipt_id") != expected_receipt:
        raise HistoricalProvenanceError("receipt identity mismatch")
