import unittest

from runtime.intr_epistemic_state import (
    EpistemicItem,
    acknowledgement_for,
    discovered_unknown,
    unresolved_acknowledgements_block_ready,
)


class InTrEpistemicStateTests(unittest.TestCase):
    def test_known_applicable_item_is_incorporated(self):
        item = EpistemicItem("p1", "endpoint identity", "KNOWN", "APPLICABLE")
        ack = acknowledgement_for(receiver_entity="B", source_message_id="m1", item=item)
        self.assertEqual(ack.incorporation_state, "INCORPORATED")
        self.assertEqual(ack.incorporated_predicate_id, "p1")

    def test_ambiguity_requires_probe(self):
        item = EpistemicItem("p2", "intent scope", "AMBIGUOUS", "APPLICABLE")
        ack = acknowledgement_for(receiver_entity="B", source_message_id="m2", item=item)
        self.assertEqual(ack.incorporation_state, "PROBE_REQUIRED")
        self.assertTrue(unresolved_acknowledgements_block_ready([ack]))

    def test_unknown_applicability_requires_probe(self):
        item = EpistemicItem("p3", "new dependency", "KNOWN", "UNKNOWN")
        ack = acknowledgement_for(receiver_entity="B", source_message_id="m3", item=item)
        self.assertEqual(ack.incorporation_state, "PROBE_REQUIRED")

    def test_discovered_unknown_becomes_explicit_and_recomputes(self):
        latent = EpistemicItem("p4", "previously unrepresented condition", "UNKNOWN", "APPLICABLE")
        promoted = discovered_unknown(latent, discovery_id="d1", evidence_refs=("receipt:1",))
        self.assertEqual(promoted.state, "DISCOVERED_UNKNOWN")
        self.assertEqual(promoted.applicability, "UNKNOWN")
        self.assertEqual(promoted.readiness_effect, "RECOMPUTE_REQUIRED")
        ack = acknowledgement_for(receiver_entity="B", source_message_id="m4", item=promoted)
        self.assertEqual(ack.incorporation_state, "PROBE_REQUIRED")

    def test_receiver_may_establish_not_applicable(self):
        item = EpistemicItem("p5", "foreign condition", "KNOWN", "NOT_APPLICABLE")
        ack = acknowledgement_for(receiver_entity="B", source_message_id="m5", item=item)
        self.assertEqual(ack.incorporation_state, "NOT_APPLICABLE")
        self.assertFalse(unresolved_acknowledgements_block_ready([ack]))


if __name__ == "__main__":
    unittest.main()
