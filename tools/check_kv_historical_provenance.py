#!/usr/bin/env python3
"""Dependency-light source validator for KV historical provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.historical_provenance import HistoricalProvenanceError, assert_artifact_record, build_artifact_record

SCHEMA = ROOT / "schemas" / "kv-historical-artifact-record.schema.json"
HANDOFF = ROOT / "KV_HISTORICAL_PROVENANCE_MIRROR_HANDOFF.md"
README = ROOT / "README.md"


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if schema.get("$id") != "https://stegverse.org/schemas/kv-historical-artifact-record.schema.json":
        raise SystemExit("historical provenance schema id mismatch")

    handoff = HANDOFF.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    for required in (
        "storage_location != authority",
        "copy != original",
        "historical_evidence != current_doctrine",
        "import_receipt != truth_certification",
    ):
        if required not in handoff:
            raise SystemExit(f"handoff invariant missing: {required}")
    if "Historical provenance across storage providers" not in readme:
        raise SystemExit("README historical provenance section missing")

    payload = b"historical-source-validation-vector"
    record = build_artifact_record(
        artifact_id="validation-vector-001",
        exact_bytes=payload,
        original_filename="validation-vector.bin",
        source_provider="owner-controlled-storage",
        source_storage_class="historical-evidence",
        source_locator_ref="provider:historical/validation-vector.bin",
        first_observed_at="2026-09-05T19:55:00-05:00",
        ingested_at="2026-09-05T19:55:01-05:00",
        relationship_kind="ORIGINAL",
        contradiction_state="UNKNOWN",
    )
    assert_artifact_record(record, exact_bytes=payload)

    try:
        assert_artifact_record(record, exact_bytes=b"tampered")
    except HistoricalProvenanceError:
        pass
    else:
        raise SystemExit("byte-drift negative control failed")

    if any(record["authority_posture"].values()):
        raise SystemExit("authority posture must remain false")

    print("KV historical provenance source validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
