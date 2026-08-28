import unittest

from runtime.email_continuity import (
    bind_skap_credential,
    create_mapping,
    mark_session_verified,
)
from runtime.personal_contact_profile import (
    PersonalContactProfileError,
    add_email,
    map_email_entry,
    new_profile,
    sync_mapping_state,
    validate_profile,
)


class PersonalContactProfileTests(unittest.TestCase):
    def test_multiple_email_addresses_are_supported(self):
        profile = new_profile()
        profile = add_email(profile, address="one@example.com", label="personal", primary=True)
        profile = add_email(profile, address="two@example.com", label="work")
        self.assertEqual(len(profile["email_addresses"]), 2)
        self.assertEqual(validate_profile(profile), [])

    def test_only_one_primary_is_preserved(self):
        profile = new_profile()
        profile = add_email(profile, address="one@example.com", primary=True)
        profile = add_email(profile, address="two@example.com", primary=True)
        primaries = [item for item in profile["email_addresses"] if item["primary"]]
        self.assertEqual([item["address"] for item in primaries], ["two@example.com"])

    def test_duplicate_address_is_rejected_case_insensitively(self):
        profile = add_email(new_profile(), address="User@Example.com")
        with self.assertRaises(PersonalContactProfileError):
            add_email(profile, address="user@example.com")

    def test_address_can_exist_without_mailbox_monitoring(self):
        profile = add_email(new_profile(), address="user@example.com")
        item = profile["email_addresses"][0]
        self.assertFalse(item["email_continuity_enabled"])
        self.assertIsNone(item["mapping_id"])
        self.assertEqual(item["connection_state"], "UNMAPPED")

    def test_mapping_existing_profile_address_enables_email_continuity(self):
        profile = add_email(new_profile(), address="user@example.com")
        mapping = create_mapping(
            email_address="user@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        profile = map_email_entry(profile, mapping)
        item = profile["email_addresses"][0]
        self.assertTrue(item["email_continuity_enabled"])
        self.assertEqual(item["mapping_id"], mapping.mapping_id)
        self.assertEqual(item["connection_state"], "MAPPED_CREDENTIAL_REQUIRED")

    def test_each_address_has_independent_connection_state(self):
        profile = add_email(new_profile(), address="one@example.com", primary=True)
        profile = add_email(profile, address="two@example.com", label="work")

        one = create_mapping(
            email_address="one@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        two = create_mapping(
            email_address="two@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        profile = map_email_entry(profile, one)
        profile = map_email_entry(profile, two)

        one_bound = bind_skap_credential(one, skap_credential_ref="skap://Mail/example/one")
        one_verified = mark_session_verified(one_bound)
        profile = sync_mapping_state(profile, one_verified)

        states = {item["address"]: item["connection_state"] for item in profile["email_addresses"]}
        self.assertEqual(states["one@example.com"], "SESSION_VERIFIED")
        self.assertEqual(states["two@example.com"], "MAPPED_CREDENTIAL_REQUIRED")

    def test_mapping_unknown_profile_address_is_rejected(self):
        profile = add_email(new_profile(), address="one@example.com")
        mapping = create_mapping(
            email_address="two@example.com",
            provider_id="example-mail",
            provider_route="provider://example/mail",
        )
        with self.assertRaises(PersonalContactProfileError):
            map_email_entry(profile, mapping)


if __name__ == "__main__":
    unittest.main()
