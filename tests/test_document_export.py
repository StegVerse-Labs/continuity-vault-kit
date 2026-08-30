from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "runtime" / "document_export.py"
FIXTURE = ROOT / "fixtures" / "document-export" / "admitted.json"


def load_module():
    spec = importlib.util.spec_from_file_location("document_export", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class DocumentExportTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.request = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.now = datetime(2026, 8, 29, 8, 30, tzinfo=timezone.utc)

    def prepare(self, request=None):
        return self.m.prepare_document_export(request or self.request, now=self.now)

    def test_prepares_hash_bound_publisher_bundle_and_receipt(self):
        bundle, receipt = self.prepare()
        self.assertEqual(bundle["schema_version"], self.m.BUNDLE_SCHEMA)
        self.assertEqual(bundle["authorization"]["destination"], self.m.PUBLISHER_DESTINATION)
        self.assertEqual(bundle["export_sha256"], receipt["export_sha256"])
        unhashed = copy.deepcopy(bundle)
        unhashed.pop("export_sha256")
        self.assertEqual(bundle["export_sha256"], self.m.sha256_uri(unhashed))
        self.assertEqual(receipt["result"], "PREPARED_NOT_TRANSMITTED")
        self.assertFalse(receipt["publication_authorized"])
        self.assertEqual(receipt["authority_effect"], "NONE")

    def test_preparation_is_deterministic(self):
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first, second)

    def test_requested_format_cannot_exceed_owner_authorization(self):
        request = copy.deepcopy(self.request)
        request["authorization"]["allowed_formats"] = ["markdown"]
        with self.assertRaisesRegex(self.m.DocumentExportError, "exceeds authorization"):
            self.prepare(request)

    def test_restricted_and_policy_paths_fail_closed(self):
        for path in ("03_Records/medical.md", "_Policy/Data_Sharing_Policy.md", "_System/SKAP/session.json"):
            with self.subTest(path=path):
                request = copy.deepcopy(self.request)
                request["evidence"][0]["path"] = path
                with self.assertRaisesRegex(self.m.DocumentExportError, "path prohibited"):
                    self.prepare(request)

    def test_ai_derived_section_cannot_claim_exact_fidelity(self):
        request = copy.deepcopy(self.request)
        request["document"]["sections"][1]["fidelity"] = "exact"
        with self.assertRaisesRegex(self.m.DocumentExportError, "cannot claim exact"):
            self.prepare(request)

    def test_missing_section_provenance_fails_closed(self):
        request = copy.deepcopy(self.request)
        request["document"]["sections"][0]["source_subject_ids"] = ["unknown-evidence"]
        with self.assertRaisesRegex(self.m.DocumentExportError, "source provenance missing"):
            self.prepare(request)

    def test_unknown_content_class_and_unsafe_id_fail_closed(self):
        unknown = copy.deepcopy(self.request)
        unknown["document"]["sections"][0]["content_class"] = "MODEL_TRUTH"
        with self.assertRaisesRegex(self.m.DocumentExportError, "content class"):
            self.prepare(unknown)
        unsafe = copy.deepcopy(self.request)
        unsafe["document"]["document_id"] = "../outside"
        with self.assertRaisesRegex(self.m.DocumentExportError, "filesystem-safe"):
            self.prepare(unsafe)

    def test_revoked_or_expired_authority_fails_closed(self):
        revoked = copy.deepcopy(self.request)
        revoked["authorization"]["revoked"] = True
        with self.assertRaisesRegex(self.m.DocumentExportError, "not active"):
            self.prepare(revoked)
        expired = copy.deepcopy(self.request)
        expired["authorization"]["expires_at"] = "2026-08-29T08:29:59Z"
        with self.assertRaisesRegex(self.m.DocumentExportError, "expired"):
            self.prepare(expired)

    def test_revocation_receipt_is_bounded_and_deterministic(self):
        bundle, _ = self.prepare()
        first = self.m.revoke_document_export(
            export_id=bundle["export_id"],
            export_sha256=bundle["export_sha256"],
            authority_ref=bundle["authorization"]["authority_ref"],
            revoked_at="2026-08-29T09:00:00Z",
            reason="Owner withdrew document export authority.",
        )
        second = self.m.revoke_document_export(
            export_id=bundle["export_id"],
            export_sha256=bundle["export_sha256"],
            authority_ref=bundle["authorization"]["authority_ref"],
            revoked_at="2026-08-29T09:00:00Z",
            reason="Owner withdrew document export authority.",
        )
        self.assertEqual(first, second)
        self.assertEqual(first["result"], "REVOKED")
        self.assertFalse(first["artifact_deletion_authorized"])
        self.assertFalse(first["publication_retraction_authorized"])


if __name__ == "__main__":
    unittest.main()
