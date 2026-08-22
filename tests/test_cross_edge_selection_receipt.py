import tempfile
import unittest

from execution.vault_store import KnowledgeVaultExecutionStore


class CrossEdgeSelectionReceiptTests(unittest.TestCase):
    def test_selection_receipt_round_trips_through_receipt_stream(self):
        receipt = {
            "schema_version":"0.1",
            "receipt_type":"CROSS_EDGE_SELECTION",
            "attempt_id":"attempt:1",
            "policy_version":"stegtalk.cross-edge.v0.1",
            "posture":"AUTO",
            "recipient_state":"KNOWN",
            "candidate_set_sha256":"a"*64,
            "selected_edge_id":"gateway",
            "selected_bearer":"stegtalk-ip",
            "primary_score":12.5,
            "primary_score_components":{"security":1.9},
            "fallback_order":[{"edge_id":"phone","score":7.0,"bearer":"sms"}],
            "excluded_paths":[],
            "selected_advertisement_sha256":"b"*64,
            "decided_at":"2026-08-22T22:00:00Z",
            "multipath_authorized":False,
            "remote_edge_execution_authorized":True,
            "selection_sha256":"c"*64,
        }
        with tempfile.TemporaryDirectory() as root:
            store = KnowledgeVaultExecutionStore(root)
            path = store.append_receipt("attempt-1-selection", receipt)
            self.assertTrue(path.exists())
            self.assertEqual(store.read_stream("Receipts", "attempt-1-selection"), [receipt])

    def test_multiple_selection_receipts_preserve_order_for_reconstruction(self):
        with tempfile.TemporaryDirectory() as root:
            store = KnowledgeVaultExecutionStore(root)
            first={"receipt_type":"CROSS_EDGE_SELECTION","attempt_id":"a","selection_sha256":"1"*64}
            second={"receipt_type":"CROSS_EDGE_SELECTION","attempt_id":"a","selection_sha256":"2"*64}
            store.append_receipt("attempt-a-selection", first)
            store.append_receipt("attempt-a-selection", second)
            self.assertEqual(store.read_stream("Receipts", "attempt-a-selection"), [first, second])


if __name__ == "__main__": unittest.main()
