import unittest

from runtime.direct_source_ingress import (
    DirectSourceIngressError,
    admit_receipt,
    build_request,
    fail_closed_receipt,
)


class DirectSourceIngressTests(unittest.TestCase):
    def test_build_request_requires_skap(self):
        with self.assertRaises(DirectSourceIngressError):
            build_request(
                source_id="example-bank",
                source_kind="financial_institution",
                target_domain="finance",
                skap_credential_ref="not-skap",
            )

    def test_build_request_is_read_only_direct_source(self):
        req = build_request(
            source_id="example-bank",
            source_kind="financial_institution",
            target_domain="finance",
            skap_credential_ref="skap://finance/example-bank",
            masked_owner_reference="acct-1234",
        )
        self.assertEqual(req["requested_access"], "READ_ONLY")
        self.assertTrue(req["direct_source_required"])
        self.assertTrue(req["minimum_necessary"])
        self.assertEqual(req["authority_effect"], "NONE")

    def test_secret_provider_result_is_rejected(self):
        req = build_request(
            source_id="example-bank",
            source_kind="financial_institution",
            target_domain="assets",
            skap_credential_ref="skap://finance/example-bank",
        )
        with self.assertRaises(DirectSourceIngressError):
            admit_receipt(
                req,
                {
                    "direct_source_verified": True,
                    "session_verified": True,
                    "retrieved_at": "2026-08-28T15:00:00Z",
                    "access_token": "should-not-propagate",
                },
                normalization_receipt_ref="norm:1",
                persistence_receipt_ref="kv:1",
            )

    def test_verified_direct_source_can_admit(self):
        req = build_request(
            source_id="example-music",
            source_kind="music_provider",
            target_domain="music",
            skap_credential_ref="skap://music/example",
        )
        receipt = admit_receipt(
            req,
            {
                "direct_source_verified": True,
                "session_verified": True,
                "retrieved_at": "2026-08-28T15:00:00Z",
                "freshness_state": "FRESH",
                "adapter_version": "synthetic-v1",
                "intermediary": {"used": False, "name": None},
            },
            normalization_receipt_ref="norm:music:1",
            persistence_receipt_ref="kv:music:1",
        )
        self.assertEqual(receipt["state"], "ADMITTED_PERSISTED")
        self.assertTrue(receipt["direct_source_verified"])
        self.assertFalse(receipt["intermediary_used"])

    def test_unverified_source_fails_closed(self):
        req = build_request(
            source_id="example-photo",
            source_kind="photo_provider",
            target_domain="pictures",
            skap_credential_ref="skap://photos/example",
        )
        with self.assertRaises(DirectSourceIngressError):
            admit_receipt(
                req,
                {
                    "direct_source_verified": False,
                    "session_verified": True,
                    "retrieved_at": "2026-08-28T15:00:00Z",
                },
                normalization_receipt_ref="norm:1",
                persistence_receipt_ref="kv:1",
            )

    def test_explicit_fail_closed_receipt(self):
        req = build_request(
            source_id="example-mail",
            source_kind="mailbox_provider",
            target_domain="email",
            skap_credential_ref="skap://mail/example",
        )
        receipt = fail_closed_receipt(req, "provider session unavailable")
        self.assertEqual(receipt["state"], "FAIL_CLOSED")
        self.assertEqual(receipt["freshness_state"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
