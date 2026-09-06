#!/usr/bin/env python3
"""Dependency-light source validator for historical-corpus import semantics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.historical_provenance import build_artifact_record
from runtime.historical_corpus_import import (
    HistoricalCorpusImportError,
    assert_import_receipt,
    assert_master_records_custody_request,
    assert_site_status_projection,
    build_import_receipt,
    build_master_records_custody_request,
    build_site_status_projection,
)

HANDOFF = ROOT / "KV_HISTORICAL_CORPUS_IMPORT_MIRROR_HANDOFF.md"
README = ROOT / "README.md"
SCHEMAS = {
    "https://stegverse.org/schemas/kv-historical-import-receipt.schema.json": ROOT / "schemas/kv-historical-import-receipt.schema.json",
    "https://stegverse.org/schemas/kv-historical-custody-request.schema.json": ROOT / "schemas/kv-historical-custody-request.schema.json",
    "https://stegverse.org/schemas/kv-historical-status-projection.schema.json": ROOT / "schemas/kv-historical-status-projection.schema.json",
}


def main() -> int:
    for expected_id, path in SCHEMAS.items():
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("$id") != expected_id:
            raise SystemExit(f"schema id mismatch: {path.name}")

    handoff = HANDOFF.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    for invariant in (
        "import_receipt != truth_certification",
        "custody_request != destination_custody_acceptance",
        "site_status_projection != private_content",
        "source_merge != live_provider_observation",
    ):
        if invariant not in handoff:
            raise SystemExit(f"handoff invariant missing: {invariant}")
    if "Owner-authorized historical imports and custody" not in readme:
        raise SystemExit("README historical import/custody section missing")

    payload = b"historical-corpus-import-validation-vector"
    artifact = build_artifact_record(
        artifact_id="validation-artifact-001",
        exact_bytes=payload,
        original_filename="validation.bin",
        source_provider="owner-controlled-storage",
        source_storage_class="historical-evidence",
        source_locator_ref="provider:validation/historical.bin",
        first_observed_at="2026-09-05T22:00:00-05:00",
        ingested_at="2026-09-05T22:01:00-05:00",
        relationship_kind="ORIGINAL",
        contradiction_state="UNRESOLVED",
    )
    receipt = build_import_receipt(
        artifact_record=artifact,
        exact_bytes=payload,
        owner_authorization_ref="owner-auth:synthetic-validation-only",
        direct_source_receipt_ref="direct-source:synthetic-validation-only",
        intr_admission_receipt_ref="intr:synthetic-validation-only",
        persistence_receipt_ref="kv:synthetic-validation-only",
        imported_at="2026-09-05T22:02:00-05:00",
    )
    assert_import_receipt(receipt, artifact_record=artifact)

    custody = build_master_records_custody_request(
        import_receipt=receipt,
        requested_at="2026-09-05T22:03:00-05:00",
    )
    assert_master_records_custody_request(custody)
    if custody["destination_custody_accepted"] or custody["destination_acknowledgement_minted"]:
        raise SystemExit("source validator may not mint Master Records destination state")

    projection = build_site_status_projection(import_receipt=receipt, custody_request=custody)
    assert_site_status_projection(projection)
    if projection["private_content_included"]:
        raise SystemExit("bounded Site projection contains private content")

    try:
        build_import_receipt(
            artifact_record=artifact,
            exact_bytes=b"tampered",
            owner_authorization_ref="owner-auth:synthetic-validation-only",
            intr_admission_receipt_ref="intr:synthetic-validation-only",
            persistence_receipt_ref="kv:synthetic-validation-only",
            imported_at="2026-09-05T22:02:00-05:00",
        )
    except HistoricalCorpusImportError:
        pass
    else:
        raise SystemExit("exact-byte drift negative control failed")

    print("KV historical corpus import source validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
