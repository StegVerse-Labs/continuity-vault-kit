"""Private-KV append-only conversation event store.

This module reuses the canonical continuity.recall chain semantics. Storage is
injected so source code cannot silently acquire Drive, provider, credential, or
execution authority.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any, Callable

from continuity.recall import event_hash, validate_chain

CHAIN_REF = "_System/Continuity/Events/events.jsonl"
FORBIDDEN_FIELD_TOKENS = {
    "password",
    "token",
    "cookie",
    "private_key",
    "privatekey",
    "credential_value",
    "credential_secret",
    "seed",
    "mnemonic",
    "recovery_code",
    "raw_biometric",
    "transcript",
    "raw_message",
    "conversation_dump",
    "chat_dump",
}


class ConversationEventStoreError(ValueError):
    pass


def _contains_forbidden_name(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in FORBIDDEN_FIELD_TOKENS)


def _reject_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ConversationEventStoreError(f"non-string field at {path}")
            if _contains_forbidden_name(key):
                raise ConversationEventStoreError(f"forbidden field at {path}.{key}")
            _reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def parse_events_jsonl(text: str) -> list[dict[str, Any]]:
    if not isinstance(text, str):
        raise ConversationEventStoreError("event store content must be text")
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConversationEventStoreError(
                f"invalid event JSON at line {lineno}"
            ) from exc
        if not isinstance(event, dict):
            raise ConversationEventStoreError(
                f"event line {lineno} must be an object"
            )
        _reject_forbidden_fields(event)
        events.append(event)
    try:
        return validate_chain(events)
    except ValueError as exc:
        raise ConversationEventStoreError(str(exc)) from exc


def serialize_events_jsonl(events: list[dict[str, Any]]) -> str:
    try:
        validated = validate_chain(events)
    except ValueError as exc:
        raise ConversationEventStoreError(str(exc)) from exc
    for event in validated:
        _reject_forbidden_fields(event)
    if not validated:
        return ""
    return "".join(
        json.dumps(
            event,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
        for event in validated
    )


def verification_root(events: list[dict[str, Any]]) -> str | None:
    if not events:
        return None
    try:
        validated = validate_chain(events)
    except ValueError as exc:
        raise ConversationEventStoreError(str(exc)) from exc
    return event_hash(validated[-1])


def append_event_candidate(
    current_events: list[dict[str, Any]],
    event: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    try:
        current = validate_chain(current_events)
    except ValueError as exc:
        raise ConversationEventStoreError(str(exc)) from exc

    candidate = copy.deepcopy(event)
    _reject_forbidden_fields(candidate)

    if current:
        candidate["previous_event_hash"] = event_hash(current[-1])
        try:
            if datetime.fromisoformat(
                candidate["timestamp"].replace("Z", "+00:00")
            ) < datetime.fromisoformat(
                current[-1]["timestamp"].replace("Z", "+00:00")
            ):
                raise ConversationEventStoreError("event timestamp rollback")
        except KeyError as exc:
            raise ConversationEventStoreError("event timestamp required") from exc
    else:
        if candidate.get("previous_event_hash") is not None:
            raise ConversationEventStoreError(
                "genesis event previous_event_hash must be null"
            )
        candidate["previous_event_hash"] = None

    successor = [*copy.deepcopy(current), candidate]
    try:
        successor = validate_chain(successor)
    except ValueError as exc:
        raise ConversationEventStoreError(str(exc)) from exc
    return successor, event_hash(successor[-1])


class ConversationEventStore:
    """Compare-and-swap private event-chain store.

    reader returns the current exact JSONL string and an opaque storage ref.
    writer receives expected prior root plus exact successor text and must
    return an opaque write ref. readback then independently returns current
    exact JSONL text and opaque storage ref.
    """

    def __init__(
        self,
        *,
        reader: Callable[[], tuple[str, str]],
        writer: Callable[[str | None, str], str],
        readback: Callable[[], tuple[str, str]],
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.readback = readback

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        try:
            current_text, current_ref = self.reader()
        except Exception as exc:
            raise ConversationEventStoreError("event store read failed") from exc
        if not isinstance(current_ref, str) or not current_ref:
            raise ConversationEventStoreError("current storage reference required")

        current = parse_events_jsonl(current_text)
        prior_root = verification_root(current)
        successor, new_event_hash = append_event_candidate(current, event)
        successor_text = serialize_events_jsonl(successor)

        try:
            write_ref = self.writer(prior_root, successor_text)
        except Exception as exc:
            raise ConversationEventStoreError("event store compare-and-swap failed") from exc
        if not isinstance(write_ref, str) or not write_ref:
            raise ConversationEventStoreError("event store write reference required")

        try:
            readback_text, readback_ref = self.readback()
        except Exception as exc:
            raise ConversationEventStoreError("event store readback failed") from exc
        if not isinstance(readback_ref, str) or not readback_ref:
            raise ConversationEventStoreError("event store readback reference required")
        if readback_text != successor_text:
            raise ConversationEventStoreError("event store exact readback mismatch")

        observed = parse_events_jsonl(readback_text)
        observed_root = verification_root(observed)
        if observed_root != new_event_hash:
            raise ConversationEventStoreError("event store verification root mismatch")
        if observed[-1] != successor[-1]:
            raise ConversationEventStoreError("event store terminal event mismatch")

        return {
            "schema": "stegverse.kv.conversation-event-append-receipt/v1",
            "chain_ref": CHAIN_REF,
            "event_id": observed[-1]["event_id"],
            "event_hash": new_event_hash,
            "prior_verification_root": prior_root,
            "verification_root": observed_root,
            "event_count": len(observed),
            "prior_storage_ref": current_ref,
            "write_ref": write_ref,
            "readback_ref": readback_ref,
            "exact_readback_verified": True,
            "authority_transfer": False,
            "execution_authority": "NONE",
            "credential_authority": "TV/TVC",
            "authority_effect": "NONE",
        }
