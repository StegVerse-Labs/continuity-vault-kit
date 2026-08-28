import unittest

from runtime.email_continuity import EmailMappingError
from runtime.email_provider_adapter import ProviderRegistry


class ExampleAdapter:
    provider_id = "example-mail"
    provider_route = "provider://example/mail"

    def matches_domain(self, domain: str) -> bool:
        return domain == "example.com"

    def session_descriptor(self, mapping):
        return {
            "provider_id": self.provider_id,
            "provider_route": self.provider_route,
            "mapping_id": mapping.mapping_id,
            "skap_credential_ref_required": True,
            "authority_effect": "NONE",
        }


class SecretLeakingAdapter(ExampleAdapter):
    provider_id = "bad-mail"
    provider_route = "provider://bad/mail"

    def matches_domain(self, domain: str) -> bool:
        return domain == "bad.example"

    def session_descriptor(self, mapping):
        return {"access_token": "synthetic-prohibited"}


class EmailProviderAdapterTests(unittest.TestCase):
    def test_discovery_creates_credential_required_mapping(self):
        registry = ProviderRegistry([ExampleAdapter()])
        mapping = registry.discover("User@Example.com")
        self.assertEqual(mapping.provider_id, "example-mail")
        self.assertEqual(mapping.mapping_state, "MAPPED_CREDENTIAL_REQUIRED")
        self.assertIsNone(mapping.skap_credential_ref)

    def test_unknown_provider_fails_closed(self):
        registry = ProviderRegistry([ExampleAdapter()])
        with self.assertRaises(EmailMappingError):
            registry.discover("user@unknown.example")

    def test_ambiguous_provider_fails_closed(self):
        registry = ProviderRegistry([ExampleAdapter(), ExampleAdapter()])
        with self.assertRaises(EmailMappingError):
            registry.discover("user@example.com")

    def test_session_descriptor_is_secret_free(self):
        registry = ProviderRegistry([ExampleAdapter()])
        mapping = registry.discover("user@example.com")
        descriptor = registry.descriptor_for(mapping)
        self.assertTrue(descriptor["skap_credential_ref_required"])
        self.assertEqual(descriptor["authority_effect"], "NONE")

    def test_secret_leaking_adapter_is_rejected(self):
        registry = ProviderRegistry([SecretLeakingAdapter()])
        mapping = registry.discover("user@bad.example")
        with self.assertRaises(EmailMappingError):
            registry.descriptor_for(mapping)


if __name__ == "__main__":
    unittest.main()
