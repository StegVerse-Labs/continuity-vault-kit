from __future__ import annotations

from dataclasses import asdict
import json
from typing import Protocol

from .master_records import MasterRecordAcknowledgement, MasterRecordEnvelope, MasterRecordsVerifier
from .master_records_state import (
    DurableMasterRecordsOutbox,
    MasterRecordsEntry,
    MasterRecordsState,
    MasterRecordsStateStore,
)


class ReplicatedBlobStore(Protocol):
    """External compare-and-swap blob store.

    Implementations may use a database, object store, or consensus service, but
    must compare against the exact prior blob bytes before replacing them.
    """

    def read_blob(self) -> bytes | None: ...

    def compare_and_swap_blob(self, expected: bytes | None, updated: bytes) -> bool: ...


class MasterRecordsStateCodec:
    """Canonical, integrity-checked serialization for durable outbox state."""

    @staticmethod
    def encode(state: MasterRecordsState) -> bytes:
        state.verify()
        payload = {
            "version": state.version,
            "tip": state.tip,
            "source_commitments": sorted(state.source_commitments),
            "state_hash": state.state_hash,
            "entries": {
                export_id: {
                    "envelope": asdict(entry.envelope),
                    "state": entry.state,
                    "attempts": entry.attempts,
                    "next_attempt_at": entry.next_attempt_at,
                    "acknowledgement": asdict(entry.acknowledgement) if entry.acknowledgement else None,
                    "terminal_reason": entry.terminal_reason,
                    "superseded_by": entry.superseded_by,
                }
                for export_id, entry in sorted(state.entries.items())
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    @staticmethod
    def decode(blob: bytes) -> MasterRecordsState:
        try:
            payload = json.loads(blob.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid Master-Records state blob") from exc
        entries: dict[str, MasterRecordsEntry] = {}
        for export_id, raw in payload["entries"].items():
            acknowledgement = raw.get("acknowledgement")
            entries[export_id] = MasterRecordsEntry(
                envelope=MasterRecordEnvelope(**raw["envelope"]),
                state=raw["state"],
                attempts=raw["attempts"],
                next_attempt_at=raw["next_attempt_at"],
                acknowledgement=MasterRecordAcknowledgement(**acknowledgement) if acknowledgement else None,
                terminal_reason=raw.get("terminal_reason"),
                superseded_by=raw.get("superseded_by"),
            )
        state = MasterRecordsState(
            version=payload["version"],
            entries=entries,
            source_commitments=frozenset(payload["source_commitments"]),
            tip=payload.get("tip"),
            state_hash=payload["state_hash"],
        )
        state.verify()
        return state


class BlobMasterRecordsStateStore(MasterRecordsStateStore):
    """Adapter from the outbox state protocol to an external CAS blob store."""

    def __init__(self, backend: ReplicatedBlobStore) -> None:
        self._backend = backend

    def read(self) -> MasterRecordsState:
        blob = self._backend.read_blob()
        if blob is None:
            return MasterRecordsState(0, {}, frozenset(), None).with_hash()
        return MasterRecordsStateCodec.decode(blob)

    def compare_and_swap(self, expected_hash: str, updated: MasterRecordsState) -> bool:
        updated.verify()
        current_blob = self._backend.read_blob()
        current = MasterRecordsState(0, {}, frozenset(), None).with_hash() if current_blob is None else MasterRecordsStateCodec.decode(current_blob)
        if current.state_hash != expected_hash:
            return False
        if updated.version != current.version + 1:
            raise ValueError("Master-Records state must advance exactly one version")
        return self._backend.compare_and_swap_blob(current_blob, MasterRecordsStateCodec.encode(updated))


class MasterRecordsDeliveryClient(Protocol):
    def deliver(self, envelope: MasterRecordEnvelope) -> MasterRecordAcknowledgement | None:
        """Return a destination acknowledgement, or None when delivery is unresolved."""


def deliver_due_exports(
    outbox: DurableMasterRecordsOutbox,
    client: MasterRecordsDeliveryClient,
    verifier: MasterRecordsVerifier,
    *,
    now: int,
    retry_after: int,
) -> tuple[str, ...]:
    """Attempt due exports without treating transport success as acknowledgement."""

    completed: list[str] = []
    for entry in outbox.due(now):
        acknowledgement = client.deliver(entry.envelope)
        if acknowledgement is None:
            outbox.record_attempt(entry.envelope.export_id, now=now, retry_after=retry_after)
            continue
        outbox.acknowledge(acknowledgement, verifier)
        completed.append(entry.envelope.export_id)
    return tuple(completed)
