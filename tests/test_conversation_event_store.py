from __future__ import annotations

import copy
import hashlib
import json

import pytest

from continuity.recall import sha256
from runtime.conversation_event_store import (
    CHAIN_REF,
    ConversationEventStore,
    ConversationEventStoreError,
    append_event_candidate,
    parse_events_jsonl,
    serialize_events_jsonl,
    verification_root,
)


def event(event_id="evt-001", timestamp="2026-08-30T20:00:00Z", content=None):
    if content is None:
        content = {
            "goal": "KV persistent session reconstruction",
            "status": "active",
        }
    return {
        "event_id": event_id,
        "previous_event_hash": None,
        "timestamp": timestamp,
        "actor": "assistant",
        "event_type": "implementation_recorded",
        "topic": "persistent session reconstruction",
        "subject_id": "kv-persistent-session-reconstruction",
        "supersedes": None,
        "content": content,
        "content_hash": sha256(content),
        "resulting_state_hash": hashlib.sha256(
            json.dumps(
                {"goal": "kv-persistent-session-reconstruction", "event": event_id},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "retention_class": "reconstructable",
        "fidelity": "semantic_reconstruction",
        "artifact_refs": [
            "KV_PERSISTENT_SESSION_RECONSTRUCTION_MIRROR_HANDOFF.md"
        ],
        "authority_context": {
            "execution_authority": "NONE",
            "credential_authority": "TV/TVC",
        },
        "policy_context": None,
    }


def test_genesis_append_and_jsonl_roundtrip():
    successor, root = append_event_candidate([], event())
    assert successor[0]["previous_event_hash"] is None
    text = serialize_events_jsonl(successor)
    parsed = parse_events_jsonl(text)
    assert parsed == successor
    assert verification_root(parsed) == root


def test_successor_is_bound_to_exact_prior_event_hash():
    first, first_root = append_event_candidate([], event())
    second, second_root = append_event_candidate(
        first,
        event("evt-002", "2026-08-30T20:01:00Z"),
    )
    assert second[1]["previous_event_hash"] == first_root
    assert second_root != first_root


def test_duplicate_and_timestamp_rollback_fail_closed():
    first, _ = append_event_candidate([], event())
    with pytest.raises(ConversationEventStoreError, match="duplicate event_id"):
        append_event_candidate(first, event())

    with pytest.raises(ConversationEventStoreError, match="timestamp rollback"):
        append_event_candidate(
            first,
            event("evt-002", "2026-08-30T19:59:59Z"),
        )


def test_content_hash_and_secret_or_transcript_fields_fail_closed():
    bad = event()
    bad["content_hash"] = "0" * 64
    with pytest.raises(ConversationEventStoreError, match="content hash mismatch"):
        append_event_candidate([], bad)

    bad = event(content={"transcript": "raw conversation"})
    with pytest.raises(ConversationEventStoreError, match="forbidden field"):
        append_event_candidate([], bad)

    bad = event(content={"token_hint": "forbidden"})
    with pytest.raises(ConversationEventStoreError, match="forbidden field"):
        append_event_candidate([], bad)


def test_store_requires_compare_and_swap_and_exact_readback():
    state = {"text": "", "ref": "kv://events/current"}
    writes = []

    def reader():
        return state["text"], state["ref"]

    def writer(expected_root, successor_text):
        assert expected_root is None
        writes.append((expected_root, successor_text))
        state["text"] = successor_text
        state["ref"] = "kv://events/version/1"
        return "kv://events/write/1"

    def readback():
        return state["text"], state["ref"]

    receipt = ConversationEventStore(
        reader=reader,
        writer=writer,
        readback=readback,
    ).append(event())

    assert receipt["chain_ref"] == CHAIN_REF
    assert receipt["event_count"] == 1
    assert receipt["exact_readback_verified"] is True
    assert receipt["event_hash"] == receipt["verification_root"]
    assert receipt["authority_transfer"] is False
    assert receipt["execution_authority"] == "NONE"
    assert receipt["credential_authority"] == "TV/TVC"
    assert writes


def test_store_rejects_ambiguous_write_and_readback_drift():
    state = {"text": "", "ref": "kv://events/current"}

    store = ConversationEventStore(
        reader=lambda: (state["text"], state["ref"]),
        writer=lambda _root, _text: "",
        readback=lambda: (state["text"], state["ref"]),
    )
    with pytest.raises(ConversationEventStoreError, match="write reference"):
        store.append(event())

    def writer(_root, successor):
        state["text"] = successor + "\n"
        return "kv://events/write/1"

    store = ConversationEventStore(
        reader=lambda: ("", "kv://events/current"),
        writer=writer,
        readback=lambda: (state["text"], "kv://events/version/1"),
    )
    with pytest.raises(ConversationEventStoreError, match="exact readback mismatch"):
        store.append(event())
