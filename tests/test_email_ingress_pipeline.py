import unittest

from runtime.email_ingress_pipeline import (
    EmailIngressError,
    decide,
    reconcile_duplicate,
    stage_message,
)


class EmailIngressPipelineTests(unittest.TestCase):
    def setUp(self):
        self.mapping_id = "kv-email:" + ("a" * 64)

    def _stage(self, *, payload="hello"):
        return stage_message(
            mapping_id=self.mapping_id,
            provider_message_id="provider-123",
            from_address="Sender@Example.com",
            subject="Subject",
            payload=payload,
        )

    def test_stage_is_untrusted_and_deterministic(self):
        first = self._stage()
        second = self._stage()
        self.assertEqual(first.canonical_message_id, second.canonical_message_id)
        self.assertEqual(first.staged_content_hash, second.staged_content_hash)
        self.assertEqual(first.trust_state, "STAGED_UNTRUSTED")

    def test_admit_creates_trusted_projection_and_payload_free_receipt(self):
        staged = self._stage()
        receipt, projection = decide(staged, signals=[])
        self.assertEqual(receipt.decision, "ADMIT")
        self.assertTrue(receipt.trusted_projection_created)
        self.assertFalse(receipt.payload_retained_in_receipt)
        self.assertIsNotNone(projection)
        self.assertEqual(projection.trust_state, "TRUSTED_ADMITTED")
        self.assertNotIn("payload", receipt.to_dict())

    def test_spam_rejects_without_projection(self):
        staged = self._stage()
        receipt, projection = decide(staged, signals=["spam_or_bulk_abuse"])
        self.assertEqual(receipt.decision, "REJECT")
        self.assertIsNone(projection)
        self.assertFalse(receipt.trusted_projection_created)

    def test_phishing_quarantines_without_projection(self):
        staged = self._stage()
        receipt, projection = decide(staged, signals=["phishing"])
        self.assertEqual(receipt.decision, "QUARANTINE")
        self.assertIsNone(projection)

    def test_user_restriction_requires_review(self):
        staged = self._stage()
        receipt, projection = decide(staged, signals=["user_review_required"])
        self.assertEqual(receipt.decision, "REVIEW")
        self.assertIsNone(projection)

    def test_governance_unavailable_fails_closed(self):
        staged = self._stage()
        receipt, projection = decide(staged, signals=[], governance_available=False)
        self.assertEqual(receipt.decision, "FAIL_CLOSED")
        self.assertIsNone(projection)

    def test_duplicate_reconciliation_is_idempotent(self):
        staged = self._stage()
        receipt, _ = decide(staged, signals=[])
        self.assertEqual(
            reconcile_duplicate(staged=staged, prior_receipt=receipt),
            "ALREADY_EVALUATED",
        )

    def test_same_provider_id_with_content_drift_fails(self):
        staged = self._stage(payload="hello")
        receipt, _ = decide(staged, signals=[])
        changed = self._stage(payload="changed")
        with self.assertRaises(EmailIngressError):
            reconcile_duplicate(staged=changed, prior_receipt=receipt)


if __name__ == "__main__":
    unittest.main()
