import unittest

from runtime.intr_epistemic_roundtrip import execute_discovery_roundtrip
from runtime.intr_epistemic_state import EpistemicItem


class InTrEpistemicRoundTripTests(unittest.TestCase):
    def test_discovery_forces_probe_until_all_affected_entities_incorporate(self):
        latent = EpistemicItem(
            item_id="u1",
            subject="previously unrepresented dependency",
            state="UNKNOWN",
            applicability="APPLICABLE",
        )
        result = execute_discovery_roundtrip(
            source_entity="A",
            affected_entities=("B", "C"),
            item=latent,
            discovery_id="d1",
            evidence_refs=("evidence:1",),
        )
        self.assertEqual(result.discovery.state, "DISCOVERED_UNKNOWN")
        self.assertEqual(result.discovery.scope_hypothesis, ("B", "C"))
        self.assertEqual(result.unresolved_entities, ("B", "C"))
        self.assertEqual(result.dependent_state, "PROBE_REQUIRED")
        self.assertTrue(all(a.incorporation_state == "PROBE_REQUIRED" for a in result.acknowledgements))


if __name__ == "__main__":
    unittest.main()
