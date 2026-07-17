import copy
import unittest

from continuity.recall import build_index, event_hash, recall, sha256, validate_chain


def make_event(event_id, event_type, topic, subject_id, content, fidelity="exact", supersedes=None, previous=None):
    event = {
        "event_id": event_id,
        "previous_event_hash": previous,
        "timestamp": f"2026-07-{10 + int(event_id[-1])}T12:00:00Z",
        "actor": "user",
        "event_type": event_type,
        "topic": topic,
        "subject_id": subject_id,
        "supersedes": supersedes,
        "content": content,
        "content_hash": sha256(content) if content is not None else "0" * 64,
        "resulting_state_hash": sha256({"event_id": event_id, "content": content}),
        "retention_class": "full_fidelity" if content is not None else "integrity_only",
        "fidelity": fidelity,
        "artifact_refs": [],
        "authority_context": None,
        "policy_context": None,
    }
    return event


def chain():
    e1 = make_event("e1", "decision_accepted", "ingestion storage", "storage-v1", {"decision": "store bundles in every repository"}, previous=None)
    e2 = make_event("e2", "decision_superseded", "ingestion storage", "storage-v2", {"reason": "custody and reconstruction"}, supersedes="storage-v1", previous=event_hash(e1))
    e3 = make_event("e3", "decision_accepted", "ingestion storage", "storage-v2", {"decision": "master-records retains full bundles; downstream retains hashes and receipts"}, previous=event_hash(e2))
    e4 = make_event("e4", "implementation_recorded", "ingestion storage", "storage-v2", {"repositories": 3, "status": "partial"}, fidelity="semantic_reconstruction", previous=event_hash(e3))
    return [e1, e2, e3, e4]


class ConversationRecallTests(unittest.TestCase):
    def test_current_decision_excludes_superseded_version(self):
        result = recall(chain(), "what changed about ingestion storage")
        self.assertEqual(result["historical_conclusion"]["decision"], "master-records retains full bundles; downstream retains hashes and receipts")
        self.assertTrue(result["implemented"])
        self.assertFalse(result["superseded"])
        self.assertEqual(result["verification"], "chain_confirmed")

    def test_index_is_rebuildable(self):
        events = validate_chain(chain())
        first = build_index(events)
        second = build_index(events)
        self.assertEqual(first, second)
        self.assertEqual(first["event_count"], 4)

    def test_tampered_content_is_rejected(self):
        events = copy.deepcopy(chain())
        events[2]["content"]["decision"] = "tampered"
        with self.assertRaisesRegex(ValueError, "content hash mismatch"):
            validate_chain(events)

    def test_broken_chain_is_rejected(self):
        events = copy.deepcopy(chain())
        events[3]["previous_event_hash"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "breaks previous-event chain"):
            validate_chain(events)

    def test_missing_payload_cannot_claim_exact_fidelity(self):
        event = make_event("e1", "claim_introduced", "missing payload", "missing", None, fidelity="exact")
        with self.assertRaisesRegex(ValueError, "claims recoverable fidelity"):
            validate_chain([event])

    def test_no_match_is_honestly_unavailable(self):
        result = recall(chain(), "unrelated astronomy")
        self.assertEqual(result["result_type"], "unavailable")
        self.assertEqual(result["current_status"], "not_found")


if __name__ == "__main__":
    unittest.main()
