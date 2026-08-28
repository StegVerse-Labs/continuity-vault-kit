import copy
import json
import unittest
from pathlib import Path

from tools.check_kv_email_ingress_policy import load_policy, validate


class EmailIngressPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def test_canonical_policy_passes(self):
        self.assertEqual(validate(self.policy), [])

    def test_plaintext_credentials_fail(self):
        policy = copy.deepcopy(self.policy)
        policy["provider_session"]["credential_storage"] = "PLAINTEXT_PASSWORD"
        self.assertTrue(any("plaintext" in error for error in validate(policy)))

    def test_skap_vault_is_required_for_activation(self):
        policy = copy.deepcopy(self.policy)
        policy["skap_credential_binding"]["required_for_activation"] = False
        self.assertTrue(any("SKAP Vault" in error for error in validate(policy)))

    def test_kv_cannot_store_mailbox_secret(self):
        policy = copy.deepcopy(self.policy)
        policy["skap_credential_binding"]["kv_stores_secret"] = True
        self.assertTrue(any("must not store" in error for error in validate(policy)))

    def test_mapping_must_prompt_for_credential_completion(self):
        policy = copy.deepcopy(self.policy)
        policy["skap_credential_binding"]["user_prompt_after_mapping"] = False
        self.assertTrue(any("prompted" in error for error in validate(policy)))

    def test_pre_admission_trust_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["staging"]["trusted_kv_content_before_decision"] = True
        self.assertTrue(any("trusted KV content" in error for error in validate(policy)))

    def test_ambiguity_must_fail_closed(self):
        policy = copy.deepcopy(self.policy)
        policy["governance"]["default_on_ambiguity"] = "ADMIT"
        self.assertTrue(any("fail closed" in error for error in validate(policy)))

    def test_only_admit_promotes_trusted_content(self):
        policy = copy.deepcopy(self.policy)
        policy["admission"]["trusted_content_decision"] = "REVIEW"
        self.assertTrue(any("only ADMIT" in error for error in validate(policy)))

    def test_every_evaluation_requires_receipt(self):
        policy = copy.deepcopy(self.policy)
        policy["receipt"]["required_for_every_evaluation"] = False
        self.assertTrue(any("requires a governance receipt" in error for error in validate(policy)))

    def test_rejected_payload_retention_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["receipt"]["retain_rejected_payload"] = True
        self.assertTrue(any("must not be retained" in error for error in validate(policy)))


if __name__ == "__main__":
    unittest.main()
