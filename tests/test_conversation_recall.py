import copy
import unittest
from pathlib import Path

from continuity.recall import archive_readiness, build_index, event_hash, load_jsonl, recall, sha256, validate_chain

FIXTURE = Path("fixtures/conversation-recall/example-vault/events.jsonl")


def make_event(event_id, event_type, topic, subject_id, content, fidelity="exact", supersedes=None, previous=None, status=None):
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


def chain(complete=False):
    e1 = make_event("e1", "decision_accepted", "ingestion storage", "storage-v1", {"decision": "store bundles in every repository"})
    e2 = make_event("e2", "decision_superseded", "ingestion storage", "storage-v2", {"reason": "custody and reconstruction"}, supersedes="storage-v1", previous=event_hash(e1))
    e3 = make_event("e3", "decision_accepted", "ingestion storage", "storage-v2", {"decision": "master-records retains full bundles; downstream retains hashes and receipts"}, previous=event_hash(e2))
    implementation = {"status": "complete", "remaining": []} if complete else {"status": "partial", "remaining": ["propagation verification"]}
    e4 = make_event("e4", "implementation_recorded", "ingestion storage", "storage-v2", implementation, fidelity="semantic_reconstruction", previous=event_hash(e3))
    return [e1, e2, e3, e4]


class ConversationRecallTests(unittest.TestCase):
    def test_current_decision_excludes_superseded_version(self):
        result = recall(chain(), "what changed about ingestion storage")
        self.assertEqual(result["historical_conclusion"]["decision"], "master-records retains full bundles; downstream retains hashes and receipts")
        self.assertTrue(result["implemented"])
        self.assertFalse(result["superseded"])
        self.assertEqual(result["verification"], "chain_confirmed")

    def test_time_window_answers_yesterday_to_now(self):
        events = load_jsonl(FIXTURE)
        result = recall(events, "What changed between yesterday and now about ingestion storage?", since="2026-07-16T00:00:00Z", until="2026-07-17T23:59:59Z")
        self.assertEqual(result["historical_conclusion"]["decision"], "master-records retains full bundles; downstream repositories retain hashes, receipts, pointers, and active-custody exceptions")
        self.assertEqual(result["result_type"], "exact")
        self.assertEqual(result["verification_root"], "c75ae4fb1b048b3583ec7463bf63b9d0c12b7334831c9b0235651eb569b494ed")

    def test_archive_readiness_stays_false_for_partial_goal(self):
        readiness = archive_readiness(load_jsonl(FIXTURE))
        self.assertFalse(readiness["ready"])
        self.assertIn("storage-policy-v2", readiness["blockers"])

    def test_archive_readiness_can_become_true(self):
        readiness = archive_readiness(chain(complete=True))
        self.assertTrue(readiness["ready"])

    def test_index_is_rebuildable(self):
        events = validate_chain(chain())
        self.assertEqual(build_index(events), build_index(events))
        self.assertEqual(build_index(events)["event_count"], 4)

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
