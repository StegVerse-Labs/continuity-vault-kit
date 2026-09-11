import unittest

from runtime.intr_epistemic_state import (
    EpistemicItem,
    acknowledgement_for,
    acknowledgement_is_fresh,
    acknowledgement_satisfies_consequence,
    aggregate_receiver_completion,
    discovered_unknown,
    supersede,
    unresolved_acknowledgements_block_ready,
)


class InTrEpistemicStateTests(unittest.TestCase):
    def test_receipt_does_not_imply_incorporation(self):
        item = EpistemicItem("p1", "endpoint identity", "KNOWN", "APPLICABLE")
        ack = acknowledgement_for(acknowledgement_id="a1", receiver_entity="B", source_message_id="m1", item=item)
        self.assertEqual(ack.level, "RECEIVED")
        self.assertIsNone(ack.incorporated_predicate_id)
        self.assertFalse(acknowledgement_satisfies_consequence(ack, "HIGH_CONSEQUENCE"))

    def test_incorporation_is_explicit(self):
        item = EpistemicItem("p1", "endpoint identity", "KNOWN", "APPLICABLE")
        ack = acknowledgement_for(acknowledgement_id="a2", receiver_entity="B", source_message_id="m1", item=item, level="INCORPORATED")
        self.assertEqual(ack.incorporated_predicate_id, "p1")
        self.assertTrue(acknowledgement_satisfies_consequence(ack, "HIGH_CONSEQUENCE"))

    def test_ambiguity_cannot_advance_past_unresolved_applicability(self):
        item = EpistemicItem("p2", "intent scope", "AMBIGUOUS", "APPLICABLE")
        with self.assertRaises(ValueError):
            acknowledgement_for(acknowledgement_id="a3", receiver_entity="B", source_message_id="m2", item=item, level="INCORPORATED")

    def test_unknown_applicability_requires_probe(self):
        item = EpistemicItem("p3", "new dependency", "KNOWN", "UNKNOWN")
        ack = acknowledgement_for(acknowledgement_id="a4", receiver_entity="B", source_message_id="m3", item=item)
        self.assertEqual(ack.incorporation_state, "PROBE_REQUIRED")
        self.assertTrue(unresolved_acknowledgements_block_ready([ack]))

    def test_discovered_unknown_carries_scope_hypothesis_not_sender_authority(self):
        latent = EpistemicItem("p4", "previously unrepresented condition", "UNKNOWN", "APPLICABLE")
        promoted = discovered_unknown(latent, discovery_id="d1", evidence_refs=("receipt:1",), scope_hypothesis=("B", "C"))
        self.assertEqual(promoted.state, "DISCOVERED_UNKNOWN")
        self.assertEqual(promoted.applicability, "UNKNOWN")
        self.assertEqual(promoted.scope_hypothesis, ("B", "C"))

    def test_dispute_is_representable_and_blocks_ready(self):
        item = EpistemicItem("p5", "shared interpretation", "DISPUTED", "APPLICABLE")
        ack = acknowledgement_for(acknowledgement_id="a5", receiver_entity="B", source_message_id="m5", item=item, dispute_ref="dispute:1")
        self.assertEqual(ack.incorporation_state, "DISPUTED")
        self.assertTrue(unresolved_acknowledgements_block_ready([ack]))

    def test_supersession_preserves_lineage(self):
        old = EpistemicItem("old", "policy state", "KNOWN", "APPLICABLE", source_evidence_refs=("e:old",))
        new = supersede(old, new_item_id="new", state="KNOWN", evidence_refs=("e:new",))
        self.assertEqual(new.supersedes_item_id, "old")
        self.assertEqual(new.source_evidence_refs, ("e:new",))

    def test_expired_epistemic_state_is_not_fresh(self):
        item = EpistemicItem("p6", "session identity", "KNOWN", "APPLICABLE", valid_until="2026-09-10T15:00:00-05:00")
        ack = acknowledgement_for(acknowledgement_id="a6", receiver_entity="B", source_message_id="m6", item=item, observed_at="2026-09-10T14:59:00-05:00")
        self.assertFalse(acknowledgement_is_fresh(ack, item, now="2026-09-10T15:01:00-05:00"))

    def test_multi_recipient_completion_requires_each_affected_entity(self):
        item = EpistemicItem("p7", "transition predicate", "KNOWN", "APPLICABLE")
        ack_b = acknowledgement_for(acknowledgement_id="a7", receiver_entity="B", source_message_id="m7", item=item, level="INCORPORATED")
        missing = aggregate_receiver_completion(affected_entities=("B", "C"), acknowledgements=(ack_b,), consequence="HIGH_CONSEQUENCE")
        self.assertEqual(missing, ("C",))


if __name__ == "__main__":
    unittest.main()
