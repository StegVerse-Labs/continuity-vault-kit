from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence

from .core import ChainEvent, ProtectedObject


class ContentProtector(Protocol):
    def protect(self, *, content_ref: str, plaintext: str, pair_id: str, policy_ref: str) -> ProtectedObject:
        """Encrypt and bind approved plaintext outside the continuity chain."""


@dataclass(frozen=True)
class ChatObservation:
    observation_id: str
    event_type: str
    plaintext: str
    approved: bool
    retention_class: str
    dependencies: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    time_bucket: str | None = None


@dataclass(frozen=True)
class IngestionResult:
    event: ChainEvent
    protected_object: ProtectedObject | None


class EcosystemChatIngestor:
    """Convert an approved chat observation into a minimal chain event.

    Raw chat content is never copied into ChainEvent. A caller-supplied minimizer
    determines whether content is retained, and a protector owns encryption.
    """

    def __init__(
        self,
        *,
        pair_id: str,
        policy_ref: str,
        authority_ref: str,
        minimizer: Callable[[ChatObservation], str | None],
        protector: ContentProtector,
    ) -> None:
        self._pair_id = pair_id
        self._policy_ref = policy_ref
        self._authority_ref = authority_ref
        self._minimizer = minimizer
        self._protector = protector

    def ingest(
        self,
        observation: ChatObservation,
        *,
        sequence: int,
        previous_event_hash: str | None,
    ) -> IngestionResult:
        if not observation.approved:
            raise PermissionError("chat observation was not user-approved for durable continuity")
        if observation.retention_class not in {"integrity-only", "reconstructable", "full-fidelity"}:
            raise ValueError("unsupported retention class")

        minimized = self._minimizer(observation)
        protected: ProtectedObject | None = None
        content_ref: str | None = None
        content_commitment: str | None = None

        if observation.retention_class == "integrity-only":
            minimized = None
        elif minimized:
            content_ref = f"vault://protected/chat/{observation.observation_id}"
            protected = self._protector.protect(
                content_ref=content_ref,
                plaintext=minimized,
                pair_id=self._pair_id,
                policy_ref=self._policy_ref,
            )
            content_commitment = protected.plaintext_commitment
        else:
            raise ValueError("reconstructable content requires a nonempty minimized representation")

        event = ChainEvent(
            event_id=observation.observation_id,
            sequence=sequence,
            event_type=observation.event_type,
            pair_id=self._pair_id,
            content_ref=content_ref,
            content_commitment=content_commitment,
            policy_ref=self._policy_ref,
            authority_ref=self._authority_ref,
            retention_class=observation.retention_class,
            previous_event_hash=previous_event_hash,
            dependencies=observation.dependencies,
            supersedes=observation.supersedes,
            time_bucket=observation.time_bucket,
        ).with_hash()
        event.verify()
        return IngestionResult(event=event, protected_object=protected)
