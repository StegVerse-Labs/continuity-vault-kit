#!/usr/bin/env python3
"""Deterministic tests for governed KV-backed AI memory context."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.kv_ai_memory_substrate import (  # noqa: E402
    MemorySubstrateError,
    build_context_packet,
    build_write_proposal,
)


REQUEST = {
    "schema": "stegverse.kv.ai-memory-context-request/v1",
    "request_id": "REQ-AURI-ERL-001",
    "kv_class": "PERSONAL_KV",
    "authority_domain": "PERSON",
    "consumer_ai_role": "PERSONAL_ASSISTANT_AI",
    "source_kv_instance_ids": ["KV-INSTANCE-1"],
    "purpose": "Recover prior ERL research context for the current conversation",
    "query_terms": ["ERL", "AI funding"],
    "max_items": 3,
    "max_bytes": 4096,
    "intr_admission_required": True,
    "authority_effect": "NONE_CONTEXT_REQUEST_ONLY",
}

ENTRIES = [
    {
        "entry_id": "MEM-ERL-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "source_kv_instance_id": "KV-INSTANCE-1",
        "relative_path": "02_Research/ERL/ai-influence.md",
        "title": "ERL AI influence research continuity",
        "content": "ERL tracks primary-source funding and advocacy edges related to AI access and data-center opposition.",
        "tags": ["ERL", "AI funding", "research"],
        "retention_class": "DURABLE",
        "provenance_ref": "ERL-EDUCATIONAL-ACCESS-INFLUENCE-001",
        "ai_context_allowed": True,
        "secret_material": False,
        "priority": 10,
    },
    {
        "entry_id": "MEM-OTHER-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "source_kv_instance_id": "KV-INSTANCE-1",
        "relative_path": "05_Projects/unrelated.md",
        "title": "Unrelated project",
        "content": "This record does not concern the requested research topic.",
        "tags": ["other"],
        "retention_class": "PROJECT",
        "provenance_ref": "PROJECT-OTHER-001",
        "ai_context_allowed": True,
        "secret_material": False,
        "priority": 1,
    },
]


def expect_failure(fn, fragment: str) -> None:
    try:
        fn()
    except MemorySubstrateError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"expected MemorySubstrateError containing {fragment!r}")


def test_relevant_context_selected_with_provenance() -> None:
    packet = build_context_packet(copy.deepcopy(REQUEST), copy.deepcopy(ENTRIES))
    assert packet["selected_item_count"] == 1
    assert packet["entries"][0]["entry_id"] == "MEM-ERL-001"
    assert packet["entries"][0]["provenance_ref"] == "ERL-EDUCATIONAL-ACCESS-INFLUENCE-001"
    assert packet["secret_material_included"] is False
    assert packet["cross_authority_content_included"] is False
    assert packet["authority_effect"] == "NONE_CONTEXT_ONLY"


def test_context_packet_is_deterministic() -> None:
    first = build_context_packet(copy.deepcopy(REQUEST), copy.deepcopy(ENTRIES))
    second = build_context_packet(copy.deepcopy(REQUEST), list(reversed(copy.deepcopy(ENTRIES))))
    assert first == second


def test_ai_eligible_secret_fails_closed() -> None:
    entries = copy.deepcopy(ENTRIES)
    entries[0]["secret_material"] = True
    expect_failure(lambda: build_context_packet(copy.deepcopy(REQUEST), entries), "secret material")


def test_cross_authority_entry_fails_closed() -> None:
    entries = copy.deepcopy(ENTRIES)
    entries[0]["kv_class"] = "ORGANIZATIONAL_KV"
    entries[0]["authority_domain"] = "ORGANIZATION"
    expect_failure(lambda: build_context_packet(copy.deepcopy(REQUEST), entries), "cross-class")


def test_model_cannot_request_mismatched_role() -> None:
    request = copy.deepcopy(REQUEST)
    request["consumer_ai_role"] = "STEGVERSE_AI"
    expect_failure(lambda: build_context_packet(request, copy.deepcopy(ENTRIES)), "consumer_ai_role")


def test_non_authorizing_write_proposal() -> None:
    packet = build_context_packet(copy.deepcopy(REQUEST), copy.deepcopy(ENTRIES))
    proposal = build_write_proposal(
        source_packet=packet,
        target_kv_instance_id="KV-INSTANCE-1",
        relative_path="01_Notes/Auri/session-continuity.md",
        content="ERL funding investigation context recovered and linked to the active task.",
        retention_class="PROJECT",
    )
    assert proposal["intr_admission_required"] is True
    assert proposal["execution_authorized"] is False
    assert proposal["model_is_authority"] is False
    assert proposal["authority_effect"] == "NONE_PROPOSAL_ONLY"


def test_oversized_entry_is_skipped_not_truncated() -> None:
    request = copy.deepcopy(REQUEST)
    request["max_bytes"] = 256
    entries = copy.deepcopy(ENTRIES)
    entries[0]["content"] = "ERL " + ("x" * 600)
    packet = build_context_packet(request, entries)
    assert packet["selected_item_count"] == 0
    assert packet["selected_content_bytes"] == 0


if __name__ == "__main__":
    tests = [
        test_relevant_context_selected_with_provenance,
        test_context_packet_is_deterministic,
        test_ai_eligible_secret_fails_closed,
        test_cross_authority_entry_fails_closed,
        test_model_cannot_request_mismatched_role,
        test_non_authorizing_write_proposal,
        test_oversized_entry_is_skipped_not_truncated,
    ]
    for test in tests:
        test()
    print(f"KV_AI_MEMORY_SUBSTRATE_TESTS_PASS={len(tests)}")
