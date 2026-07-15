import json
import unittest
from copy import deepcopy
from pathlib import Path

from execution.adapter import (
    ConnectorResult,
    ExecutionEnvelopeError,
    assert_request_matches_envelope,
    canonical_sha256,
    make_receipt,
    prepare_connector_request,
    resolve_duplicate_attempt,
    validate_envelope,
)


ROOT = Path(__file__).resolve().parents[1]


def load_envelope():
    return json.loads(
        (ROOT / "fixtures" / "action-execution" / "facebook-good-times.prepared.json").read_text(
            encoding="utf-8"
        )
    )


class ActionExecutionTests(unittest.TestCase):
    def test_act_envelope_prepares_exact_connector_request(self):
        envelope = load_envelope()
        request = prepare_connector_request(envelope)
        self.assertEqual(request["destination"], "facebook:owner-account")
        self.assertEqual(request["payload"]["text"], "Good times!")
        assert_request_matches_envelope(envelope, request)

    def test_ask_or_deny_cannot_produce_envelope(self):
        for outcome in ("ASK", "DENY"):
            envelope = load_envelope()
            envelope["authority_decision"]["outcome"] = outcome
            with self.assertRaises(ExecutionEnvelopeError):
                validate_envelope(envelope)

    def test_destination_substitution_is_rejected(self):
        envelope = load_envelope()
        request = prepare_connector_request(envelope)
        request["destination"] = "facebook:public-timeline"
        with self.assertRaises(ExecutionEnvelopeError):
            assert_request_matches_envelope(envelope, request)

    def test_payload_substitution_is_rejected(self):
        envelope = load_envelope()
        request = prepare_connector_request(envelope)
        request["payload"] = deepcopy(request["payload"])
        request["payload"]["text"] = "Changed caption"
        with self.assertRaises(ExecutionEnvelopeError):
            assert_request_matches_envelope(envelope, request)

    def test_executed_requires_confirmation(self):
        envelope = load_envelope()
        with self.assertRaises(ExecutionEnvelopeError):
            make_receipt(
                envelope,
                ConnectorResult(status="EXECUTED", platform_object_id="post:1"),
                receipt_id="receipt:missing-confirmation",
            )

    def test_indeterminate_blocks_automatic_retry(self):
        envelope = load_envelope()
        receipt = make_receipt(
            envelope,
            ConnectorResult(
                status="INDETERMINATE",
                failure_code="TIMEOUT_AFTER_SUBMISSION",
                failure_message="Unknown completion state",
            ),
            receipt_id="receipt:indeterminate",
        )
        with self.assertRaises(ExecutionEnvelopeError):
            resolve_duplicate_attempt(envelope, [receipt])

    def test_executed_duplicate_returns_prior_receipt(self):
        envelope = load_envelope()
        receipt = make_receipt(
            envelope,
            ConnectorResult(
                status="EXECUTED",
                platform_object_id="facebook:post:1",
                confirmation="published",
            ),
            receipt_id="receipt:executed",
        )
        self.assertEqual(resolve_duplicate_attempt(envelope, [receipt]), receipt)

    def test_confirmed_failed_attempt_may_retry_same_envelope(self):
        envelope = load_envelope()
        receipt = make_receipt(
            envelope,
            ConnectorResult(
                status="FAILED",
                failure_code="REJECTED",
                side_effect_absence_confirmed=True,
            ),
            receipt_id="receipt:failed",
        )
        self.assertIsNone(resolve_duplicate_attempt(envelope, [receipt]))
        self.assertEqual(receipt["envelope_sha256"], canonical_sha256(envelope))


if __name__ == "__main__":
    unittest.main()
