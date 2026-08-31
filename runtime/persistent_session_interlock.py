from __future__ import annotations

import re
from typing import Any, Callable

from runtime.persistent_session_reconstruction import (
    PersistentSessionError,
    build_reconstruction_projection,
    session_head_sha256,
    validate_session_head,
    verify_successor,
)

RECORD_PREFIX = "persistent-session-head:"
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")
READ_SCOPE = ["session_head"]
COMMIT_SCOPE = ["session_head_candidate"]


class PersistentSessionInterlockError(ValueError):
    pass


def parse_session_id(record_class: Any) -> str:
    if not isinstance(record_class, str) or not record_class.startswith(RECORD_PREFIX):
        raise PersistentSessionInterlockError("persistent session record_class required")
    session_id = record_class[len(RECORD_PREFIX):]
    if not SESSION_ID_RE.fullmatch(session_id):
        raise PersistentSessionInterlockError("session_id invalid")
    return session_id


def session_head_destination(session_id: str) -> str:
    if not SESSION_ID_RE.fullmatch(session_id):
        raise PersistentSessionInterlockError("session_id invalid")
    return f"kv://_System/Continuity/Sessions/{session_id}/head.json"


class PersistentSessionPolicyAdapter:
    """Policy adapter for bounded persistent-session reads and candidate staging.

    This object is intended to be injected as KVInterlockRuntime.policy_evaluator.
    Existing KVInterlockRuntime authority and verified InTr admission checks run
    before this adapter is invoked.
    """

    def __init__(
        self,
        *,
        head_reader: Callable[[str], dict[str, Any] | None],
    ) -> None:
        self.head_reader = head_reader

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        session_id = parse_session_id(request.get("record_class"))
        operation = request.get("operation")

        if operation == "REQUEST":
            return self._read_policy(request, session_id)
        if operation == "COMMIT_CANDIDATE":
            return self._candidate_policy(request, session_id)
        return {
            "decision": "DENY",
            "granted_scope": [],
            "context": {},
            "source_refs": [],
            "policy_profile": "KV-PERSISTENT-SESSION-v1:OPERATION_NOT_ALLOWED",
        }

    def _read_policy(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        if request.get("requested_scope") != READ_SCOPE:
            raise PersistentSessionInterlockError("session read scope invalid")
        if request.get("disclosure_mode") != "BOUNDED_CONTEXT":
            raise PersistentSessionInterlockError("session read requires bounded context")

        head = self.head_reader(session_id)
        if head is None:
            return {
                "decision": "DENY",
                "granted_scope": [],
                "context": {},
                "source_refs": [session_head_destination(session_id)],
                "policy_profile": "KV-PERSISTENT-SESSION-v1:HEAD_NOT_FOUND",
            }
        try:
            validated = validate_session_head(head)
            projection = build_reconstruction_projection(validated)
        except PersistentSessionError as exc:
            raise PersistentSessionInterlockError("stored session head invalid") from exc

        source_refs = [
            session_head_destination(session_id),
            validated["provenance"]["conversation_event_chain_ref"],
        ]
        return {
            "decision": "ALLOW_BOUNDED_CONTEXT",
            "granted_scope": list(READ_SCOPE),
            "context": {"session_head": projection},
            "source_refs": source_refs,
            "policy_profile": "KV-PERSISTENT-SESSION-v1:BOUNDED_RECONSTRUCTION",
            "redaction_profile": "SEMANTIC_SESSION_HEAD_ONLY",
        }

    def _candidate_policy(self, request: dict[str, Any], session_id: str) -> dict[str, Any]:
        if request.get("requested_scope") != COMMIT_SCOPE:
            raise PersistentSessionInterlockError("session candidate scope invalid")
        candidate = request.get("candidate_writeback")
        if not isinstance(candidate, dict):
            raise PersistentSessionInterlockError("candidate_writeback required")
        expected_type = f"{RECORD_PREFIX}{session_id}"
        if candidate.get("candidate_type") != expected_type:
            raise PersistentSessionInterlockError("candidate_type session binding mismatch")
        if candidate.get("requested_destination") != session_head_destination(session_id):
            raise PersistentSessionInterlockError("candidate destination mismatch")
        return {
            "decision": "ALLOW_BOUNDED_CONTEXT",
            "granted_scope": list(COMMIT_SCOPE),
            "context": {},
            "source_refs": [session_head_destination(session_id)],
            "policy_profile": "KV-PERSISTENT-SESSION-v1:CANDIDATE_STAGING_ONLY",
            "redaction_profile": "NO_CANONICAL_MUTATION",
        }


class PersistentSessionCandidateStore:
    """Validate and stage successor heads without changing canonical KV state."""

    def __init__(
        self,
        *,
        head_reader: Callable[[str], dict[str, Any] | None],
        payload_reader: Callable[[str], dict[str, Any]],
        candidate_writer: Callable[[dict[str, Any]], str],
        recall_root_validator: Callable[[str, str, str], bool] | None = None,
    ) -> None:
        self.head_reader = head_reader
        self.payload_reader = payload_reader
        self.candidate_writer = candidate_writer
        self.recall_root_validator = recall_root_validator

    def __call__(self, candidate_record: dict[str, Any]) -> str:
        session_id = parse_session_id(candidate_record.get("candidate_type"))
        expected_destination = session_head_destination(session_id)
        if candidate_record.get("requested_destination") != expected_destination:
            raise PersistentSessionInterlockError("candidate destination mismatch")
        if candidate_record.get("canonical_state_changed") is not False:
            raise PersistentSessionInterlockError("candidate cannot claim canonical mutation")
        if candidate_record.get("candidate_only") is not True:
            raise PersistentSessionInterlockError("candidate_only required")
        if candidate_record.get("authority_effect") != "NONE":
            raise PersistentSessionInterlockError("candidate authority_effect must be NONE")

        current = self.head_reader(session_id)
        if current is None:
            raise PersistentSessionInterlockError("current session head required")

        payload_ref = candidate_record.get("payload_ref")
        if not isinstance(payload_ref, str) or not payload_ref:
            raise PersistentSessionInterlockError("payload_ref required")
        successor = self.payload_reader(payload_ref)

        try:
            current_valid = validate_session_head(current)
            successor_valid = verify_successor(current_valid, successor)
        except PersistentSessionError as exc:
            raise PersistentSessionInterlockError("session successor rejected") from exc

        current_chain = current_valid["provenance"]["conversation_event_chain_ref"]
        successor_chain = successor_valid["provenance"]["conversation_event_chain_ref"]
        if successor_chain != current_chain:
            raise PersistentSessionInterlockError("conversation event chain ref drift")

        current_root = current_valid["provenance"]["conversation_event_verification_root"]
        successor_root = successor_valid["provenance"]["conversation_event_verification_root"]
        if successor_root != current_root:
            if self.recall_root_validator is None:
                raise PersistentSessionInterlockError(
                    "conversation event verification root advance not admitted"
                )
            try:
                admitted = self.recall_root_validator(current_root, successor_root, current_chain)
            except Exception as exc:
                raise PersistentSessionInterlockError(
                    "conversation event verification root validation failed"
                ) from exc
            if admitted is not True:
                raise PersistentSessionInterlockError(
                    "conversation event verification root advance rejected"
                )

        staged = {
            "schema": "stegverse.kv.persistent-session-candidate/v1",
            "session_id": session_id,
            "request_id": candidate_record.get("request_id"),
            "authority_ref": candidate_record.get("authority_ref"),
            "intr_receipt_ref": candidate_record.get("intr_receipt_ref"),
            "payload_ref": payload_ref,
            "requested_destination": expected_destination,
            "current_head_sha256": session_head_sha256(current_valid),
            "successor_head_sha256": session_head_sha256(successor_valid),
            "conversation_event_chain_ref": successor_chain,
            "conversation_event_verification_root": successor_root,
            "canonical_state_changed": False,
            "candidate_only": True,
            "execution_authority": "NONE",
            "credential_authority": "TV/TVC",
            "authority_effect": "NONE",
        }
        ref = self.candidate_writer(staged)
        if not isinstance(ref, str) or not ref:
            raise PersistentSessionInterlockError("candidate staging did not return reference")
        return ref
