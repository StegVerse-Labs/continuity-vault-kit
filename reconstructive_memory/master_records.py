from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from typing import Mapping, Protocol


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class MasterRecordEnvelope:
    export_id: str
    source_type: str
    source_commitment: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    destination: str
    created_at: int
    prior_export_hash: str | None = None
    payload_commitment: str = ""
    export_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "export_id": self.export_id,
            "source_type": self.source_type,
            "source_commitment": self.source_commitment,
            "pair_id": self.pair_id,
            "policy_ref": self.policy_ref,
            "relationship_epoch": self.relationship_epoch,
            "destination": self.destination,
            "created_at": self.created_at,
            "prior_export_hash": self.prior_export_hash,
            "payload_commitment": self.payload_commitment,
        }

    def with_hash(self) -> "MasterRecordEnvelope":
        return replace(self, export_hash=_digest(self.payload()))

    def verify(self) -> None:
        if not self.export_id or not self.source_type or not self.source_commitment:
            raise ValueError("Master-Records export identity is incomplete")
        if self.relationship_epoch < 1:
            raise ValueError("relationship epoch must be positive")
        if self.destination != "master-records":
            raise ValueError("unsupported Master-Records destination")
        expected = _digest(self.payload())
        if not self.export_hash or not hmac.compare_digest(self.export_hash, expected):
            raise ValueError("Master-Records export hash mismatch")


@dataclass(frozen=True)
class MasterRecordAcknowledgement:
    export_id: str
    export_hash: str
    destination_receipt_ref: str
    destination_receipt_hash: str
    accepted_at: int
    acknowledgement_hash: str = ""

    def payload(self) -> Mapping[str, object]:
        return {
            "export_id": self.export_id,
            "export_hash": self.export_hash,
            "destination_receipt_ref": self.destination_receipt_ref,
            "destination_receipt_hash": self.destination_receipt_hash,
            "accepted_at": self.accepted_at,
        }

    def with_hash(self) -> "MasterRecordAcknowledgement":
        return replace(self, acknowledgement_hash=_digest(self.payload()))

    def verify(self) -> None:
        expected = _digest(self.payload())
        if not self.acknowledgement_hash or not hmac.compare_digest(self.acknowledgement_hash, expected):
            raise ValueError("Master-Records acknowledgement hash mismatch")


class MasterRecordsVerifier(Protocol):
    def verify_acknowledgement(self, acknowledgement: MasterRecordAcknowledgement) -> bool:
        """Verify the destination-controlled acknowledgement proof."""


class MasterRecordsOutbox:
    """Replay-safe, plaintext-free propagation state for Master-Records exports."""

    def __init__(self) -> None:
        self._pending: dict[str, MasterRecordEnvelope] = {}
        self._acknowledged: dict[str, MasterRecordAcknowledgement] = {}
        self._source_commitments: set[str] = set()
        self._tip: str | None = None

    @property
    def tip(self) -> str | None:
        return self._tip

    def enqueue(
        self,
        *,
        export_id: str,
        source_type: str,
        source_commitment: str,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        created_at: int,
        payload_descriptor: Mapping[str, object],
    ) -> MasterRecordEnvelope:
        if export_id in self._pending or export_id in self._acknowledged:
            raise PermissionError("Master-Records export identifier replay")
        if source_commitment in self._source_commitments:
            raise PermissionError("source receipt was already exported")
        envelope = MasterRecordEnvelope(
            export_id=export_id,
            source_type=source_type,
            source_commitment=source_commitment,
            pair_id=pair_id,
            policy_ref=policy_ref,
            relationship_epoch=relationship_epoch,
            destination="master-records",
            created_at=created_at,
            prior_export_hash=self._tip,
            payload_commitment=_digest(payload_descriptor),
        ).with_hash()
        envelope.verify()
        self._pending[export_id] = envelope
        self._source_commitments.add(source_commitment)
        self._tip = envelope.export_hash
        return envelope

    def acknowledge(
        self,
        acknowledgement: MasterRecordAcknowledgement,
        verifier: MasterRecordsVerifier,
    ) -> MasterRecordAcknowledgement:
        acknowledgement.verify()
        envelope = self._pending.get(acknowledgement.export_id)
        if envelope is None:
            raise LookupError("Master-Records export is not pending")
        if acknowledgement.export_hash != envelope.export_hash:
            raise PermissionError("Master-Records acknowledgement export mismatch")
        if not verifier.verify_acknowledgement(acknowledgement):
            raise PermissionError("Master-Records acknowledgement verification failed")
        self._acknowledged[acknowledgement.export_id] = acknowledgement
        del self._pending[acknowledgement.export_id]
        return acknowledgement

    def pending(self, export_id: str) -> MasterRecordEnvelope:
        try:
            return self._pending[export_id]
        except KeyError as exc:
            raise KeyError("Master-Records export is not pending") from exc

    def acknowledged(self, export_id: str) -> MasterRecordAcknowledgement:
        try:
            return self._acknowledged[export_id]
        except KeyError as exc:
            raise KeyError("Master-Records export is not acknowledged") from exc
