from __future__ import annotations

import copy
import unittest

from runtime.historical_provenance import build_artifact_record
from runtime.historical_corpus_import import (
    LEGACY_ORGANIZATION_RECORD_REQUEST_SCHEMA,
    LEGACY_RECORD_REQUESTED_FIELD,
    LEGACY_REQUEST_AUTHORITY_EFFECT,
    HistoricalCorpusImportError,
    assert_import_receipt,
    assert_master_records_organization_record_request,
    assert_site_status_projection,
    build_import_receipt,
    build_master_records_organization_record_request,
    build_site_status_projection,
)


class HistoricalCorpusImportTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"exact historical artifact bytes\n"
        self.artifact = build_artifact_record(
            artifact_id="artifact-001",
            exact_bytes=self.payload,
            original_filename="artifact.txt",
            source_provider="owner-controlled-storage",
            source_storage_class="historical-evidence",
            source_locator_ref="provider:history/artifact.txt",
            first_observed_at="2026-05-20T12:00:00-05:00",
            ingested_at="2026-09-05T22:00:00-05:00",
            relationship_kind="ORIGINAL",
            contradiction_state="UNRESOLVED",
        )
        self.receipt = build_import_receipt(
            artifact_record=self.artifact,
            exact_bytes=self.payload,
            owner_authorization_ref="owner-auth:receipt-001",
            direct_source_receipt_ref="kv-direct-source:receipt-001",
            intr_admission_receipt_ref="intr:admission-001",
            persistence_receipt_ref="kv:persistence-001",
            imported_at="2026-09-05T22:01:00-05:00",
        )

    def test_import_receipt_binds_artifact_and_preserves_non_authority(self):
        assert_import_receipt(self.receipt, artifact_record=self.artifact)
        self.assertEqual(self.receipt["contradiction_state"], "UNRESOLVED")
        self.assertFalse(self.receipt["truth_certified"])
        self.assertTrue(all(value is False for value in self.receipt["authority_posture"].values()))

    def test_byte_drift_fails_closed(self):
        with self.assertRaises(HistoricalCorpusImportError):
            build_import_receipt(
                artifact_record=self.artifact,
                exact_bytes=b"changed bytes",
                owner_authorization_ref="owner-auth:receipt-001",
                intr_admission_receipt_ref="intr:admission-001",
                persistence_receipt_ref="kv:persistence-001",
                imported_at="2026-09-05T22:01:00-05:00",
            )

    def test_missing_or_secret_bearing_owner_authorization_fails_closed(self):
        for ref in ("", "owner-auth:?access_token=abc"):
            with self.assertRaises(HistoricalCorpusImportError):
                build_import_receipt(
                    artifact_record=self.artifact,
                    exact_bytes=self.payload,
                    owner_authorization_ref=ref,
                    intr_admission_receipt_ref="intr:admission-001",
                    persistence_receipt_ref="kv:persistence-001",
                    imported_at="2026-09-05T22:01:00-05:00",
                )

    def test_import_receipt_hash_and_authority_tamper_fail(self):
        tampered = copy.deepcopy(self.receipt)
        tampered["authority_posture"]["publication"] = True
        with self.assertRaises(HistoricalCorpusImportError):
            assert_import_receipt(tampered)

        tampered = copy.deepcopy(self.receipt)
        tampered["contradiction_state"] = "NONE"
        with self.assertRaises(HistoricalCorpusImportError):
            assert_import_receipt(tampered)

    def test_organization_record_request_cannot_mint_destination_acceptance(self):
        request = build_master_records_organization_record_request(
            import_receipt=self.receipt,
            requested_at="2026-09-05T22:02:00-05:00",
        )
        assert_master_records_organization_record_request(request)
        self.assertEqual(request["schema_version"], "stegverse.kv.historical-organization-record-request/v1")
        self.assertTrue(request["record_requested"])
        self.assertNotIn("custody_requested", request)
        self.assertEqual(request["authority_effect"], "NONE_ORGANIZATION_RECORD_REQUEST_ONLY")
        self.assertFalse(request["destination_custody_accepted"])
        self.assertFalse(request["destination_acknowledgement_minted"])

        tampered = copy.deepcopy(request)
        tampered["destination_custody_accepted"] = True
        with self.assertRaises(HistoricalCorpusImportError):
            assert_master_records_organization_record_request(tampered)

    def test_reader_accepts_legacy_custody_request_names(self):
        request = build_master_records_organization_record_request(
            import_receipt=self.receipt,
            requested_at="2026-09-05T22:02:00-05:00",
        )
        legacy = copy.deepcopy(request)
        legacy["schema_version"] = LEGACY_ORGANIZATION_RECORD_REQUEST_SCHEMA
        legacy[LEGACY_RECORD_REQUESTED_FIELD] = legacy.pop("record_requested")
        legacy["authority_effect"] = LEGACY_REQUEST_AUTHORITY_EFFECT
        self.assertEqual(LEGACY_ORGANIZATION_RECORD_REQUEST_SCHEMA, "stegverse.kv.historical-custody-request/v1")
        self.assertEqual(LEGACY_RECORD_REQUESTED_FIELD, "custody_requested")
        self.assertEqual(LEGACY_REQUEST_AUTHORITY_EFFECT, "NONE_CUSTODY_REQUEST_ONLY")
        assert_master_records_organization_record_request(legacy)
        projection = build_site_status_projection(import_receipt=self.receipt, record_request=legacy)
        self.assertTrue(projection["record_requested"])
        self.assertNotIn("custody_requested", projection)

        legacy[LEGACY_RECORD_REQUESTED_FIELD] = False
        with self.assertRaises(HistoricalCorpusImportError):
            assert_master_records_organization_record_request(legacy)

    def test_site_projection_is_bounded_and_non_authorizing(self):
        request = build_master_records_organization_record_request(
            import_receipt=self.receipt,
            requested_at="2026-09-05T22:02:00-05:00",
        )
        projection = build_site_status_projection(import_receipt=self.receipt, record_request=request)
        assert_site_status_projection(projection)
        self.assertTrue(projection["record_requested"])
        self.assertFalse(projection["private_content_included"])
        self.assertFalse(projection["publication_authority_granted"])
        self.assertNotIn("source", projection)
        self.assertNotIn("bytes", projection)

    def test_site_projection_rejects_mismatched_organization_record_request(self):
        request = build_master_records_organization_record_request(
            import_receipt=self.receipt,
            requested_at="2026-09-05T22:02:00-05:00",
        )
        request["import_receipt_id"] = "other"
        with self.assertRaises(HistoricalCorpusImportError):
            build_site_status_projection(import_receipt=self.receipt, record_request=request)


if __name__ == "__main__":
    unittest.main()
