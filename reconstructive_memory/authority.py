from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from .access import AccessReceipt
from .journal import SessionJournal
from .lifecycle import CapabilityGrant
from .session import ReconstructionSessionResult


@dataclass(frozen=True)
class PreparedSession:
    session_id: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    capability_commitment: str
    request_commitment: str
    expected_use_count: int


@dataclass(frozen=True)
class CommitSnapshot:
    version: int
    journal: SessionJournal
    capability: CapabilityGrant
    receipt: AccessReceipt


class AuthoritativeSessionStore:
    """Compare-and-swap boundary for one reconstruction commit.

    The lock models the minimum atomicity invariant: capability consumption,
    receipt persistence, and the terminal journal transition become visible
    together. A production adapter must reproduce this in durable storage.
    """

    def __init__(self, capability: CapabilityGrant, journal: SessionJournal | None = None) -> None:
        self._capability = capability
        self._journal = journal or SessionJournal()
        self._receipts: dict[str, AccessReceipt] = {}
        self._prepared: dict[str, PreparedSession] = {}
        self._version = 0
        self._lock = Lock()

    @property
    def version(self) -> int:
        return self._version

    @property
    def journal(self) -> SessionJournal:
        return self._journal

    @property
    def capability(self) -> CapabilityGrant:
        return self._capability

    def prepare(
        self,
        *,
        session_id: str,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        request_commitment: str,
    ) -> PreparedSession:
        with self._lock:
            if session_id in self._prepared or any(
                entry.session_id == session_id for entry in self._journal.entries
            ):
                raise PermissionError("session identifier replay")
            if pair_id != self._capability.pair_id or policy_ref != self._capability.policy_ref:
                raise PermissionError("preparation crosses capability pair or policy")
            if relationship_epoch != self._capability.relationship_epoch:
                raise PermissionError("preparation relationship epoch mismatch")
            if not request_commitment:
                raise ValueError("request commitment is required")

            prepared = PreparedSession(
                session_id=session_id,
                pair_id=pair_id,
                policy_ref=policy_ref,
                relationship_epoch=relationship_epoch,
                capability_commitment=self._capability.commitment,
                request_commitment=request_commitment,
                expected_use_count=self._capability.use_count,
            )
            self._journal = self._journal.prepare(
                session_id=session_id,
                pair_id=pair_id,
                policy_ref=policy_ref,
                relationship_epoch=relationship_epoch,
                capability_commitment=prepared.capability_commitment,
                request_commitment=request_commitment,
            )
            self._prepared[session_id] = prepared
            self._version += 1
            return prepared

    def commit(
        self,
        *,
        prepared: PreparedSession,
        result: ReconstructionSessionResult,
    ) -> CommitSnapshot:
        with self._lock:
            current = self._prepared.get(prepared.session_id)
            if current != prepared:
                raise PermissionError("session preparation is unknown or stale")
            if self._capability.commitment != prepared.capability_commitment:
                raise PermissionError("capability changed after preparation")
            if self._capability.use_count != prepared.expected_use_count:
                raise PermissionError("capability use count changed after preparation")

            consumed = result.consumed_capability
            if consumed.capability_id != self._capability.capability_id:
                raise PermissionError("committed capability identifier mismatch")
            if consumed.pair_id != prepared.pair_id or consumed.policy_ref != prepared.policy_ref:
                raise PermissionError("committed capability binding mismatch")
            if consumed.relationship_epoch != prepared.relationship_epoch:
                raise PermissionError("committed capability epoch mismatch")
            if consumed.use_count != self._capability.use_count + 1:
                raise PermissionError("capability consumption transition is invalid")

            result.receipt.verify()
            if result.receipt.pair_id != prepared.pair_id:
                raise PermissionError("receipt pair binding mismatch")
            if result.receipt.policy_ref != prepared.policy_ref:
                raise PermissionError("receipt policy binding mismatch")
            if result.receipt.relationship_epoch != prepared.relationship_epoch:
                raise PermissionError("receipt epoch binding mismatch")
            if result.receipt.receipt_id in self._receipts:
                raise PermissionError("receipt identifier replay")

            journal = self._journal.commit(
                prepared.session_id,
                receipt_hash=result.receipt.receipt_hash,
            )
            self._capability = consumed
            self._receipts[result.receipt.receipt_id] = result.receipt
            self._journal = journal
            del self._prepared[prepared.session_id]
            self._version += 1
            return CommitSnapshot(
                version=self._version,
                journal=self._journal,
                capability=self._capability,
                receipt=result.receipt,
            )

    def abort(self, *, prepared: PreparedSession, failure_code: str) -> None:
        with self._lock:
            current = self._prepared.get(prepared.session_id)
            if current != prepared:
                raise PermissionError("session preparation is unknown or stale")
            if not failure_code:
                raise ValueError("failure code is required")
            self._journal = self._journal.abort(prepared.session_id, failure_code=failure_code)
            del self._prepared[prepared.session_id]
            self._version += 1

    def receipt(self, receipt_id: str) -> AccessReceipt:
        try:
            return self._receipts[receipt_id]
        except KeyError as exc:
            raise KeyError("receipt is not committed") from exc
