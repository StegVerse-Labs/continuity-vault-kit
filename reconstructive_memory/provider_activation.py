from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from typing import Mapping


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ProviderSelection:
    role: str
    provider: str
    service: str
    identity_ref: str
    region: str
    status: str = "selected"

    def verify(self) -> None:
        if self.status not in {"selected", "configured", "verified", "revoked"}:
            raise ValueError("unsupported provider status")
        if not all((self.role, self.provider, self.service, self.identity_ref, self.region)):
            raise ValueError("provider selection is incomplete")


@dataclass(frozen=True)
class ProductionActivationProfile:
    profile_id: str
    environment: str
    steg_id: ProviderSelection
    ai_attestation: ProviderSelection
    key_custody: ProviderSelection
    state_store: ProviderSelection
    chat_transport: ProviderSelection
    master_records: ProviderSelection
    rollback_ref: str
    created_at: int
    profile_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "profile_id": self.profile_id,
            "environment": self.environment,
            "providers": {
                key: vars(value)
                for key, value in {
                    "steg_id": self.steg_id,
                    "ai_attestation": self.ai_attestation,
                    "key_custody": self.key_custody,
                    "state_store": self.state_store,
                    "chat_transport": self.chat_transport,
                    "master_records": self.master_records,
                }.items()
            },
            "rollback_ref": self.rollback_ref,
            "created_at": self.created_at,
        }

    def with_hash(self) -> "ProductionActivationProfile":
        return replace(self, profile_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.environment not in {"development", "staging", "production"}:
            raise ValueError("unsupported activation environment")
        if not self.profile_id or not self.rollback_ref or self.created_at < 1:
            raise ValueError("activation profile identity is incomplete")
        for selection in (
            self.steg_id,
            self.ai_attestation,
            self.key_custody,
            self.state_store,
            self.chat_transport,
            self.master_records,
        ):
            selection.verify()
        expected = _digest(self.payload())
        if not self.profile_hash or not hmac.compare_digest(self.profile_hash, expected):
            raise ValueError("activation profile hash mismatch")

    def activation_ready(self) -> bool:
        self.verify()
        return all(
            selection.status == "verified"
            for selection in (
                self.steg_id,
                self.ai_attestation,
                self.key_custody,
                self.state_store,
                self.chat_transport,
                self.master_records,
            )
        )


@dataclass(frozen=True)
class DeploymentReceipt:
    receipt_id: str
    profile_hash: str
    validation_commit: str
    rollback_ref: str
    provider_evidence: Mapping[str, str]
    issued_at: int
    decision: str
    receipt_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "profile_hash": self.profile_hash,
            "validation_commit": self.validation_commit,
            "rollback_ref": self.rollback_ref,
            "provider_evidence": dict(sorted(self.provider_evidence.items())),
            "issued_at": self.issued_at,
            "decision": self.decision,
        }

    def with_hash(self) -> "DeploymentReceipt":
        return replace(self, receipt_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.decision not in {"ALLOW", "DENY", "FAIL_CLOSED"}:
            raise ValueError("unsupported deployment decision")
        if not self.receipt_id or not self.profile_hash or not self.validation_commit or not self.rollback_ref:
            raise ValueError("deployment receipt is incomplete")
        if self.issued_at < 1 or len(self.provider_evidence) != 6:
            raise ValueError("deployment receipt evidence is incomplete")
        expected = _digest(self.payload())
        if not self.receipt_hash or not hmac.compare_digest(self.receipt_hash, expected):
            raise ValueError("deployment receipt hash mismatch")


def default_aws_profile(*, created_at: int) -> ProductionActivationProfile:
    """Concrete provider selection. Resource identifiers remain placeholders until provisioned."""
    return ProductionActivationProfile(
        profile_id="reconstructive-memory-aws-v1",
        environment="staging",
        steg_id=ProviderSelection("steg-id-signature", "AWS", "KMS asymmetric verify", "kms-key-arn:UNCONFIGURED", "us-east-1"),
        ai_attestation=ProviderSelection("ai-entity-attestation", "SPIFFE", "SPIRE X.509-SVID", "spiffe-id:UNCONFIGURED", "global"),
        key_custody=ProviderSelection("key-custody", "AWS", "KMS customer-managed key", "kms-key-arn:UNCONFIGURED", "us-east-1"),
        state_store=ProviderSelection("replicated-state", "AWS", "DynamoDB conditional write", "table-arn:UNCONFIGURED", "us-east-1"),
        chat_transport=ProviderSelection("ecosystem-chat", "StegVerse", "authenticated chat endpoint", "endpoint:UNCONFIGURED", "global"),
        master_records=ProviderSelection("master-records", "StegVerse", "receipt ingestion endpoint", "endpoint:UNCONFIGURED", "global"),
        rollback_ref="docs/PRODUCTION_PROVIDER_ACTIVATION.md#rollback-and-revocation",
        created_at=created_at,
    ).with_hash()
