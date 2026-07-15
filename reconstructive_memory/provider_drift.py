from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Iterable


class DriftKind(str, Enum):
    NONE = "none"
    PROFILE = "profile"
    MISSING_ROLE = "missing_role"
    RESOURCE_IDENTITY = "resource_identity"
    CAPABILITY = "capability"
    EVIDENCE = "evidence"
    FAILED_PROBE = "failed_probe"
    STALE_EVIDENCE = "stale_evidence"
    TAMPERING = "tampering"


@dataclass(frozen=True)
class ProviderObservation:
    role: str
    resource: str
    capability: str
    evidence_commitment: str
    observed_at: str
    success: bool = True

    def canonical(self) -> dict[str, object]:
        return {
            "role": self.role,
            "resource": self.resource,
            "capability": self.capability,
            "evidence_commitment": self.evidence_commitment,
            "observed_at": self.observed_at,
            "success": self.success,
        }

    @property
    def commitment(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ConformanceBaseline:
    profile_commitment: str
    observations: tuple[ProviderObservation, ...]
    created_at: str

    def by_role(self) -> dict[str, ProviderObservation]:
        result: dict[str, ProviderObservation] = {}
        for observation in self.observations:
            if observation.role in result:
                raise ValueError(f"duplicate baseline role: {observation.role}")
            result[observation.role] = observation
        return result

    @property
    def commitment(self) -> str:
        payload = {
            "profile_commitment": self.profile_commitment,
            "created_at": self.created_at,
            "observations": [o.canonical() for o in sorted(self.observations, key=lambda o: o.role)],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class DriftFinding:
    role: str
    kind: DriftKind
    detail: str


@dataclass(frozen=True)
class DriftReport:
    baseline_commitment: str
    current_profile_commitment: str
    checked_at: str
    findings: tuple[DriftFinding, ...]

    @property
    def ready(self) -> bool:
        return not self.findings

    @property
    def decision(self) -> str:
        return "ALLOW" if self.ready else "FAIL_CLOSED"

    @property
    def commitment(self) -> str:
        payload = {
            "baseline_commitment": self.baseline_commitment,
            "current_profile_commitment": self.current_profile_commitment,
            "checked_at": self.checked_at,
            "decision": self.decision,
            "findings": [
                {"role": f.role, "kind": f.kind.value, "detail": f.detail}
                for f in self.findings
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def compare_conformance(
    baseline: ConformanceBaseline,
    current_profile_commitment: str,
    current_observations: Iterable[ProviderObservation],
    *,
    max_age_seconds: int,
    now: datetime | None = None,
) -> DriftReport:
    now = now or datetime.now(timezone.utc)
    findings: list[DriftFinding] = []
    baseline_by_role = baseline.by_role()
    current_by_role: dict[str, ProviderObservation] = {}

    if current_profile_commitment != baseline.profile_commitment:
        findings.append(DriftFinding("*", DriftKind.PROFILE, "profile commitment changed"))

    for observation in current_observations:
        if observation.role in current_by_role:
            findings.append(DriftFinding(observation.role, DriftKind.TAMPERING, "duplicate current role"))
            continue
        current_by_role[observation.role] = observation

    for role, expected in baseline_by_role.items():
        actual = current_by_role.get(role)
        if actual is None:
            findings.append(DriftFinding(role, DriftKind.MISSING_ROLE, "current observation missing"))
            continue
        if not actual.success:
            findings.append(DriftFinding(role, DriftKind.FAILED_PROBE, "provider probe failed"))
        if actual.resource != expected.resource:
            findings.append(DriftFinding(role, DriftKind.RESOURCE_IDENTITY, "resource identity changed"))
        if actual.capability != expected.capability:
            findings.append(DriftFinding(role, DriftKind.CAPABILITY, "capability changed"))
        if actual.evidence_commitment != expected.evidence_commitment:
            findings.append(DriftFinding(role, DriftKind.EVIDENCE, "evidence commitment changed"))
        try:
            observed = datetime.fromisoformat(actual.observed_at.replace("Z", "+00:00"))
            age = (now - observed.astimezone(timezone.utc)).total_seconds()
            if age < 0 or age > max_age_seconds:
                findings.append(DriftFinding(role, DriftKind.STALE_EVIDENCE, "observation outside freshness window"))
        except ValueError:
            findings.append(DriftFinding(role, DriftKind.TAMPERING, "invalid observation timestamp"))

    for role in sorted(set(current_by_role) - set(baseline_by_role)):
        findings.append(DriftFinding(role, DriftKind.TAMPERING, "unexpected provider role"))

    return DriftReport(
        baseline_commitment=baseline.commitment,
        current_profile_commitment=current_profile_commitment,
        checked_at=now.isoformat(),
        findings=tuple(findings),
    )
