from __future__ import annotations

import unittest
from pathlib import Path

from runtime.legacy_capsule import build_capsule, evaluate_disclosure


ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = ROOT / "vault_template" / "KnowledgeVault" / "_Entities" / "Self" / "Legacy"


class LegacyKVSourceContractTests(unittest.TestCase):
    def test_expected_template_layout_is_source_complete(self) -> None:
        self.assertTrue((LEGACY_ROOT / "README.md").is_file())
        self.assertTrue((LEGACY_ROOT / "Capsules").is_dir())
        self.assertTrue((LEGACY_ROOT / "Policies").is_dir())
        self.assertTrue((LEGACY_ROOT / "Recipients").is_dir())

    def test_readme_preserves_non_authority_boundaries(self) -> None:
        text = (LEGACY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Do not store reusable credentials", text)
        self.assertIn("does not arm a capsule", text)
        self.assertIn("Disclosure is governed separately from custody", text)

    def test_capsule_defaults_fail_closed_for_release(self) -> None:
        capsule = build_capsule(
            capsule_id="LEGACY-SOURCE-CONTRACT-001",
            subject_ref="kv://personal/self",
            payload_class="LETTER",
            sealed_ref="kv://personal/legacy/sealed/LEGACY-SOURCE-CONTRACT-001",
            payload_sha256="a" * 64,
            recipient_policy_ref="kv://personal/legacy/recipients/source-contract",
            release_policy_ref="kv://personal/legacy/policies/source-contract",
            participation_gate_ref="kv://personal/legacy/gates/source-contract",
            qualified_reveal_stage="CAPSULE_EXISTS",
        )
        self.assertFalse(capsule["armed"])
        self.assertEqual(capsule["state"], "NOT_ARMED")
        result = evaluate_disclosure(
            capsule,
            evidence={
                "INVITATION_DELIVERED",
                "RECIPIENT_IDENTITY_VERIFIED",
                "RECIPIENT_PARTICIPATION_QUALIFIED",
                "RELEASE_TRIGGER_VERIFIED",
                "TVC_AUTHORIZATION_VERIFIED",
                "INTR_RELEASE_ALLOW",
            },
        )
        self.assertFalse(result["release_admissible"])


if __name__ == "__main__":
    unittest.main()
