from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from typing import Mapping, Sequence

from .core import AuthorizationContext, ChainEvent, ProtectedObject


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class CapabilityGrant:
    capability_id: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    issued_at: int
    expires_at: int
    nonce: str
    max_uses: int = 1
    use_count: int = 0
    revoked: bool = False

    def validate(self, auth: AuthorizationContext, *, now: int) -> None:
        if self.revoked:
            raise PermissionError("capability is revoked")
        if now < self.issued_at:
            raise PermissionError("capability is not active yet")
        if now >= self.expires_at:
            raise PermissionError("capability has expired")
        if self.use_count >= self.max_uses:
            raise PermissionError("capability use limit exhausted")
        if not self.nonce:
            raise PermissionError("capability nonce is required")
        if not hmac.compare_digest(self.capability_id, auth.capability_id):
            raise PermissionError("capability identifier mismatch")
        auth.validate(self.pair_id, self.policy_ref)
        if auth.relationship_epoch != self.relationship_epoch:
            raise PermissionError("capability relationship epoch mismatch")

    def consume(self, auth: AuthorizationContext, *, now: int) -> "CapabilityGrant":
        self.validate(auth, now=now)
        return replace(self, use_count=self.use_count + 1)

    def revoke(self) -> "CapabilityGrant":
        return replace(self, revoked=True)

    @property
    def commitment(self) -> str:
        return _digest(
            {
                "capability_id": self.capability_id,
                "pair_id": self.pair_id,
                "policy_ref": self.policy_ref,
                "relationship_epoch": self.relationship_epoch,
                "issued_at": self.issued_at,
                "expires_at": self.expires_at,
                "nonce": self.nonce,
                "max_uses": self.max_uses,
            }
        )


@dataclass(frozen=True)
class ObjectLifecycleState:
    content_ref: str
    pair_id: str
    policy_ref: str
    status: str = "active"
    lifecycle_epoch: int = 1
    tombstone_commitment: str | None = None

    def validate_reconstructable(self, protected: ProtectedObject) -> None:
        if self.status != "active":
            raise FileNotFoundError("protected content is no longer reconstructable")
        if protected.content_ref != self.content_ref:
            raise ValueError("protected object reference mismatch")
        if protected.pair_id != self.pair_id or protected.policy_ref != self.policy_ref:
            raise PermissionError("protected object lifecycle binding mismatch")

    def tombstone(self, *, reason_code: str, deletion_receipt_ref: str) -> "ObjectLifecycleState":
        if self.status != "active":
            raise ValueError("protected object is already inactive")
        commitment = _digest(
            {
                "content_ref": self.content_ref,
                "pair_id": self.pair_id,
                "policy_ref": self.policy_ref,
                "lifecycle_epoch": self.lifecycle_epoch,
                "reason_code": reason_code,
                "deletion_receipt_ref": deletion_receipt_ref,
            }
        )
        return replace(
            self,
            status="tombstoned",
            lifecycle_epoch=self.lifecycle_epoch + 1,
            tombstone_commitment=commitment,
        )


class ObjectLifecycleRegistry:
    def __init__(self, states: Sequence[ObjectLifecycleState]) -> None:
        self._states = {state.content_ref: state for state in states}

    def resolve(self, protected: ProtectedObject) -> ObjectLifecycleState:
        state = self._states.get(protected.content_ref)
        if state is None:
            raise FileNotFoundError("protected object lifecycle state is unknown")
        state.validate_reconstructable(protected)
        return state

    def tombstone(
        self,
        content_ref: str,
        *,
        reason_code: str,
        deletion_receipt_ref: str,
    ) -> "ObjectLifecycleRegistry":
        state = self._states.get(content_ref)
        if state is None:
            raise KeyError("protected object lifecycle state is unknown")
        updated = dict(self._states)
        updated[content_ref] = state.tombstone(
            reason_code=reason_code,
            deletion_receipt_ref=deletion_receipt_ref,
        )
        return ObjectLifecycleRegistry(tuple(updated.values()))

    def state(self, content_ref: str) -> ObjectLifecycleState:
        try:
            return self._states[content_ref]
        except KeyError as exc:
            raise KeyError("protected object lifecycle state is unknown") from exc


def make_tombstone_event(
    *,
    event_id: str,
    sequence: int,
    pair_id: str,
    policy_ref: str,
    authority_ref: str,
    previous_event_hash: str | None,
    content_ref: str,
    tombstone_commitment: str,
    dependencies: Sequence[str] = (),
) -> ChainEvent:
    return ChainEvent(
        event_id=event_id,
        sequence=sequence,
        event_type="protected_object_tombstoned",
        pair_id=pair_id,
        content_ref=None,
        content_commitment=tombstone_commitment,
        policy_ref=policy_ref,
        authority_ref=authority_ref,
        retention_class="integrity-only",
        previous_event_hash=previous_event_hash,
        dependencies=tuple(dependencies),
        supersedes=(),
        time_bucket=None,
    ).with_hash()
