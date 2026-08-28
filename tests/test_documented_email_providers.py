import copy
import json
import tempfile
import unittest
from pathlib import Path

from runtime.documented_email_providers import load_documented_provider_registry
from runtime.email_continuity import EmailMappingError


class DocumentedEmailProviderTests(unittest.TestCase):
    def test_gmail_discovery_is_documented_unverified(self):
        registry = load_documented_provider_registry()
        mapping = registry.discover("user@gmail.com")
        descriptor = registry.descriptor_for(mapping)
        self.assertEqual(mapping.provider_id, "google-gmail")
        self.assertEqual(mapping.mapping_state, "MAPPED_CREDENTIAL_REQUIRED")
        self.assertEqual(descriptor["minimum_read_permission"], "https://www.googleapis.com/auth/gmail.readonly")
        self.assertEqual(descriptor["evidence_state"], "DOCUMENTED_UNVERIFIED")
        self.assertFalse(descriptor["runtime_verified"])
        self.assertTrue(descriptor["skap_credential_ref_required"])

    def test_outlook_discovery_uses_delegated_mail_read(self):
        registry = load_documented_provider_registry()
        mapping = registry.discover("user@outlook.com")
        descriptor = registry.descriptor_for(mapping)
        self.assertEqual(mapping.provider_id, "microsoft-outlook-graph")
        self.assertEqual(descriptor["minimum_read_permission"], "Mail.Read")
        self.assertEqual(descriptor["authorization_mode"], "OAUTH2_DELEGATED")

    def test_icloud_discovery_uses_skap_bound_app_specific_password(self):
        registry = load_documented_provider_registry()
        mapping = registry.discover("user@icloud.com")
        descriptor = registry.descriptor_for(mapping)
        self.assertEqual(mapping.provider_id, "apple-icloud-mail")
        self.assertEqual(descriptor["authorization_mode"], "APP_SPECIFIC_PASSWORD")
        self.assertEqual(mapping.mapping_state, "MAPPED_CREDENTIAL_REQUIRED")
        self.assertTrue(descriptor["skap_credential_ref_required"])

    def test_unknown_domain_fails_closed(self):
        registry = load_documented_provider_registry()
        with self.assertRaises(EmailMappingError):
            registry.discover("user@example.org")

    def test_overlapping_domains_are_rejected(self):
        source = Path("specs/kv-email-provider-registry.v1.json")
        data = json.loads(source.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(data["providers"][0])
        duplicate["provider_id"] = "duplicate-provider"
        data["providers"].append(duplicate)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(EmailMappingError):
                load_documented_provider_registry(path)


if __name__ == "__main__":
    unittest.main()
