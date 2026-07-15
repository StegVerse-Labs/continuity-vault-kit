from datetime import datetime, timezone
import unittest

from reconstructive_memory.provider_drift import DriftFinding, DriftKind, DriftReport
from reconstructive_memory.provider_incident import (
    IncidentState,
    open_incident,
    transition_incident,
)


NOW = datetime(2026, 7, 15, 21, 30, tzinfo=timezone.utc)


def drift_report(*, ready: bool = False) -> DriftReport:
    findings = () if ready else (DriftFinding("key-custody", DriftKind.RESOURCE_IDENTITY, "resource changed"),)
    return DriftReport(
        baseline_commitment="b" * 64,
        current_profile_commitment="p" * 64,
        checked_at=NOW.isoformat(),
        findings=findings,
    )


class ProviderIncidentTests(unittest.TestCase):
    def test_incident_opens_only_from_failed_conformance(self) -> None:
        incident = open_incident(drift_report(), actor="monitor", now=NOW)
        self.assertEqual(IncidentState.DETECTED, incident.state)
        self.assertTrue(incident.blocks_readiness)
        with self.assertRaises(ValueError):
            open_incident(drift_report(ready=True), actor="monitor", now=NOW)

    def test_incident_requires_ordered_fail_closed_transitions(self) -> None:
        incident = open_incident(drift_report(), actor="monitor", now=NOW)
        with self.assertRaises(ValueError):
            transition_incident(
                incident,
                IncidentState.RESOLVED,
                actor="operator",
                evidence_commitment="e" * 64,
                now=NOW,
            )
        for state in (
            IncidentState.QUARANTINED,
            IncidentState.REVOKED,
            IncidentState.REMEDIATING,
            IncidentState.REATTESTING,
        ):
            incident = transition_incident(
                incident,
                state,
                actor="operator",
                evidence_commitment=state.value * 8,
                now=NOW,
            )
        self.assertTrue(incident.blocks_readiness)

    def test_resolution_requires_successor_baseline_and_receipt(self) -> None:
        incident = open_incident(drift_report(), actor="monitor", now=NOW)
        for state in (
            IncidentState.QUARANTINED,
            IncidentState.REVOKED,
            IncidentState.REMEDIATING,
            IncidentState.REATTESTING,
        ):
            incident = transition_incident(
                incident,
                state,
                actor="operator",
                evidence_commitment="e" * 64,
                now=NOW,
            )
        with self.assertRaises(ValueError):
            transition_incident(
                incident,
                IncidentState.RESOLVED,
                actor="operator",
                evidence_commitment="r" * 64,
                now=NOW,
            )
        resolved = transition_incident(
            incident,
            IncidentState.RESOLVED,
            actor="operator",
            evidence_commitment="r" * 64,
            successor_baseline_commitment="n" * 64,
            successor_receipt_commitment="s" * 64,
            now=NOW,
        )
        self.assertFalse(resolved.blocks_readiness)
        self.assertEqual("n" * 64, resolved.successor_baseline_commitment)
        self.assertEqual("s" * 64, resolved.successor_receipt_commitment)

    def test_failed_reattest_returns_to_remediation(self) -> None:
        incident = open_incident(drift_report(), actor="monitor", now=NOW)
        for state in (
            IncidentState.QUARANTINED,
            IncidentState.REVOKED,
            IncidentState.REMEDIATING,
            IncidentState.REATTESTING,
            IncidentState.REMEDIATING,
        ):
            incident = transition_incident(
                incident,
                state,
                actor="operator",
                evidence_commitment="e" * 64,
                now=NOW,
            )
        self.assertEqual(IncidentState.REMEDIATING, incident.state)
        self.assertTrue(incident.blocks_readiness)


if __name__ == "__main__":
    unittest.main()
