from __future__ import annotations

import unittest

from reconstructive_memory.journal import SessionJournal


class SessionJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.common = {
            "session_id": "session-1",
            "pair_id": "sha256:" + "a" * 64,
            "policy_ref": "policy://memory/v1",
            "relationship_epoch": 2,
            "capability_commitment": "sha256:" + "b" * 64,
            "request_commitment": "sha256:" + "c" * 64,
        }

    def test_prepare_and_commit_forms_verified_chain(self) -> None:
        journal = SessionJournal().prepare(**self.common)
        self.assertEqual(journal.entries[-1].status, "prepared")
        journal = journal.commit("session-1", receipt_hash="sha256:" + "d" * 64)
        self.assertEqual(journal.entries[-1].status, "committed")
        self.assertEqual(len(journal.entries), 2)
        self.assertNotEqual(journal.entries[0].entry_hash, journal.entries[1].entry_hash)

    def test_abort_requires_prepared_session(self) -> None:
        with self.assertRaises(ValueError):
            SessionJournal().abort("missing", failure_code="PROOF_FAILURE")

    def test_terminal_state_cannot_be_extended(self) -> None:
        journal = SessionJournal().prepare(**self.common).commit(
            "session-1", receipt_hash="sha256:" + "d" * 64
        )
        with self.assertRaises(ValueError):
            journal.abort("session-1", failure_code="LATE_ABORT")

    def test_duplicate_session_is_recorded_as_replay_rejection(self) -> None:
        journal = SessionJournal().prepare(**self.common)
        replay = journal.prepare(**self.common)
        self.assertEqual(replay.entries[-1].status, "aborted")
        self.assertEqual(replay.entries[-1].failure_code, "SESSION_ID_REPLAY")
        self.assertNotEqual(replay.entries[-1].session_id, "session-1")

    def test_journal_retains_no_plaintext_query_or_result(self) -> None:
        journal = SessionJournal().prepare(**self.common).abort(
            "session-1", failure_code="OBJECT_TOMBSTONED"
        )
        serialized = repr([entry.payload() for entry in journal.entries])
        self.assertNotIn("private query", serialized)
        self.assertNotIn("private result", serialized)


if __name__ == "__main__":
    unittest.main()
