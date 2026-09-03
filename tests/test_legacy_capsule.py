import unittest

from runtime.legacy_capsule import (
    LegacyCapsuleError,
    build_capsule,
    evaluate_disclosure,
)


DIGEST = "a" * 64


class LegacyCapsuleTests(unittest.TestCase):
    def _capsule(self):
        return build_capsule(
            capsule_id="LEGACY-EXAMPLE-001",
            subject_ref="kv://personal/self",
            payload_class="MIXED",
            sealed_ref="kv://personal/legacy/sealed/LEGACY-EXAMPLE-001",
            payload_sha256=DIGEST,
            recipient_policy_ref="kv://personal/legacy/recipients/example",
            release_policy_ref="kv://personal/legacy/policies/example",
            participation_gate_ref="kv://personal/legacy/gates/example",
            qualified_reveal_stage="ASSET_CLASS",
        )

    def test_capsule_defaults_not_armed(self):
        capsule = self._capsule()
        self.assertFalse(capsule["armed"])
        self.assertEqual(capsule["state"], "NOT_ARMED")

    def test_plaintext_field_is_rejected(self):
        with self.assertRaises(LegacyCapsuleError):
            build_capsule(
                capsule_id="bad",
                subject_ref="kv://personal/self",
                payload_class="LETTER",
                sealed_ref="kv://legacy/1",
                payload_sha256=DIGEST,
                recipient_policy_ref="kv://recipient/1",
                release_policy_ref="kv://policy/1",
                qualified_reveal_stage="FULL_PAYLOAD",
                alternate_disposition_ref=None,
            ) | {"payload_text": "must never be embedded"}

    def test_invitation_does_not_reveal_capsule(self):
        result = evaluate_disclosure(self._capsule(), evidence={"INVITATION_DELIVERED"})
        self.assertEqual(result["stage"], "INVITED")
        self.assertNotIn("CAPSULE_EXISTS", result["disclose"])
        self.assertFalse(result["release_admissible"])

    def test_participation_without_qualification_stays_sealed(self):
        result = evaluate_disclosure(
            self._capsule(),
            evidence={"INVITATION_DELIVERED", "RECIPIENT_PARTICIPATING"},
        )
        self.assertEqual(result["stage"], "PARTICIPATING")
        self.assertEqual(result["disclose"], ())

    def test_qualified_recipient_gets_progressive_reveal_only(self):
        result = evaluate_disclosure(
            self._capsule(),
            evidence={
                "INVITATION_DELIVERED",
                "RECIPIENT_PARTICIPATING",
                "RECIPIENT_IDENTITY_VERIFIED",
                "RECIPIENT_PARTICIPATION_QUALIFIED",
            },
        )
        self.assertEqual(result["stage"], "QUALIFIED")
        self.assertEqual(
            result["disclose"],
            ("CAPSULE_EXISTS", "ORIGINATOR_IDENTITY", "ASSET_CLASS"),
        )
        self.assertFalse(result["release_admissible"])

    def test_unarmed_capsule_never_releases(self):
        result = evaluate_disclosure(
            self._capsule(),
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
