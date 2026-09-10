import copy
import unittest

from runtime.kv_skap_account_transfer import (
    KVSKAPTransferError,
    build_intr_boundary_envelope,
    build_intr_request,
    build_transfer_packet,
)


class KVSKAPAccountTransferTests(unittest.TestCase):
    def packet(self):
        return build_transfer_packet(
            owner_selection_ref="kv://selection/abc123",
            provider_org_ref="org:linkedin",
            account_class="social",
            account_status="ACTIVE",
            source_evidence_ref="evidence://provider-observation/sha256-only",
            source_evidence_sha256="sha256:" + "a" * 64,
        )

    def test_builds_nonsecret_owner_selected_packet(self):
        packet = self.packet()
        self.assertFalse(packet["contains_secret_material"])
        self.assertFalse(packet["raw_provider_account_identifier_present"])
        self.assertEqual(packet["destination_boundary"], "SKAP_Vault")
        self.assertEqual(packet["requested_transition"], "SKAP_ACCOUNT_METADATA_ADMIT")

    def test_interlock_request_uses_canonical_candidate_shape(self):
        packet = self.packet()
        req = build_intr_request(packet, request_id="REQ-1", authority_ref="intr://owner-selection/REQ-1")
        self.assertEqual(req["schema_version"], "kv.interlock.request.v1")
        self.assertEqual(req["operation"], "COMMIT_CANDIDATE")
        self.assertEqual(req["disclosure_mode"], "SOURCE_REFERENCE_ONLY")
        self.assertEqual(req["candidate_writeback"]["payload_ref"], packet["payload_sha256"])
        self.assertEqual(req["candidate_writeback"]["requested_destination"], "skap://internal/account-metadata")

    def test_boundary_envelope_binds_exact_request_and_packet(self):
        packet = self.packet()
        req = build_intr_request(packet, request_id="REQ-2", authority_ref="intr://owner-selection/REQ-2")
        env = build_intr_boundary_envelope(packet, req)
        self.assertEqual(env["direction"], "KNOWLEDGEVAULT_TO_SKAP_VAULT")
        self.assertFalse(env["canonical_state_changed"])
        self.assertFalse(env["credential_material_transferred"])
        self.assertIsNone(env["intr_receipt_ref"])

    def test_raw_provider_account_id_is_rejected(self):
        packet = self.packet()
        packet["provider_account_id"] = "123456"
        with self.assertRaises(KVSKAPTransferError):
            build_intr_request(packet, request_id="REQ-3", authority_ref="intr://owner-selection/REQ-3")

    def test_payload_mutation_breaks_binding(self):
        packet = self.packet()
        packet["account_status"] = "INACTIVE"
        with self.assertRaises(KVSKAPTransferError):
            build_intr_request(packet, request_id="REQ-4", authority_ref="intr://owner-selection/REQ-4")

    def test_request_packet_swap_rejected(self):
        packet = self.packet()
        req = build_intr_request(packet, request_id="REQ-5", authority_ref="intr://owner-selection/REQ-5")
        other = copy.deepcopy(packet)
        other["owner_selection_ref"] = "kv://selection/other"
        with self.assertRaises(KVSKAPTransferError):
            build_intr_boundary_envelope(other, req)


if __name__ == "__main__":
    unittest.main()
