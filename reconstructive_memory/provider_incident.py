from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json

from .provider_drift import DriftReport


class IncidentState(str, Enum):
    DETECTED = "detected"
    QUARANTINED = "quarantined"
    REVOKED = "revoked"
    REMEDIATING = "remediating"
    REATTESTING = "reattesting"
    RESOLVED = "resolved"


_ALLOWED_TRANSITIONS = {
    IncidentState.DETECTED: {IncidentState.QUARANTINED},
    IncidentState.QUARANTINED: {IncidentState.REVOKED},
    IncidentState.REVOKED: {IncidentState.REMEDIATING},
    IncidentState.REMEDIATING: {IncidentState.REATTESTING},
    IncidentState.REATTESTING: {IncidentState.RESOLVED, IncidentState.REMEDIATING},
    IncidentState.RESOLVED: set(),
}


@dataclass(frozen=True)
class IncidentEvent:
    state: IncidentState
    actor: str
    occurred_at: str
    evidence_commitment: str
    note: str = ""

    def canonical(self) -> dict[str, str]:
        return {
            "state": self.state.value,
            "actor": self.actor,
            "occurred_at": self.occurred_at,
            "evidence_commitment": self.evidence_commitment,
            "note": self.note,
        }


@dataclass(frozen=True)
class ProviderIncident:
    incident_id: str
    baseline_commitment: str
    drift_report_commitment: str
    opened_at: str
    events: tuple[IncidentEvent, ...]
    successor_baseline_commitment: str = ""
    successor_receipt_commitment: str = ""

    @property
    def state(self) -> IncidentState:
        if not self.events:
            raise ValueError("incident requires at least one event")
        return self.events[-1].state

    @property
    def blocks_readiness(self) -> bool:
        return self.state is not IncidentState.RESOLVED

    @property
    def commitment(self) -> str:
        payload = {
            "incident_id": self.incident_id,
            "baseline_commitment": self.baseline_commitment,
            "drift_report_commitment": self.drift_report_commitment,
            "opened_at": self.opened_at,
            "events": [event.canonical() for event in self.events],
            "successor_baseline_commitment": self.successor_baseline_commitment,
            "successor_receipt_commitment": self.successor_receipt_commitment,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def open_incident(report: DriftReport, *, actor: str, now: datetime | None = None) -> ProviderIncident:
    if report.ready:
        raise ValueError("cannot open incident from an ALLOW drift report")
    now = now or datetime.now(timezone.utc)
    opened_at = now.isoformat()
    incident_id = hashlib.sha256(
        f"{report.baseline_commitment}:{report.commitment}:{opened_at}".encode()
    ).hexdigest()
    event = IncidentEvent(
        state=IncidentState.DETECTED,
        actor=actor,
        occurred_at=opened_at,
        evidence_commitment=report.commitment,
        note="provider conformance drift detected",
    )
    return ProviderIncident(
        incident_id=incident_id,
        baseline_commitment=report.baseline_commitment,
        drift_report_commitment=report.commitment,
        opened_at=opened_at,
        events=(event,),
    )


def transition_incident(
    incident: ProviderIncident,
    new_state: IncidentState,
    *,
    actor: str,
    evidence_commitment: str,
    note: str = "",
    successor_baseline_commitment: str = "",
    successor_receipt_commitment: str = "",
    now: datetime | None = None,
) -> ProviderIncident:
    if new_state not in _ALLOWED_TRANSITIONS[incident.state]:
        raise ValueError(f"invalid incident transition: {incident.state.value}->{new_state.value}")
    if not actor or not evidence_commitment:
        raise ValueError("actor and evidence commitment are required")
    if new_state is IncidentState.RESOLVED:
        if incident.state is not IncidentState.REATTESTING:
            raise ValueError("incident can resolve only after re-attestation")
        if not successor_baseline_commitment or not successor_receipt_commitment:
            raise ValueError("resolution requires successor baseline and deployment receipt")
    else:
        if successor_baseline_commitment or successor_receipt_commitment:
            raise ValueError("successor commitments are valid only on resolution")

    now = now or datetime.now(timezone.utc)
    event = IncidentEvent(
        state=new_state,
        actor=actor,
        occurred_at=now.isoformat(),
        evidence_commitment=evidence_commitment,
        note=note,
    )
    return replace(
        incident,
        events=incident.events + (event,),
        successor_baseline_commitment=successor_baseline_commitment,
        successor_receipt_commitment=successor_receipt_commitment,
    )
