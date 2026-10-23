"""KV gateway storage adapter interface: fail-closed null binding, content addressing, no plaintext, and external
storage records never crossing into KV (StegVerse-org/.github#160 comments 6372045430 and 6372216673)."""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from runtime import kv_gateway_storage as gw  # noqa: E402
from kv_gateway_e0 import E0MemoryGateway, E0Opener, e0_seal  # noqa: E402

SIX = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint",
       "owning_existing_goal", "next_attempt")


class GatewayStorageInterface(unittest.TestCase):
    def assertSix(self, out, code):
        self.assertEqual((out["disposition"], out["failure_code"]), ("FAIL_CLOSED", code), out)
        for f in SIX:
            self.assertTrue(isinstance(out[f], str) and out[f].strip(), f)
        self.assertFalse(out["ledger_written"])

    def test_interface_method_names_exactly(self):
        names = [n for n, _ in inspect.getmembers(gw.GatewayStorageAdapter, inspect.isfunction)]
        self.assertEqual(sorted(names), ["advance_head", "get", "get_head", "list", "put"])
        self.assertEqual(list(inspect.signature(gw.GatewayStorageAdapter.put).parameters), ["self", "location", "blob"])
        self.assertEqual(list(inspect.signature(gw.GatewayStorageAdapter.get).parameters),
                         ["self", "location", "blob_sha256"])
        self.assertEqual(list(inspect.signature(gw.GatewayStorageAdapter.advance_head).parameters),
                         ["self", "location", "expected_previous", "new"])

    def test_null_adapter_fails_closed_svkv_not_provisioned(self):
        store = gw.GatewayStore(gw.NullGatewayStorageAdapter())
        blob = e0_seal(b'{"x": 1}')
        for value, out in (store.put_blob("01_KV_Ledger", blob), store.get_blob("01_KV_Ledger", "a" * 64),
                           store.list_blobs("01_KV_Ledger"), store.head("01_KV_Ledger")):
            self.assertIsNone(value)
            self.assertSix(out, "SVKV_GATEWAY_STORAGE_NOT_PROVISIONED")
            self.assertEqual(out["failure_class"], "B")
            self.assertIn("ECOSYSTEM-OWN-KV-001", out["owning_existing_goal"])
            self.assertIn("provisioned", out["next_attempt"])
        self.assertSix(store.advance("01_KV_Ledger", None, "a" * 64)[1], "SVKV_GATEWAY_STORAGE_NOT_PROVISIONED")

    def test_null_opener_fails_closed_key_not_custodied(self):
        with self.assertRaises(gw.GatewayStorageRefused) as ctx:
            gw.NullBlobOpener().open(e0_seal(b"{}"))
        self.assertSix(ctx.exception.refusal, "KV_LEDGER_BLOB_KEY_NOT_CUSTODIED")
        self.assertIn("TV/TVC", ctx.exception.refusal["required_evidence_or_repair"])

    def test_content_addressed_round_trip_and_append_only_head(self):
        mem = E0MemoryGateway()
        store = gw.GatewayStore(mem)
        a, failed = store.put_blob("01_KV_Ledger", e0_seal(b'{"n": 1}'))
        self.assertIsNone(failed)
        self.assertEqual(a, gw.blob_sha256(mem.blobs["01_KV_Ledger"][a]))
        blob, failed = store.get_blob("01_KV_Ledger", a)
        self.assertIsNone(failed)
        self.assertEqual(E0Opener().open(blob), b'{"n": 1}')
        self.assertEqual(store.list_blobs("01_KV_Ledger"), ([a], None))
        self.assertEqual(store.head("01_KV_Ledger"), (None, None))
        self.assertEqual(store.advance("01_KV_Ledger", None, a), (True, None))
        b, _ = store.put_blob("01_KV_Ledger", e0_seal(b'{"n": 2}'))
        self.assertEqual(store.advance("01_KV_Ledger", None, b)[1]["failure_code"], "KV_HEAD_POINTER_NOT_APPEND_ONLY")
        self.assertEqual(store.advance("01_KV_Ledger", a, "c" * 64)[1]["failure_code"],
                         "KV_HEAD_POINTER_NOT_APPEND_ONLY")
        self.assertEqual(store.advance("01_KV_Ledger", a, b), (True, None))
        self.assertEqual(store.head("01_KV_Ledger"), (b, None))

    def test_no_plaintext_and_location_names(self):
        store = gw.GatewayStore(E0MemoryGateway())
        for plain in (b'{"receipt": "plaintext"}', gw.SEALED_MAGIC + b'{"wrapped": "plaintext"}', gw.SEALED_MAGIC):
            self.assertSix(store.put_blob("01_KV_Ledger", plain)[1], "KV_GATEWAY_BLOB_NOT_SEALED")
        for bad in ("KV_Ledger", "1_KV", "01_", "../01_KV_Ledger", "_StegVerse-org/01_KV_Ledger"):
            self.assertSix(store.put_blob(bad, e0_seal(b"{}"))[1], "KV_STORAGE_LOCATION_INVALID")

    def test_external_storage_records_never_cross(self):
        """The gateway rule: an external endpoint's records (Drive file ids, owners, revisions, modified times,
        sharing) are refused as KV input; only sealed bytes and their sha256 addresses cross."""
        mem = E0MemoryGateway()
        store = gw.GatewayStore(mem)
        a, _ = store.put_blob("01_KV_Ledger", e0_seal(b'{"n": 1}'))
        drive_listing = [{"id": "1AbCdriveFileId", "name": a, "mimeType": "application/octet-stream",
                          "modifiedTime": "2026-10-23T18:00:00Z", "owners": [{"emailAddress": "x@example.invalid"}],
                          "headRevisionId": "0B-rev"}]
        mem.list = lambda location: drive_listing
        self.assertSix(store.list_blobs("01_KV_Ledger")[1], "EXTERNAL_STORAGE_RECORD_REFUSED")
        mem.list = lambda location: [a, {"revisions": ["r1"]}]
        self.assertSix(store.list_blobs("01_KV_Ledger")[1], "EXTERNAL_STORAGE_RECORD_REFUSED")
        mem.get = lambda location, address: {"id": "1AbC", "content": "..."}
        self.assertSix(store.get_blob("01_KV_Ledger", a)[1], "EXTERNAL_STORAGE_RECORD_REFUSED")
        mem.get = lambda location, address: e0_seal(b'{"swapped": true}')
        self.assertSix(store.get_blob("01_KV_Ledger", a)[1], "EXTERNAL_STORAGE_RECORD_REFUSED")
        mem.get_head = lambda location: {"id": "1AbC", "headRevisionId": "0B-rev"}
        self.assertSix(store.head("01_KV_Ledger")[1], "EXTERNAL_STORAGE_RECORD_REFUSED")
        self.assertSix(gw.GatewayStore({"files": drive_listing}).list_blobs("01_KV_Ledger")[1],
                       "EXTERNAL_STORAGE_RECORD_REFUSED")

    def test_adapter_exceptions_are_never_allow(self):
        mem = E0MemoryGateway()
        self.assertSix(gw.GatewayStore(mem).get_blob("01_KV_Ledger", "d" * 64)[1], "KV_GATEWAY_STORAGE_UNREADABLE")

    def test_stdlib_only(self):
        source = (ROOT / "runtime" / "kv_gateway_storage.py").read_text(encoding="utf-8")
        self.assertNotIn("import cryptography", source)
        self.assertNotIn("from cryptography", source)
        for mod in ("googleapiclient", "google.oauth2", "requests", "boto3"):
            self.assertNotIn(mod, source)


if __name__ == "__main__":
    unittest.main()
