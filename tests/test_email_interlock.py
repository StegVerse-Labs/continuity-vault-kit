import unittest

from runtime.email_continuity import (
    EmailMappingError,
    bind_skap_credential,
    create_mapping,
    mark_session_verified,
    revoke_mapping,
)
from runtime.email_interlock import (
    build_ingress_discovery_request,
    build_ingress_evaluation_request,
    build_projection_candidate_request,
)


class EmailInterlockBridgeTests(unittest.TestCase):
    def _mapped(self):
        return create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )

    def _verified(self):
        mapped = self._mapped()
        bound = bind_skap_credential(mapped, skap_credential_ref="skap://Mail/example/user")
        return mark_session_verified(bound)

    def test_discovery_request_contains_no_secret_fields(self):
        request = build_ingress_discovery_request(
            request_id="req-discover-1",
            authority_ref="authority://owner/example",
            mapping=self._mapped(),
        )
        encoded = str(request).lower()
        self.assertEqual(request["operation"], "DISCOVER")
        self.assertNotIn("password", encoded)
        self.assertNotIn("access_token", encoded)
        self.assertNotIn("refresh_token", encoded)

    def test_evaluation_requires_verified_session(self):
        with self.assertRaises(EmailMappingError):
            build_ingress_evaluation_request(
                request_id="req-eval-1",
                authority_ref="authority://owner/example",
                mapping=self._mapped(),
            )

    def test_verified_session_can_request_ingress_evaluation(self):
        request = build_ingress_evaluation_request(
            request_id="req-eval-2",
            authority_ref="authority://owner/example",
            mapping=self._verified(),
        )
        self.assertEqual(request["operation"], "REQUEST")
        self.assertEqual(request["record_class"], "email-continuity")
        self.assertEqual(request["disclosure_mode"], "SOURCE_REFERENCE_ONLY")

    def test_projection_is_candidate_only(self):
        request = build_projection_candidate_request(
            request_id="req-write-1",
            authority_ref="authority://owner/example",
            mapping=self._verified(),
            payload_ref="sha256:" + ("b" * 64),
        )
        self.assertEqual(request["operation"], "COMMIT_CANDIDATE")
        self.assertEqual(
            request["candidate_writeback"]["candidate_type"],
            "email_admitted_projection",
        )
        self.assertTrue(request["candidate_writeback"]["payload_ref"].startswith("sha256:"))

    def test_revoked_mapping_cannot_request_interlock(self):
        with self.assertRaises(EmailMappingError):
            build_ingress_discovery_request(
                request_id="req-revoked",
                authority_ref="authority://owner/example",
                mapping=revoke_mapping(self._mapped()),
            )


if __name__ == "__main__":
    unittest.main()
