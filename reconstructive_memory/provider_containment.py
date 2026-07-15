from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable


class ContainmentAction(str, Enum):
    DISABLE_KMS_KEY = "disable_kms_key"
    FREEZE_STATE_WRITES = "freeze_state_writes"
    SUSPEND_SPIFFE_IDENTITY = "suspend_spiffe_identity"
    QUARANTINE_CHAT_ENDPOINT = "quarantine_chat_endpoint"
    QUARANTINE_MASTER_RECORDS_ENDPOINT = "quarantine_master_records_endpoint"


class ActionStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class ContainmentCommand:
    incident_commitment: str
    role: str
    action: ContainmentAction
    resource: str
    reason_commitment: str

    def canonical(self) -> dict[str, str]:
        return {
            "incident_commitment": self.incident_commitment,
            "role": self.role,
            "action": self.action.value,
            "resource": self.resource,
            "reason_commitment": self.reason_commitment,
        }

    @property
    def commitment(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ContainmentReceipt:
    command_commitment: str
    status: ActionStatus
    actor: str
    evidence_commitment: str
    observed_at: str

    def __post_init__(self) -> None:
        if not self.actor:
            raise ValueError("actor is required")
        if not self.evidence_commitment:
            raise ValueError("evidence commitment is required")

    def canonical(self) -> dict[str, str]:
        return {
            "command_commitment": self.command_commitment,
            "status": self.status.value,
            "actor": self.actor,
            "evidence_commitment": self.evidence_commitment,
            "observed_at": self.observed_at,
        }

    @property
    def commitment(self) -> str:
        raw = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ContainmentPlan:
    incident_commitment: str
    commands: tuple[ContainmentCommand, ...]

    def __post_init__(self) -> None:
        seen: set[tuple[str, ContainmentAction]] = set()
        for command in self.commands:
            if command.incident_commitment != self.incident_commitment:
                raise ValueError("command incident commitment mismatch")
            key = (command.role, command.action)
            if key in seen:
                raise ValueError(f"duplicate containment command: {command.role}/{command.action.value}")
            seen.add(key)

    @property
    def commitment(self) -> str:
        payload = {
            "incident_commitment": self.incident_commitment,
            "commands": [c.canonical() for c in sorted(self.commands, key=lambda c: (c.role, c.action.value))],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def evaluate(self, receipts: Iterable[ContainmentReceipt]) -> str:
        by_command: dict[str, ContainmentReceipt] = {}
        for receipt in receipts:
            if receipt.command_commitment in by_command:
                return "FAIL_CLOSED"
            by_command[receipt.command_commitment] = receipt
        for command in self.commands:
            receipt = by_command.get(command.commitment)
            if receipt is None or receipt.status is not ActionStatus.APPLIED:
                return "FAIL_CLOSED"
        if set(by_command) != {c.commitment for c in self.commands}:
            return "FAIL_CLOSED"
        return "CONTAINED"


def build_default_plan(incident_commitment: str, role_resources: dict[str, str], reason_commitment: str) -> ContainmentPlan:
    action_by_role = {
        "stegid-signature": ContainmentAction.DISABLE_KMS_KEY,
        "key-custody": ContainmentAction.DISABLE_KMS_KEY,
        "replicated-state": ContainmentAction.FREEZE_STATE_WRITES,
        "ai-entity-attestation": ContainmentAction.SUSPEND_SPIFFE_IDENTITY,
        "ecosystem-chat": ContainmentAction.QUARANTINE_CHAT_ENDPOINT,
        "master-records": ContainmentAction.QUARANTINE_MASTER_RECORDS_ENDPOINT,
    }
    commands: list[ContainmentCommand] = []
    for role, action in action_by_role.items():
        resource = role_resources.get(role)
        if not resource:
            raise ValueError(f"missing resource for role: {role}")
        commands.append(
            ContainmentCommand(
                incident_commitment=incident_commitment,
                role=role,
                action=action,
                resource=resource,
                reason_commitment=reason_commitment,
            )
        )
    return ContainmentPlan(incident_commitment=incident_commitment, commands=tuple(commands))
