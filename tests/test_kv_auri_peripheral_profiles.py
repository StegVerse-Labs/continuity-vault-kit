"""Source-only regression fixtures; never authentic receipts or device tests."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "auri_profiles", ROOT / "scripts/validate_kv_auri_peripheral_profiles.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceContractTests(unittest.TestCase):
    def test_source_contract_and_existing_owner_bindings(self):
        result = module.validate_source_contract()
        self.assertEqual(result["state"], "SOURCE_CONTRACT_VALID")
        self.assertEqual(result["profiles"], 7)
        self.assertEqual(result["modes"], 3)
        self.assertFalse(result["authentic_runtime_evidence"])

    def test_glass_composition_does_not_assume_hardware(self):
        profiles = module.load_json(module.PROFILES)
        glass = next(p for p in profiles["profiles"] if p["id"] == "flexible_glass")
        self.assertEqual(glass["capabilities"], [])
        self.assertTrue(glass["photovoltaic_is_not_display"])
        self.assertTrue(glass["standalone_compute_or_network_not_assumed"])

    def test_fail_closed_when_scope_is_broadened(self):
        profiles = module.load_json(module.PROFILES)
        profiles["modes"][0]["capture_scopes"].append("video_capture")
        with self.assertRaisesRegex(ValueError, "mode_capture_scope_mismatch"):
            module.validate_source_contract(profiles=profiles)

    def test_fail_closed_when_glass_claims_power_implies_display(self):
        profiles = module.load_json(module.PROFILES)
        profiles["profiles"][-1]["photovoltaic_is_not_display"] = False
        with self.assertRaisesRegex(ValueError, "photovoltaic_misrepresented_as_display"):
            module.validate_source_contract(profiles=profiles)


class ModeTransitionProposalTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "session_id": "fixture-existing-kv-conversation",
            "kv_skap_verification_observed": True,
            "peripheral_relationship_active": True,
            "eligible_node_observed": True,
            "observed_profiles": ["audio_input", "audio_output", "video_input", "video_output"],
            "current_capture_consents": ["audio_capture", "video_capture"],
            "typed_transport_observed": True,
            "all_hop_intr_admissions_observed": True,
            "scope_bound_manifest": True,
        }

    def evaluate(self, mode, **overrides):
        req = {**copy.deepcopy(self.base), "mode": mode, **overrides}
        return module.propose_live_mode(req)

    def assert_candidate_only(self, result):
        self.assertEqual(result["evidence_class"], "SOURCE_ONLY")
        self.assertFalse(result["authentic_transition_receipt"])
        self.assertFalse(result["master_records_reconstruction"])
        self.assertEqual(result["session_id"], self.base["session_id"])

    def test_three_mode_proposals_preserve_one_session(self):
        for mode in ("live_audio", "live_video", "live_audio_video"):
            result = self.evaluate(mode)
            self.assert_candidate_only(result)
            self.assertEqual(
                result["candidate_disposition"],
                "CANDIDATE_ALLOW_REQUIRES_REAL_RUNTIME_DISPOSITION",
            )

    def test_audio_never_infers_camera(self):
        result = self.evaluate("live_audio", current_capture_consents=["audio_capture"],
                               observed_profiles=["audio_input", "audio_output"])
        self.assert_candidate_only(result)
        self.assertEqual(result["requested_capture_scopes"], ["audio_capture"])

    def test_video_never_infers_microphone(self):
        result = self.evaluate("live_video", current_capture_consents=["video_capture"],
                               observed_profiles=["video_input", "video_output"])
        self.assert_candidate_only(result)
        self.assertEqual(result["requested_capture_scopes"], ["video_capture"])

    def test_missing_microphone_consent(self):
        result = self.evaluate("live_audio", current_capture_consents=["video_capture"])
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "CAPTURE_CONSENT_NOT_OBSERVED:audio_capture")

    def test_missing_camera_consent(self):
        result = self.evaluate("live_audio_video",
                               current_capture_consents=["audio_capture"])
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "CAPTURE_CONSENT_NOT_OBSERVED:video_capture")

    def test_revocation_fails_closed(self):
        result = self.evaluate("live_audio_video", peripheral_relationship_active=False)
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "SKAP_PERIPHERAL_RELATIONSHIP_INACTIVE_OR_REVOKED")

    def test_transport_not_observed(self):
        result = self.evaluate("live_audio", typed_transport_observed=False)
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"], "TYPED_TRANSPORT_NOT_OBSERVED")

    def test_intr_denial_not_reinterpreted_as_allow(self):
        result = self.evaluate("live_video", all_hop_intr_admissions_observed=False)
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "ADJACENT_INTR_ADMISSION_NOT_OBSERVED")

    def test_missing_verifier_not_device_substituted(self):
        result = self.evaluate("live_audio", kv_skap_verification_observed=False)
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "KV_SKAP_VERIFICATION_NOT_OBSERVED")

    def test_optional_glass_cannot_imply_camera(self):
        result = self.evaluate("live_video",
                               observed_profiles=["visual_display", "touch_gesture"],
                               current_capture_consents=["video_capture"])
        self.assert_candidate_only(result)
        self.assertEqual(result["first_missing_predicate"],
                         "PERIPHERAL_CAPABILITY_NOT_OBSERVED:video_input")

    def test_interchangeable_node_preserves_session(self):
        a = self.evaluate("live_audio", node_ref="eligible-node-A")
        b = self.evaluate("live_audio", node_ref="eligible-node-B")
        self.assert_candidate_only(a)
        self.assert_candidate_only(b)
        self.assertEqual(a["session_id"], b["session_id"])

    def test_mid_session_video_revocation_retains_independent_audio(self):
        combined = self.evaluate("live_audio_video")
        revoked = self.evaluate("live_audio_video",
                                current_capture_consents=["audio_capture"])
        surviving_audio = self.evaluate("live_audio",
                                       current_capture_consents=["audio_capture"])
        self.assert_candidate_only(combined)
        self.assert_candidate_only(revoked)
        self.assert_candidate_only(surviving_audio)
        self.assertIn("video_capture", revoked["first_missing_predicate"])
        self.assertEqual(surviving_audio["requested_capture_scopes"], ["audio_capture"])


if __name__ == "__main__":
    unittest.main()
