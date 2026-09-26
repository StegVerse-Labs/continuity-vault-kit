import unittest

from runtime.intr_epistemic_packet_binding import bind_epistemic_envelope, require_epistemic_binding


class InTrEpistemicPacketBindingTests(unittest.TestCase):
    def envelope(self, consequence="STATE_CHANGING", required=True, level="APPLICABILITY_RESOLVED"):
        return {
            "schema": "stegverse.intr.epistemic-state/v1",
            "message_id": "m1",
            "conversation_id": "c1",
            "sender_entity": "A",
            "recipient_entities": ["B"],
            "message_class": "ASSERTION",
            "claim_scope": "test",
            "consequence_class": consequence,
            "created_at": "2026-09-10T15:00:00-05:00",
            "requires_acknowledgement": required,
            "required_acknowledgement_level": level,
            "epistemic_items": [{
                "item_id": "p1",
                "subject": "condition",
                "state": "KNOWN",
                "applicability": "APPLICABLE",
                "source_evidence_refs": [],
                "readiness_effect": "RECOMPUTE_REQUIRED"
            }],
            "authority_effect": "NONE"
        }

    def test_state_changing_message_binds_hash_and_ack_depth(self):
        binding = bind_epistemic_envelope(self.envelope())
        self.assertEqual(binding.required_acknowledgement_level, "APPLICABILITY_RESOLVED")
        self.assertTrue(binding.epistemic_envelope_sha256.startswith("sha256:"))
        require_epistemic_binding(consequence_class="STATE_CHANGING", binding=binding)

    def test_state_relevant_message_cannot_disable_acknowledgement(self):
        with self.assertRaises(ValueError):
            bind_epistemic_envelope(self.envelope(consequence="STATE_RELEVANT", required=False, level="INTERPRETED"))

    def test_consequence_controls_acknowledgement_depth(self):
        with self.assertRaises(ValueError):
            bind_epistemic_envelope(self.envelope(level="RECEIVED"))

    def test_state_relevant_transport_without_binding_fails_closed(self):
        with self.assertRaises(ValueError):
            require_epistemic_binding(consequence_class="STATE_CHANGING", binding=None)

    def test_informational_transport_may_be_lightweight(self):
        require_epistemic_binding(consequence_class="INFORMATIONAL", binding=None)


if __name__ == "__main__":
    unittest.main()
