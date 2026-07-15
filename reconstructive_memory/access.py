from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from typing import Callable, Mapping, Protocol, Sequence

from .core import AuthorizationContext, ReconstructionResult


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class RelationshipState:
    pair_id: str
    relationship_epoch: int
    policy_ref: str
    status: str = "active"
    successor_pair_id: str | None = None

    def validate(self, auth: AuthorizationContext) -> None:
        if self.status != "active":
            raise PermissionError("relationship is not active")
        if auth.relationship_epoch != self.relationship_epoch:
            raise PermissionError("relationship epoch mismatch")
        auth.validate(self.pair_id, self.policy_ref)


class KeyUnwrapper(Protocol):
    def unwrap(self, wrapped_key: bytes, auth: AuthorizationContext, relationship: RelationshipState) -> bytes:
        """Return key material only after external proof and policy validation."""


@dataclass(frozen=True)
class CallableKeyUnwrapper:
    operation: Callable[[bytes, AuthorizationContext, RelationshipState], bytes]

    def unwrap(self, wrapped_key: bytes, auth: AuthorizationContext, relationship: RelationshipState) -> bytes:
        relationship.validate(auth)
        key = self.operation(wrapped_key, auth, relationship)
        if not isinstance(key, bytes) or not key:
            raise PermissionError("key unwrapping did not return key material")
        return key


class RelationshipRegistry:
    def __init__(self, relationships: Sequence[RelationshipState]) -> None:
        self._states = {(state.pair_id, state.relationship_epoch): state for state in relationships}

    def resolve(self, auth: AuthorizationContext) -> RelationshipState:
        state = self._states.get((auth.pair_id, auth.relationship_epoch))
        if state is None:
            raise PermissionError("relationship epoch is unknown")
        state.validate(auth)
        return state

    def revoke(self, pair_id: str, relationship_epoch: int, *, successor_pair_id: str | None = None) -> "RelationshipRegistry":
        key = (pair_id, relationship_epoch)
        if key not in self._states:
            raise KeyError("relationship epoch is unknown")
        updated = dict(self._states)
        current = updated[key]
        updated[key] = RelationshipState(
            pair_id=current.pair_id,
            relationship_epoch=current.relationship_epoch,
            policy_ref=current.policy_ref,
            status="revoked",
            successor_pair_id=successor_pair_id,
        )
        return RelationshipRegistry(tuple(updated.values()))


@dataclass(frozen=True)
class AccessReceipt:
    receipt_id: str
    pair_id: str
    relationship_epoch: int
    policy_ref: str
    capability_commitment: str
    request_commitment: str
    event_range_commitment: str
    event_count: int
    result_class: str = "ephemeral_reconstruction"
    plaintext_retained: bool = False
    workspace_destroyed: bool = True
    receipt_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "pair_id": self.pair_id,
            "relationship_epoch": self.relationship_epoch,
            "policy_ref": self.policy_ref,
            "capability_commitment": self.capability_commitment,
            "request_commitment": self.request_commitment,
            "event_range_commitment": self.event_range_commitment,
            "event_count": self.event_count,
            "result_class": self.result_class,
            "plaintext_retained": self.plaintext_retained,
            "workspace_destroyed": self.workspace_destroyed,
        }

    def with_hash(self) -> "AccessReceipt":
        return AccessReceipt(**self.payload(), receipt_hash=_digest(self.payload()))

    def verify(self) -> None:
        expected = _digest(self.payload())
        if not self.receipt_hash or not hmac.compare_digest(self.receipt_hash, expected):
            raise ValueError("access receipt hash mismatch")
        if self.event_count < 1:
            raise ValueError("access receipt must cover at least one event")
        if self.plaintext_retained:
            raise ValueError("default access receipt cannot claim plaintext retention")


def make_access_receipt(
    *,
    receipt_id: str,
    auth: AuthorizationContext,
    request_descriptor: Mapping[str, object],
    result: ReconstructionResult,
) -> AccessReceipt:
    receipt = AccessReceipt(
        receipt_id=receipt_id,
        pair_id=auth.pair_id,
        relationship_epoch=auth.relationship_epoch,
        policy_ref=auth.policy_ref,
        capability_commitment=_digest(auth.capability_id),
        request_commitment=_digest(request_descriptor),
        event_range_commitment=result.event_range_commitment,
        event_count=len(result.event_ids),
        plaintext_retained=result.plaintext_retained,
        workspace_destroyed=result.workspace_destroyed,
    ).with_hash()
    receipt.verify()
    return receipt
