import copy
import json
import unittest
from pathlib import Path

from runtime.kv_skap_account_transfer import (
    KVSKAPTransferError,
    build_skap_gate_envelope,
    build_kv_interlock_request,
    build_transfer_packet,
)


FIXTURE = Path(__file__).parent / "fixtures" / "kv_skap_account_metadata_conformance_v1.json"


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
        req = build_kv_interlock_request(packet, request_id="REQ-1", authority_ref="kv://owner-selection/REQ-1")
        self.assertEqual(req["schema_version"], "kv.interlock.request.v1")
        self.assertEqual(req["operation"], "COMMIT_CANDIDATE")
        self.assertEqual(req["disclosure_mode"], "SOURCE_REFERENCE_ONLY")
        self.assertEqual(req["candidate_writeback"]["payload_ref"], packet["payload_sha256"])
        self.assertEqual(req["candidate_writeback"]["requested_destination"], "skap://internal/account-metadata")

    def test_boundary_envelope_binds_exact_request_and_packet(self):
        packet = self.packet()
        req = build_kv_interlock_request(packet, request_id="REQ-2", authority_ref="kv://owner-selection/REQ-2")
        env = build_skap_gate_envelope(packet, req, task_id="SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001")
        self.assertEqual(env["direction"], "KNOWLEDGEVAULT_TO_SKAP_VAULT")
        self.assertFalse(env["canonical_state_changed"])
        self.assertFalse(env["credential_material_transferred"])
        self.assertIsNone(env["gate_receipt_ref"])

    def test_raw_provider_account_id_is_rejected(self):
        packet = self.packet()
        packet["provider_account_id"] = "123456"
        with self.assertRaises(KVSKAPTransferError):
            build_kv_interlock_request(packet, request_id="REQ-3", authority_ref="kv://owner-selection/REQ-3")

    def test_payload_mutation_breaks_binding(self):
        packet = self.packet()
        packet["account_status"] = "INACTIVE"
        with self.assertRaises(KVSKAPTransferError):
            build_kv_interlock_request(packet, request_id="REQ-4", authority_ref="kv://owner-selection/REQ-4")

    def test_request_packet_swap_rejected(self):
        packet = self.packet()
        req = build_kv_interlock_request(packet, request_id="REQ-5", authority_ref="kv://owner-selection/REQ-5")
        other = copy.deepcopy(packet)
        other["owner_selection_ref"] = "kv://selection/other"
        with self.assertRaises(KVSKAPTransferError):
            build_skap_gate_envelope(other, req, task_id="SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001")

    def test_shared_conformance_vector_is_exact_producer_output(self):
        vector = json.loads(FIXTURE.read_text(encoding="utf-8"))
        packet = build_transfer_packet(
            owner_selection_ref="kv://selection/conformance-linkedin-001",
            provider_org_ref="org:linkedin",
            account_class="social",
            account_status="ACTIVE",
            source_evidence_ref="evidence://provider-observation/conformance-linkedin-001",
            source_evidence_sha256="sha256:" + "a" * 64,
        )
        self.assertEqual(packet, vector["packet"])
        request = build_kv_interlock_request(
            packet,
            request_id="KVSKAP-CONFORMANCE-001",
            authority_ref="owner://conformance",
        )
        self.assertEqual(request, vector["kv_interlock_request"])
        envelope = build_skap_gate_envelope(packet, request, task_id="SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001")
        self.assertEqual(envelope, vector["kv_skap_gate_envelope"])

    def test_envelope_requires_task_id_the_receiving_boundary_binds_to(self):
        """TVC binds its retained posture instance to envelope task_id.

        Without it the receiving consumer raises task_id_required, so an
        envelope that omits it cannot reach SKAP at all.
        """
        packet = self.packet()
        request = build_kv_interlock_request(packet, request_id="REQ-1", authority_ref="kv://owner/session")
        for bad in ("", "   "):
            with self.assertRaises(KVSKAPTransferError):
                build_skap_gate_envelope(packet, request, task_id=bad)
        env = build_skap_gate_envelope(packet, request, task_id="  SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001  ")
        self.assertEqual(env["task_id"], "SS-SKAP-AUTHENTIC-ACCOUNT-METADATA-POPULATION-001")



ROOT = Path(__file__).resolve().parents[1]
#: Retired InTr framing of this transfer (KV_SKAP_ACCOUNT_TRANSFER_INTR_ENVELOPE_RESIDUAL, StegVerse-org/.github#167):
#: the SKAP Vault sits inside KV, so the envelope is the in-KV SKAP gate envelope. Built by concatenation so this file
#: does not match itself; evidence/ and reports/ are receipts and are not scanned.
RETIRED_TRANSFER_TOKENS = ("stegverse.intr." + "boundary-transfer", "build_intr_" + "boundary_envelope",
                           "build_intr_" + "request(", "intr_" + "boundary_envelope", "Internal InTr " + "Boundary Transfer")


class InKvSkapGateEnvelopeTests(unittest.TestCase):
    def test_envelope_schema_is_the_in_kv_gate_envelope(self):
        import runtime.kv_skap_account_transfer as t
        schema = json.loads((ROOT / "schemas/intr-boundary-transfer.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema"]["const"], "stegverse.kv-skap-gate.account-transfer-envelope/v1")
        self.assertIn("gate_receipt_ref", schema["required"])
        self.assertFalse(hasattr(t, "build_intr_" + "boundary_envelope") or hasattr(t, "build_intr_" + "request"))

    def test_no_retired_transfer_token_in_the_tree(self):
        skip = {".git", "evidence", "reports", "__pycache__", "node_modules"}
        hits = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or set(path.relative_to(ROOT).parts[:-1]) & skip:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            hits += [f"{path.relative_to(ROOT)}: {tok}" for tok in RETIRED_TRANSFER_TOKENS if tok in text]
        self.assertEqual(hits, [])

if __name__ == "__main__":
    unittest.main()
