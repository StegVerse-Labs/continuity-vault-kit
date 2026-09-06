import copy
import unittest

from runtime.historical_provenance import (
    HistoricalProvenanceError,
    assert_artifact_record,
    build_artifact_record,
)


class HistoricalProvenanceTests(unittest.TestCase):
    def _record(self, **overrides):
        args = {
            "artifact_id": "stegverse-early-governance-001",
            "exact_bytes": b"historical source bytes",
            "original_filename": "early-governance-notes.md",
            "source_provider": "iCloud",
            "source_storage_class": "owner-controlled-cloud-file",
            "source_locator_ref": "icloud:KnowledgeVault/02_Research/early-governance-notes.md",
            "first_observed_at": "2026-09-05T19:50:00-05:00",
            "source_observed_at": "2024-11-15T10:00:00-06:00",
            "ingested_at": "2026-09-05T19:51:00-05:00",
            "relationship_kind": "ORIGINAL",
            "contradiction_state": "UNKNOWN",
        }
        args.update(overrides)
        return build_artifact_record(**args)

    def test_exact_bytes_are_bound_and_authority_is_false(self):
        record = self._record()
        assert_artifact_record(record, exact_bytes=b"historical source bytes")
        self.assertEqual(record["byte_size"], len(b"historical source bytes"))
        self.assertTrue(record["receipt_id"].endswith(record["exact_sha256"]))
        self.assertTrue(all(value is False for value in record["authority_posture"].values()))

    def test_byte_drift_is_rejected(self):
        record = self._record()
        with self.assertRaises(HistoricalProvenanceError):
            assert_artifact_record(record, exact_bytes=b"modified historical source bytes")

    def test_copy_requires_parent(self):
        with self.assertRaises(HistoricalProvenanceError):
            self._record(relationship_kind="COPY")

    def test_original_rejects_parent(self):
        with self.assertRaises(HistoricalProvenanceError):
            self._record(relationship_kind="ORIGINAL", parent_artifact_refs=["artifact:older"])

    def test_copy_preserves_parent_and_independent_byte_identity(self):
        record = self._record(
            artifact_id="stegverse-early-governance-copy-001",
            relationship_kind="COPY",
            parent_artifact_refs=["stegverse-early-governance-001"],
            source_provider="Google Drive",
            source_locator_ref="gdrive:StegVerse-History/early-governance-notes.md",
        )
        assert_artifact_record(record, exact_bytes=b"historical source bytes")
        self.assertEqual(record["relationship"]["parent_artifact_refs"], ["stegverse-early-governance-001"])

    def test_locator_rejects_reusable_secret_material(self):
        with self.assertRaises(HistoricalProvenanceError):
            self._record(source_locator_ref="https://example.invalid/file?access_token=secret")

    def test_authority_escalation_is_rejected(self):
        record = self._record()
        tampered = copy.deepcopy(record)
        tampered["authority_posture"]["doctrine"] = True
        with self.assertRaises(HistoricalProvenanceError):
            assert_artifact_record(tampered)

    def test_contradiction_state_is_preserved_not_resolved(self):
        record = self._record(contradiction_state="UNRESOLVED", interpretation_refs=["analysis:2026-09-05"])
        self.assertEqual(record["contradiction_state"], "UNRESOLVED")
        self.assertEqual(record["interpretation_refs"], ["analysis:2026-09-05"])


if __name__ == "__main__":
    unittest.main()
