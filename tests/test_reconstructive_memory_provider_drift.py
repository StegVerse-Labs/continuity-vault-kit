from datetime import datetime, timezone
import unittest

from reconstructive_memory.provider_drift import (
    ConformanceBaseline,
    DriftKind,
    ProviderObservation,
    compare_conformance,
)


NOW = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)


def observation(role: str, *, resource: str | None = None, capability: str = "verify", evidence: str = "e1", success: bool = True, observed_at: str = "2026-07-15T19:59:30Z") -> ProviderObservation:
    return ProviderObservation(
        role=role,
        resource=resource or f"resource:{role}",
        capability=capability,
        evidence_commitment=evidence,
        observed_at=observed_at,
        success=success,
    )


class ProviderDriftTests(unittest.TestCase):
    def baseline(self) -> ConformanceBaseline:
        return ConformanceBaseline(
            profile_commitment="profile-v1",
            observations=(observation("stegid"), observation("custody")),
            created_at="2026-07-15T19:00:00Z",
        )

    def test_matching_fresh_observations_allow(self) -> None:
        report = compare_conformance(
            self.baseline(),
            "profile-v1",
            (observation("stegid"), observation("custody")),
            max_age_seconds=120,
            now=NOW,
        )
        self.assertTrue(report.ready)
        self.assertEqual(report.decision, "ALLOW")

    def test_profile_and_resource_drift_fail_closed(self) -> None:
        report = compare_conformance(
            self.baseline(),
            "profile-v2",
            (observation("stegid", resource="resource:new"), observation("custody")),
            max_age_seconds=120,
            now=NOW,
        )
        kinds = {finding.kind for finding in report.findings}
        self.assertIn(DriftKind.PROFILE, kinds)
        self.assertIn(DriftKind.RESOURCE_IDENTITY, kinds)
        self.assertEqual(report.decision, "FAIL_CLOSED")

    def test_missing_failed_and_stale_evidence_fail_closed(self) -> None:
        report = compare_conformance(
            self.baseline(),
            "profile-v1",
            (observation("stegid", success=False, observed_at="2026-07-15T18:00:00Z"),),
            max_age_seconds=120,
            now=NOW,
        )
        kinds = {finding.kind for finding in report.findings}
        self.assertIn(DriftKind.FAILED_PROBE, kinds)
        self.assertIn(DriftKind.STALE_EVIDENCE, kinds)
        self.assertIn(DriftKind.MISSING_ROLE, kinds)

    def test_duplicate_and_unexpected_roles_are_tampering(self) -> None:
        report = compare_conformance(
            self.baseline(),
            "profile-v1",
            (observation("stegid"), observation("stegid"), observation("custody"), observation("extra")),
            max_age_seconds=120,
            now=NOW,
        )
        tampering = [f for f in report.findings if f.kind is DriftKind.TAMPERING]
        self.assertEqual(len(tampering), 2)

    def test_report_commitment_changes_with_findings(self) -> None:
        good = compare_conformance(self.baseline(), "profile-v1", (observation("stegid"), observation("custody")), max_age_seconds=120, now=NOW)
        bad = compare_conformance(self.baseline(), "profile-v2", (observation("stegid"), observation("custody")), max_age_seconds=120, now=NOW)
        self.assertNotEqual(good.commitment, bad.commitment)


if __name__ == "__main__":
    unittest.main()
