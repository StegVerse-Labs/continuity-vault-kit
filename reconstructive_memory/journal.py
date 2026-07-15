from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import hmac
import json
from typing import Iterable


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class SessionJournalEntry:
    session_id: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    capability_commitment: str
    request_commitment: str
    status: str
    prior_entry_hash: str | None
    receipt_hash: str | None = None
    failure_code: str | None = None
    entry_hash: str = ""

    def payload(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "pair_id": self.pair_id,
            "policy_ref": self.policy_ref,
            "relationship_epoch": self.relationship_epoch,
            "capability_commitment": self.capability_commitment,
            "request_commitment": self.request_commitment,
            "status": self.status,
            "prior_entry_hash": self.prior_entry_hash,
            "receipt_hash": self.receipt_hash,
            "failure_code": self.failure_code,
        }

    def with_hash(self) -> "SessionJournalEntry":
        return replace(self, entry_hash=_digest(self.payload()))

    def verify(self) -> None:
        if self.status not in {"prepared", "committed", "aborted", "replay-rejected"}:
            raise ValueError("unsupported session journal status")
        if self.status == "committed" and not self.receipt_hash:
            raise ValueError("committed session requires receipt hash")
        if self.status in {"aborted", "replay-rejected"} and not self.failure_code:
            raise ValueError("failed session requires failure code")
        expected = _digest(self.payload())
        if not self.entry_hash or not hmac.compare_digest(self.entry_hash, expected):
            raise ValueError("session journal hash mismatch")


class SessionJournal:
    """Append-only plaintext-free reconstruction transaction journal."""

    def __init__(self, entries: Iterable[SessionJournalEntry] = ()) -> None:
        self._entries = tuple(entries)
        self._verify_chain()

    @property
    def entries(self) -> tuple[SessionJournalEntry, ...]:
        return self._entries

    def _verify_chain(self) -> None:
        prior: str | None = None
        terminal_by_session: dict[str, str] = {}
        for entry in self._entries:
            entry.verify()
            if entry.prior_entry_hash != prior:
                raise ValueError("session journal chain mismatch")
            prior = entry.entry_hash
            previous_status = terminal_by_session.get(entry.session_id)
            if previous_status in {"committed", "aborted", "replay-rejected"}:
                raise ValueError("terminal session journal state cannot be extended")
            if previous_status is None and entry.status != "prepared":
                raise ValueError("session must begin in prepared state")
            if previous_status == "prepared" and entry.status == "prepared":
                raise ValueError("session cannot be prepared twice")
            terminal_by_session[entry.session_id] = entry.status

    def _append(self, entry: SessionJournalEntry) -> "SessionJournal":
        prior_hash = self._entries[-1].entry_hash if self._entries else None
        finalized = replace(entry, prior_entry_hash=prior_hash).with_hash()
        finalized.verify()
        return SessionJournal(self._entries + (finalized,))

    def prepare(
        self,
        *,
        session_id: str,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        capability_commitment: str,
        request_commitment: str,
    ) -> "SessionJournal":
        if any(entry.session_id == session_id for entry in self._entries):
            return self.reject_replay(
                session_id=session_id,
                pair_id=pair_id,
                policy_ref=policy_ref,
                relationship_epoch=relationship_epoch,
                capability_commitment=capability_commitment,
                request_commitment=request_commitment,
            )
        return self._append(
            SessionJournalEntry(
                session_id=session_id,
                pair_id=pair_id,
                policy_ref=policy_ref,
                relationship_epoch=relationship_epoch,
                capability_commitment=capability_commitment,
                request_commitment=request_commitment,
                status="prepared",
                prior_entry_hash=None,
            )
        )

    def _prepared(self, session_id: str) -> SessionJournalEntry:
        matches = [entry for entry in self._entries if entry.session_id == session_id]
        if not matches or matches[-1].status != "prepared":
            raise ValueError("session is not in prepared state")
        return matches[-1]

    def commit(self, session_id: str, *, receipt_hash: str) -> "SessionJournal":
        prepared = self._prepared(session_id)
        return self._append(replace(prepared, status="committed", receipt_hash=receipt_hash, entry_hash=""))

    def abort(self, session_id: str, *, failure_code: str) -> "SessionJournal":
        prepared = self._prepared(session_id)
        return self._append(replace(prepared, status="aborted", failure_code=failure_code, entry_hash=""))

    def reject_replay(
        self,
        *,
        session_id: str,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        capability_commitment: str,
        request_commitment: str,
    ) -> "SessionJournal":
        replay_id = f"{session_id}:replay:{len(self._entries) + 1}"
        prepared = self._append(
            SessionJournalEntry(
                session_id=replay_id,
                pair_id=pair_id,
                policy_ref=policy_ref,
                relationship_epoch=relationship_epoch,
                capability_commitment=capability_commitment,
                request_commitment=request_commitment,
                status="prepared",
                prior_entry_hash=None,
            )
        )
        return prepared.abort(replay_id, failure_code="SESSION_ID_REPLAY")
