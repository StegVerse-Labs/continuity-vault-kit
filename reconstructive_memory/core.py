from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import hmac
import json
from typing import Callable, Iterable, Mapping, Sequence


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


def compute_pair_id(
    steg_id_public_identifier: str,
    entity_public_identifier: str,
    vault_id: str,
    relationship_epoch: int,
) -> str:
    """Return a non-secret relationship identifier.

    The pair ID is suitable for chain routing and policy lookup. It is never a
    decryption key and must not be treated as one.
    """
    if relationship_epoch < 1:
        raise ValueError("relationship_epoch must be positive")
    return _digest(
        {
            "steg_id": steg_id_public_identifier,
            "entity_id": entity_public_identifier,
            "vault_id": vault_id,
            "relationship_epoch": relationship_epoch,
        }
    )


@dataclass(frozen=True)
class AuthorizationContext:
    pair_id: str
    user_proof: str
    entity_proof: str
    policy_ref: str
    relationship_epoch: int
    capability_id: str

    def validate(self, expected_pair_id: str, expected_policy_ref: str) -> None:
        if not hmac.compare_digest(self.pair_id, expected_pair_id):
            raise PermissionError("pair binding mismatch")
        if self.policy_ref != expected_policy_ref:
            raise PermissionError("policy binding mismatch")
        if self.relationship_epoch < 1:
            raise PermissionError("invalid relationship epoch")
        if not self.user_proof or not self.entity_proof or not self.capability_id:
            raise PermissionError("dual proof and capability are required")


@dataclass(frozen=True)
class ChainEvent:
    event_id: str
    sequence: int
    event_type: str
    pair_id: str
    content_ref: str | None
    content_commitment: str | None
    policy_ref: str
    authority_ref: str
    retention_class: str
    previous_event_hash: str | None
    dependencies: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    time_bucket: str | None = None
    event_hash: str = field(default="")

    def payload(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "pair_id": self.pair_id,
            "content_ref": self.content_ref,
            "content_commitment": self.content_commitment,
            "policy_ref": self.policy_ref,
            "authority_ref": self.authority_ref,
            "retention_class": self.retention_class,
            "previous_event_hash": self.previous_event_hash,
            "dependencies": list(self.dependencies),
            "supersedes": list(self.supersedes),
            "time_bucket": self.time_bucket,
        }

    def with_hash(self) -> "ChainEvent":
        return ChainEvent(**self.payload(), event_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.sequence < 1:
            raise ValueError("sequence must be positive")
        if self.retention_class not in {"integrity-only", "reconstructable", "full-fidelity"}:
            raise ValueError("unsupported retention class")
        expected = _digest(self.payload())
        if not self.event_hash or not hmac.compare_digest(self.event_hash, expected):
            raise ValueError(f"event hash mismatch: {self.event_id}")


@dataclass(frozen=True)
class ProtectedObject:
    content_ref: str
    pair_id: str
    policy_ref: str
    ciphertext: bytes
    plaintext_commitment: str
    retention_class: str = "reconstructable"


@dataclass(frozen=True)
class ReconstructionResult:
    event_ids: tuple[str, ...]
    plaintext_sections: tuple[str, ...]
    event_range_commitment: str
    plaintext_retained: bool = False
    workspace_destroyed: bool = True


class EphemeralReconstructor:
    """Reconstruct the smallest dependency-complete event subgraph.

    `decrypt` is injected so production code can use a hardware-backed or
    threshold key service. This prototype never derives keys from public hashes.
    """

    def __init__(
        self,
        events: Iterable[ChainEvent],
        objects: Mapping[str, ProtectedObject],
        decrypt: Callable[[ProtectedObject, AuthorizationContext], str],
    ) -> None:
        self._events = {event.event_id: event for event in events}
        self._objects = dict(objects)
        self._decrypt = decrypt
        self._validate_chain()

    def _validate_chain(self) -> None:
        ordered = sorted(self._events.values(), key=lambda event: event.sequence)
        seen_ids: set[str] = set()
        prior_hash: str | None = None
        prior_sequence = 0
        for event in ordered:
            event.verify()
            if event.event_id in seen_ids:
                raise ValueError(f"duplicate event id: {event.event_id}")
            if event.sequence <= prior_sequence:
                raise ValueError("event sequence is not strictly increasing")
            if event.previous_event_hash != prior_hash:
                raise ValueError(f"chain link mismatch: {event.event_id}")
            seen_ids.add(event.event_id)
            prior_hash = event.event_hash
            prior_sequence = event.sequence

    def _closure(self, target_event_ids: Sequence[str]) -> list[ChainEvent]:
        required: set[str] = set()
        stack = list(target_event_ids)
        while stack:
            event_id = stack.pop()
            if event_id in required:
                continue
            try:
                event = self._events[event_id]
            except KeyError as exc:
                raise KeyError(f"unknown event: {event_id}") from exc
            required.add(event_id)
            stack.extend(event.dependencies)
            stack.extend(event.supersedes)
        return sorted((self._events[event_id] for event_id in required), key=lambda event: event.sequence)

    def reconstruct(
        self,
        target_event_ids: Sequence[str],
        auth: AuthorizationContext,
        *,
        max_events: int = 32,
    ) -> ReconstructionResult:
        if not target_event_ids:
            raise ValueError("at least one target event is required")
        selected = self._closure(target_event_ids)
        if len(selected) > max_events:
            raise ValueError("reconstruction exceeds bounded event window")

        pair_ids = {event.pair_id for event in selected}
        policy_refs = {event.policy_ref for event in selected}
        if len(pair_ids) != 1 or len(policy_refs) != 1:
            raise PermissionError("mixed pair or policy reconstruction is forbidden")
        auth.validate(next(iter(pair_ids)), next(iter(policy_refs)))

        plaintext_sections: list[str] = []
        for event in selected:
            if event.retention_class == "integrity-only" or event.content_ref is None:
                continue
            protected = self._objects.get(event.content_ref)
            if protected is None:
                raise FileNotFoundError(f"protected object unavailable: {event.content_ref}")
            if protected.pair_id != event.pair_id or protected.policy_ref != event.policy_ref:
                raise PermissionError("protected object binding mismatch")
            plaintext = self._decrypt(protected, auth)
            if event.content_commitment and not hmac.compare_digest(_digest(plaintext), event.content_commitment):
                raise ValueError(f"content commitment mismatch: {event.event_id}")
            if not hmac.compare_digest(_digest(plaintext), protected.plaintext_commitment):
                raise ValueError(f"protected object commitment mismatch: {event.content_ref}")
            plaintext_sections.append(plaintext)

        event_ids = tuple(event.event_id for event in selected)
        event_range_commitment = _digest(
            {
                "event_ids": event_ids,
                "event_hashes": [event.event_hash for event in selected],
                "pair_id": auth.pair_id,
                "policy_ref": auth.policy_ref,
            }
        )
        return ReconstructionResult(
            event_ids=event_ids,
            plaintext_sections=tuple(plaintext_sections),
            event_range_commitment=event_range_commitment,
        )
