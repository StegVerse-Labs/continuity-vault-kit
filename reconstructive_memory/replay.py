from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from threading import Lock
from typing import Mapping, Protocol

from .transport import ChatTransportEnvelope


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class ReplayState:
    version: int = 0
    envelope_commitments: tuple[str, ...] = ()
    nonce_commitments: tuple[str, ...] = ()
    last_sequences: tuple[tuple[str, int], ...] = ()
    state_hash: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "envelope_commitments": list(self.envelope_commitments),
            "nonce_commitments": list(self.nonce_commitments),
            "last_sequences": [list(item) for item in self.last_sequences],
        }

    def finalized(self) -> "ReplayState":
        payload = self.payload()
        return ReplayState(
            version=self.version,
            envelope_commitments=self.envelope_commitments,
            nonce_commitments=self.nonce_commitments,
            last_sequences=self.last_sequences,
            state_hash=_digest(payload),
        )

    def verify(self) -> None:
        if self.version < 0:
            raise ValueError("replay state version cannot be negative")
        if self.state_hash != _digest(self.payload()):
            raise ValueError("replay state hash mismatch")
        sessions = [session for session, _ in self.last_sequences]
        if len(sessions) != len(set(sessions)):
            raise ValueError("duplicate replay session sequence state")


class ReplayStateStore(Protocol):
    def read(self) -> ReplayState:
        """Return the current authoritative replay state."""

    def compare_and_swap(self, expected_version: int, replacement: ReplayState) -> bool:
        """Atomically replace state only when the version still matches."""


class InMemoryReplayStateStore:
    def __init__(self, state: ReplayState | None = None) -> None:
        self._state = state or ReplayState().finalized()
        self._state.verify()
        self._lock = Lock()

    def read(self) -> ReplayState:
        with self._lock:
            return self._state

    def compare_and_swap(self, expected_version: int, replacement: ReplayState) -> bool:
        replacement.verify()
        with self._lock:
            if self._state.version != expected_version:
                return False
            if replacement.version != expected_version + 1:
                raise ValueError("replay replacement version must advance exactly once")
            self._state = replacement
            return True


class DurableTransportReplayRegistry:
    """Atomically register transport replay state without storing raw identifiers."""

    def __init__(self, store: ReplayStateStore, *, max_attempts: int = 4) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._store = store
        self._max_attempts = max_attempts

    @staticmethod
    def _envelope_commitment(envelope: ChatTransportEnvelope) -> str:
        return _digest({"envelope_id": envelope.envelope_id})

    @staticmethod
    def _nonce_commitment(envelope: ChatTransportEnvelope) -> str:
        return _digest({"source_session_id": envelope.source_session_id, "nonce": envelope.nonce})

    def validate_and_record(self, envelope: ChatTransportEnvelope) -> ReplayState:
        envelope_commitment = self._envelope_commitment(envelope)
        nonce_commitment = self._nonce_commitment(envelope)

        for _ in range(self._max_attempts):
            current = self._store.read()
            current.verify()
            if envelope_commitment in current.envelope_commitments:
                raise PermissionError("transport envelope replay")
            if nonce_commitment in current.nonce_commitments:
                raise PermissionError("transport nonce replay")

            sequences: Mapping[str, int] = dict(current.last_sequences)
            prior = sequences.get(envelope.source_session_id, 0)
            if envelope.sequence <= prior:
                raise PermissionError("transport sequence is not monotonic")

            updated_sequences = dict(sequences)
            updated_sequences[envelope.source_session_id] = envelope.sequence
            replacement = ReplayState(
                version=current.version + 1,
                envelope_commitments=current.envelope_commitments + (envelope_commitment,),
                nonce_commitments=current.nonce_commitments + (nonce_commitment,),
                last_sequences=tuple(sorted(updated_sequences.items())),
            ).finalized()
            if self._store.compare_and_swap(current.version, replacement):
                return replacement

        raise PermissionError("transport replay state changed concurrently")
