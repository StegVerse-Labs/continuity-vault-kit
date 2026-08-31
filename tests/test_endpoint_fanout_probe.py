from __future__ import annotations

import unittest

from tools.run_endpoint_fanout_probe import run_probe


class EndpointFanoutProbeTests(unittest.TestCase):
    def test_one_probe_becomes_exactly_two_reports(self):
        result = run_probe("alpha-probe-value", probe_id="probe-alpha")
        self.assertTrue(result["pass"])
        self.assertEqual(result["report_count"], 2)
        self.assertEqual(
            set(result["reports"]),
            {"kv_interlock_endpoint_status", "master_records_travel"},
        )

    def test_kv_report_returns_endpoint_status_and_binding(self):
        result = run_probe("alpha-probe-value", probe_id="probe-alpha")
        report = result["reports"]["kv_interlock_endpoint_status"]
        self.assertEqual(report["endpoint_status"], "PASS")
        self.assertEqual(report["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertEqual(report["intr_protocol"], "InTr")
        self.assertEqual(report["receipt_store_count"], 2)
        self.assertFalse(report["canonical_state_changed"])
        self.assertEqual(report["credential_authority"], "TV/TVC")
        self.assertEqual(report["execution_authority"], "NONE")
        returned = report["return_interlock"]
        self.assertEqual(returned["operation"], "COMMIT_CANDIDATE")
        self.assertEqual(returned["decision"], "ALLOW_BOUNDED_CONTEXT")
        self.assertEqual(returned["candidate_type"], "ENDPOINT_STATUS_REPORT")
        self.assertTrue(returned["candidate_only"])
        self.assertFalse(returned["canonical_state_changed"])
        self.assertEqual(returned["authority_effect"], "NONE")
        self.assertTrue(returned["writeback_candidate_ref"].startswith("urn:stegverse:test:kv-candidate:"))
        self.assertTrue(returned["payload_ref"].endswith(report["status_observation_sha256"]))

    def test_master_records_report_records_full_travel(self):
        result = run_probe("alpha-probe-value", probe_id="probe-alpha")
        report = result["reports"]["master_records_travel"]
        self.assertEqual(len(report["hops"]), 5)
        self.assertEqual(
            [hop["boundary"] for hop in report["hops"]],
            [
                "TEST_PROBE_INGRESS",
                "DEVICE->KV",
                "KV_INTERLOCK_RUNTIME",
                "REPORT_FANOUT",
                "MASTER_RECORDS_TEST_CUSTODY",
            ],
        )
        self.assertEqual(
            report["master_records_result"]["custody_status"],
            "TEST_ONLY_RECORDED",
        )
        self.assertFalse(
            report["master_records_result"]["production_custody_claimed"]
        )
        self.assertEqual(report["authority_effect"], "NONE")

    def test_probe_is_non_secret_and_does_not_mutate_canonical_state(self):
        result = run_probe("alpha-probe-value", probe_id="probe-alpha")
        text = str(result).lower()
        self.assertNotIn("password", text)
        self.assertNotIn("private_key", text)
        self.assertFalse(
            result["reports"]["kv_interlock_endpoint_status"]["canonical_state_changed"]
        )
        self.assertFalse(
            result["reports"]["kv_interlock_endpoint_status"]["return_interlock"]["canonical_state_changed"]
        )
        self.assertEqual(result["authority_effect"], "NONE_TEST_ONLY")


if __name__ == "__main__":
    unittest.main()
