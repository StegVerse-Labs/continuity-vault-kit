import unittest

from runtime.email_continuity import (
    EmailMappingError,
    assert_no_secret_fields,
    bind_skap_credential,
    create_mapping,
    mapping_id_for,
    mark_session_verified,
    next_activation_action,
    revoke_mapping,
)


class EmailContinuityRuntimeTests(unittest.TestCase):
    def test_mapping_is_deterministic_and_requires_skap(self):
        mapping = create_mapping(
            email_address="User@Example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        self.assertEqual(mapping.email_address, "user@example.com")
        self.assertEqual(mapping.mapping_id, mapping_id_for("user@example.com"))
        self.assertEqual(mapping.mapping_state, "MAPPED_CREDENTIAL_REQUIRED")
        self.assertIsNone(mapping.skap_credential_ref)
        self.assertFalse(mapping.credential_secret_present_in_kv)
        self.assertEqual(mapping.authority_effect, "NONE")

    def test_mapping_next_action_prompts_skap_vault(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        action = next_activation_action(mapping)
        self.assertEqual(action["action"], "COMPLETE_SKAP_CREDENTIAL_SETUP")
        self.assertEqual(action["credential_destination"], "SKAP_VAULT")
        self.assertEqual(action["raw_secret_destination"], "PROHIBITED_IN_KV")
        self.assertEqual(action["authority_effect"], "NONE")

    def test_skap_binding_moves_to_credential_bound(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        bound = bind_skap_credential(mapping, skap_credential_ref="skap://Mail/example/user")
        self.assertEqual(bound.mapping_state, "CREDENTIAL_BOUND")
        self.assertEqual(bound.skap_credential_ref, "skap://Mail/example/user")
        self.assertFalse(bound.credential_secret_present_in_kv)

    def test_session_cannot_be_verified_without_skap_binding(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        with self.assertRaises(EmailMappingError):
            mark_session_verified(mapping)

    def test_session_verification_requires_only_reference(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        bound = bind_skap_credential(mapping, skap_credential_ref="skap://Mail/example/user")
        verified = mark_session_verified(bound)
        self.assertEqual(verified.mapping_state, "SESSION_VERIFIED")
        self.assertFalse(verified.credential_secret_present_in_kv)

    def test_raw_secret_fields_are_rejected(self):
        for key in ("password", "secret", "token", "access_token", "refresh_token", "app_password"):
            with self.subTest(key=key), self.assertRaises(EmailMappingError):
                assert_no_secret_fields({key: "synthetic"})

    def test_non_skap_reference_rejected(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        with self.assertRaises(EmailMappingError):
            bind_skap_credential(mapping, skap_credential_ref="kv://secret")

    def test_revoked_mapping_cannot_be_rebound(self):
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        revoked = revoke_mapping(mapping)
        with self.assertRaises(EmailMappingError):
            bind_skap_credential(revoked, skap_credential_ref="skap://Mail/example/user")


if __name__ == "__main__":
    unittest.main()
