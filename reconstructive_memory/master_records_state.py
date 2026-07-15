from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from threading import Lock
from typing import Mapping, Protocol

from .master_records import MasterRecordAcknowledgement, MasterRecordEnvelope, MasterRecordsVerifier


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class MasterRecordsEntry:
    envelope: MasterRecordEnvelope
    state: str
    attempts: int = 0
    next_attempt_at: int = 0
    acknowledgement: MasterRecordAcknowledgement | None = None
    terminal_reason: str | None = None
    superseded_by: str | None = None

    def verify(self) -> None:
        self.envelope.verify()
        if self.state not in {"pending", "acknowledged", "deprecated", "superseded"}:
            raise ValueError("unsupported Master-Records entry state")
        if self.attempts < 0 or self.next_attempt_at < 0:
            raise ValueError("invalid retry state")
        if self.state == "acknowledged" and self.acknowledgement is None:
            raise ValueError("acknowledged export lacks acknowledgement")
        if self.state in {"deprecated", "superseded"} and not self.terminal_reason:
            raise ValueError("terminal export lacks reason")
        if self.state == "superseded" and not self.superseded_by:
            raise ValueError("superseded export lacks successor")


@dataclass(frozen=True)
class MasterRecordsState:
    version: int
    entries: Mapping[str, MasterRecordsEntry]
    source_commitments: frozenset[str]
    tip: str | None
    state_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "version": self.version,
            "entries": {
                key: {
                    "export_hash": value.envelope.export_hash,
                    "state": value.state,
                    "attempts": value.attempts,
                    "next_attempt_at": value.next_attempt_at,
                    "ack_hash": value.acknowledgement.acknowledgement_hash if value.acknowledgement else None,
                    "terminal_reason": value.terminal_reason,
                    "superseded_by": value.superseded_by,
                }
                for key, value in sorted(self.entries.items())
            },
            "source_commitments": sorted(self.source_commitments),
            "tip": self.tip,
        }

    def with_hash(self) -> "MasterRecordsState":
        return replace(self, state_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.version < 0:
            raise ValueError("invalid Master-Records state version")
        for entry in self.entries.values():
            entry.verify()
        expected = _digest(self.payload())
        if not self.state_hash or not hmac.compare_digest(self.state_hash, expected):
            raise ValueError("Master-Records state hash mismatch")


class MasterRecordsStateStore(Protocol):
    def read(self) -> MasterRecordsState: ...
    def compare_and_swap(self, expected_hash: str, updated: MasterRecordsState) -> bool: ...


class InMemoryMasterRecordsStateStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state = MasterRecordsState(0, {}, frozenset(), None).with_hash()

    def read(self) -> MasterRecordsState:
        with self._lock:
            return self._state

    def compare_and_swap(self, expected_hash: str, updated: MasterRecordsState) -> bool:
        updated.verify()
        with self._lock:
            if not hmac.compare_digest(self._state.state_hash, expected_hash):
                return False
            if updated.version != self._state.version + 1:
                raise ValueError("Master-Records state must advance exactly one version")
            self._state = updated
            return True


class DurableMasterRecordsOutbox:
    def __init__(self, store: MasterRecordsStateStore, *, max_cas_retries: int = 4) -> None:
        self._store = store
        self._max_cas_retries = max_cas_retries

    def enqueue(self, envelope: MasterRecordEnvelope) -> MasterRecordEnvelope:
        envelope.verify()
        for _ in range(self._max_cas_retries):
            current = self._store.read(); current.verify()
            if envelope.export_id in current.entries:
                raise PermissionError("Master-Records export identifier replay")
            if envelope.source_commitment in current.source_commitments:
                raise PermissionError("source receipt was already exported")
            if envelope.prior_export_hash != current.tip:
                raise PermissionError("Master-Records export chain tip mismatch")
            entries = dict(current.entries)
            entries[envelope.export_id] = MasterRecordsEntry(envelope=envelope, state="pending")
            updated = MasterRecordsState(current.version + 1, entries, current.source_commitments | {envelope.source_commitment}, envelope.export_hash).with_hash()
            if self._store.compare_and_swap(current.state_hash, updated):
                return envelope
        raise RuntimeError("Master-Records state contention")

    def record_attempt(self, export_id: str, *, now: int, retry_after: int) -> MasterRecordsEntry:
        if retry_after < now:
            raise ValueError("retry time cannot precede attempt time")
        return self._transition(export_id, lambda e: replace(e, attempts=e.attempts + 1, next_attempt_at=retry_after))

    def acknowledge(self, acknowledgement: MasterRecordAcknowledgement, verifier: MasterRecordsVerifier) -> MasterRecordsEntry:
        acknowledgement.verify()
        def mutate(entry: MasterRecordsEntry) -> MasterRecordsEntry:
            if entry.state != "pending": raise PermissionError("Master-Records export is not pending")
            if acknowledgement.export_hash != entry.envelope.export_hash: raise PermissionError("Master-Records acknowledgement export mismatch")
            if not verifier.verify_acknowledgement(acknowledgement): raise PermissionError("Master-Records acknowledgement verification failed")
            return replace(entry, state="acknowledged", acknowledgement=acknowledgement, next_attempt_at=0)
        return self._transition(acknowledgement.export_id, mutate)

    def deprecate(self, export_id: str, *, reason: str) -> MasterRecordsEntry:
        if not reason: raise ValueError("deprecation reason is required")
        return self._transition(export_id, lambda e: replace(e, state="deprecated", terminal_reason=reason, next_attempt_at=0) if e.state == "pending" else (_ for _ in ()).throw(PermissionError("only pending exports may be deprecated")))

    def supersede(self, export_id: str, *, successor_export_id: str, reason: str) -> MasterRecordsEntry:
        if not successor_export_id or not reason: raise ValueError("successor and reason are required")
        def mutate(entry: MasterRecordsEntry) -> MasterRecordsEntry:
            if entry.state != "pending": raise PermissionError("only pending exports may be superseded")
            state = self._store.read()
            if successor_export_id not in state.entries: raise LookupError("successor export is unknown")
            return replace(entry, state="superseded", terminal_reason=reason, superseded_by=successor_export_id, next_attempt_at=0)
        return self._transition(export_id, mutate)

    def due(self, now: int) -> tuple[MasterRecordsEntry, ...]:
        state = self._store.read(); state.verify()
        return tuple(entry for entry in state.entries.values() if entry.state == "pending" and entry.next_attempt_at <= now)

    def _transition(self, export_id: str, mutate) -> MasterRecordsEntry:
        for _ in range(self._max_cas_retries):
            current = self._store.read(); current.verify()
            try: entry = current.entries[export_id]
            except KeyError as exc: raise LookupError("Master-Records export is unknown") from exc
            changed = mutate(entry); changed.verify()
            entries = dict(current.entries); entries[export_id] = changed
            updated = MasterRecordsState(current.version + 1, entries, current.source_commitments, current.tip).with_hash()
            if self._store.compare_and_swap(current.state_hash, updated): return changed
        raise RuntimeError("Master-Records state contention")
