from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from typing import Protocol

from .ingestion import ChatObservation, EcosystemChatIngestor, IngestionResult


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ChatTransportEnvelope:
    envelope_id: str
    source_session_id: str
    sequence: int
    issued_at: int
    expires_at: int
    nonce: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    observation: ChatObservation
    user_approval_proof: str
    transport_proof: str

    def signed_payload(self) -> dict[str, object]:
        return {
            "envelope_id": self.envelope_id,
            "source_session_id": self.source_session_id,
            "sequence": self.sequence,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "pair_id": self.pair_id,
            "policy_ref": self.policy_ref,
            "relationship_epoch": self.relationship_epoch,
            "observation_id": self.observation.observation_id,
            "event_type": self.observation.event_type,
            "retention_class": self.observation.retention_class,
            "approved": self.observation.approved,
            "dependencies": list(self.observation.dependencies),
            "supersedes": list(self.observation.supersedes),
            "time_bucket": self.observation.time_bucket,
            "plaintext_commitment": _digest(self.observation.plaintext),
        }

    @property
    def commitment(self) -> str:
        return _digest(self.signed_payload())


class TransportVerifier(Protocol):
    def verify_user_approval(self, envelope: ChatTransportEnvelope) -> bool:
        """Verify approval proof over the canonical transport payload."""

    def verify_transport(self, envelope: ChatTransportEnvelope) -> bool:
        """Verify the authenticated Ecosystem Chat transport proof."""


class TransportReplayRegistry:
    def __init__(self) -> None:
        self._seen_envelopes: set[str] = set()
        self._seen_nonces: set[tuple[str, str]] = set()
        self._last_sequence: dict[str, int] = {}

    def validate_and_record(self, envelope: ChatTransportEnvelope) -> None:
        if envelope.envelope_id in self._seen_envelopes:
            raise PermissionError("transport envelope replay")
        nonce_key = (envelope.source_session_id, envelope.nonce)
        if nonce_key in self._seen_nonces:
            raise PermissionError("transport nonce replay")
        prior = self._last_sequence.get(envelope.source_session_id, 0)
        if envelope.sequence <= prior:
            raise PermissionError("transport sequence is not monotonic")
        self._seen_envelopes.add(envelope.envelope_id)
        self._seen_nonces.add(nonce_key)
        self._last_sequence[envelope.source_session_id] = envelope.sequence


class AuthenticatedChatTransportAdapter:
    """Authenticate one chat envelope before minimized durable ingestion.

    This boundary proves transport and approval metadata, checks freshness and replay,
    and then delegates to EcosystemChatIngestor. It never writes raw plaintext to the
    durable chain.
    """

    def __init__(
        self,
        *,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        verifier: TransportVerifier,
        replay_registry: TransportReplayRegistry,
        ingestor: EcosystemChatIngestor,
    ) -> None:
        self._pair_id = pair_id
        self._policy_ref = policy_ref
        self._relationship_epoch = relationship_epoch
        self._verifier = verifier
        self._replay_registry = replay_registry
        self._ingestor = ingestor

    def accept(
        self,
        envelope: ChatTransportEnvelope,
        *,
        now: int,
        previous_event_hash: str | None,
    ) -> IngestionResult:
        if not envelope.envelope_id or not envelope.source_session_id or not envelope.nonce:
            raise ValueError("transport identifiers and nonce are required")
        if envelope.sequence < 1:
            raise ValueError("transport sequence must be positive")
        if now < envelope.issued_at or now >= envelope.expires_at:
            raise PermissionError("transport envelope is outside its validity window")
        if not hmac.compare_digest(envelope.pair_id, self._pair_id):
            raise PermissionError("transport pair binding mismatch")
        if envelope.policy_ref != self._policy_ref:
            raise PermissionError("transport policy binding mismatch")
        if envelope.relationship_epoch != self._relationship_epoch:
            raise PermissionError("transport relationship epoch mismatch")
        if not envelope.observation.approved:
            raise PermissionError("transport observation is not user-approved")
        if not envelope.user_approval_proof or not envelope.transport_proof:
            raise PermissionError("transport and approval proofs are required")
        if not self._verifier.verify_user_approval(envelope):
            raise PermissionError("user approval proof verification failed")
        if not self._verifier.verify_transport(envelope):
            raise PermissionError("Ecosystem Chat transport proof verification failed")

        self._replay_registry.validate_and_record(envelope)
        return self._ingestor.ingest(
            envelope.observation,
            sequence=envelope.sequence,
            previous_event_hash=previous_event_hash,
        )
