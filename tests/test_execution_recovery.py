import json
import unittest
from pathlib import Path

from execution.recovery import (
    RecoveryError,
    acquire_lease,
    decide_recovery,
    transition,
    validate_journal,
)


ROOT = Path(__file__).resolve().parents[1]


def load_journal():
    return json.loads(
        (ROOT / "fixtures" / "execution-recovery" / "facebook-post-interrupted.json")
        .read_text(encoding="utf-8")
    )


class ExecutionRecoveryTests(unittest.TestCase):
    def test_interrupted_dispatch_requires_verification_when_uncertain(self):
        decision = decide_recovery(load_journal(), receipt_result="INDETERMINATE")
        self.assertEqual(decision.decision, "VERIFY_EXTERNALLY")

    def test_observation_resumes_when_supported(self):
        decision = decide_recovery(
            load_journal(), receipt_result=None, connector_supports_observation=True
        )
        self.assertEqual(decision.decision, "RESUME_OBSERVATION")

    def test_executed_receipt_stops_duplicate_dispatch(self):
        decision = decide_recovery(load_journal(), receipt_result="EXECUTED")
        self.assertEqual(decision.decision, "STOP")

    def test_confirmed_failure_allows_exact_retry(self):
        decision = decide_recovery(
            load_journal(),
            receipt_result="FAILED",
            side_effect_absence_confirmed=True,
        )
        self.assertEqual(decision.decision, "RETRY_EXACT")

    def test_expired_authority_requires_ask(self):
        decision = decide_recovery(
            load_journal(), receipt_result=None, authority_still_current=False
        )
        self.assertEqual(decision.decision, "ASK")

    def test_active_lease_blocks_other_worker(self):
        with self.assertRaises(RecoveryError):
            acquire_lease(
                load_journal(),
                owner="auri-worker-02",
                acquired_at="2026-07-15T21:55:30Z",
                expires_at="2026-07-15T21:56:30Z",
                expected_revision=1,
            )

    def test_stale_revision_is_rejected(self):
        with self.assertRaises(RecoveryError):
            transition(
                load_journal(),
                new_state="OBSERVING",
                event="OBSERVATION_STARTED",
                actor="auri:primary",
                recorded_at="2026-07-15T21:56:10Z",
                receipt_sha256="6" * 64,
                expected_revision=0,
            )

    def test_terminal_requires_receipt_reference(self):
        with self.assertRaises(RecoveryError):
            transition(
                load_journal(),
                new_state="TERMINAL",
                event="RESULT_ATTACHED",
                actor="auri:primary",
                recorded_at="2026-07-15T21:56:10Z",
                receipt_sha256="6" * 64,
                expected_revision=1,
            )

    def test_event_sequence_must_be_monotonic(self):
        journal = load_journal()
        journal["events"][1]["sequence"] = 8
        with self.assertRaises(RecoveryError):
            validate_journal(journal)


if __name__ == "__main__":
    unittest.main()
