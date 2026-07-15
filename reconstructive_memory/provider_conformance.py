from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from typing import Mapping, Protocol, Sequence

from .provider_activation import DeploymentReceipt, ProductionActivationProfile


REQUIRED_ROLES = (
    "stegid_verification",
    "ai_entity_attestation",
    "key_custody",
    "replicated_state",
    "ecosystem_chat",
    "master_records",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ProviderProbeResult:
    role: str
    resource_id: str
    observed_identity: str
    capability: str
    success: bool
    evidence_commitment: str
    checked_at: int
    failure_code: str | None = None
    result_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "role": self.role,
            "resource_id": self.resource_id,
            "observed_identity": self.observed_identity,
            "capability": self.capability,
            "success": self.success,
            "evidence_commitment": self.evidence_commitment,
            "checked_at": self.checked_at,
            "failure_code": self.failure_code,
        }

    def with_hash(self) -> "ProviderProbeResult":
        return replace(self, result_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.role not in REQUIRED_ROLES:
            raise ValueError("unsupported provider role")
        if not self.resource_id or self.resource_id == "UNCONFIGURED":
            raise ValueError("probe lacks configured resource")
        if not self.observed_identity or not self.capability:
            raise ValueError("probe lacks observed identity or capability")
        if not self.evidence_commitment.startswith("sha256:"):
            raise ValueError("probe lacks evidence commitment")
        if self.checked_at <= 0:
            raise ValueError("invalid probe timestamp")
        if self.success and self.failure_code is not None:
            raise ValueError("successful probe carries failure code")
        if not self.success and not self.failure_code:
            raise ValueError("failed probe lacks failure code")
        expected = _digest(self.payload())
        if not self.result_hash or not hmac.compare_digest(self.result_hash, expected):
            raise ValueError("provider probe hash mismatch")


class ProviderProbe(Protocol):
    def run(self, profile: ProductionActivationProfile, *, checked_at: int) -> ProviderProbeResult: ...


@dataclass(frozen=True)
class ConformanceReport:
    profile_commitment: str
    results: tuple[ProviderProbeResult, ...]
    ready: bool
    report_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "profile_commitment": self.profile_commitment,
            "results": [result.result_hash for result in self.results],
            "ready": self.ready,
        }

    def with_hash(self) -> "ConformanceReport":
        return replace(self, report_hash=_digest(self.payload()))

    def verify(self) -> None:
        roles = [result.role for result in self.results]
        if sorted(roles) != sorted(REQUIRED_ROLES) or len(set(roles)) != len(REQUIRED_ROLES):
            raise ValueError("conformance report must contain exactly one result per role")
        for result in self.results:
            result.verify()
        expected_ready = all(result.success for result in self.results)
        if self.ready != expected_ready:
            raise ValueError("conformance readiness mismatch")
        expected = _digest(self.payload())
        if not self.report_hash or not hmac.compare_digest(self.report_hash, expected):
            raise ValueError("conformance report hash mismatch")


def run_provider_conformance(
    profile: ProductionActivationProfile,
    probes: Sequence[ProviderProbe],
    *,
    checked_at: int,
) -> ConformanceReport:
    profile.verify()
    if len(probes) != len(REQUIRED_ROLES):
        raise ValueError("one probe is required for every provider role")
    results = tuple(probe.run(profile, checked_at=checked_at) for probe in probes)
    report = ConformanceReport(
        profile_commitment=profile.profile_hash,
        results=results,
        ready=all(result.success for result in results),
    ).with_hash()
    report.verify()
    return report


def assemble_deployment_receipt(
    profile: ProductionActivationProfile,
    report: ConformanceReport,
    *,
    receipt_id: str,
    issued_at: int,
    signer_identity: str,
) -> DeploymentReceipt:
    profile.verify()
    report.verify()
    if not report.ready:
        raise PermissionError("provider conformance is not ready")
    if not hmac.compare_digest(report.profile_commitment, profile.profile_hash):
        raise PermissionError("conformance report belongs to another profile")
    evidence = {result.role: result.evidence_commitment for result in report.results}
    receipt = DeploymentReceipt(
        receipt_id=receipt_id,
        profile_hash=profile.profile_hash,
        issued_at=issued_at,
        signer_identity=signer_identity,
        evidence_commitments=evidence,
        validation_commitment=report.report_hash,
    ).with_hash()
    receipt.verify(profile)
    return receipt
