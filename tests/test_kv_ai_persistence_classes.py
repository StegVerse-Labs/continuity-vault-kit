#!/usr/bin/env python3
"""Deterministic negative tests for KV AI persistence classes."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_kv_ai_persistence_classes import validate

SPEC = ROOT / "specs" / "kv-ai-persistence-classes.v1.json"


def load() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def expect_failure(mutator, expected_fragment: str) -> None:
    payload = copy.deepcopy(load())
    mutator(payload)
    failures = validate(payload)
    assert any(expected_fragment in item for item in failures), failures


def test_baseline_passes() -> None:
    assert validate(load()) == []


def test_context_share_never_transfers_authority() -> None:
    expect_failure(
        lambda p: p["cross_class_invariants"].__setitem__("authority_transfer_on_context_share", True),
        "context sharing must not transfer authority",
    )


def test_direct_cross_class_mutation_forbidden() -> None:
    expect_failure(
        lambda p: p["cross_class_invariants"].__setitem__("direct_cross_class_state_mutation", True),
        "direct cross-class state mutation must be forbidden",
    )


def test_provider_never_becomes_authority() -> None:
    expect_failure(
        lambda p: p["classes"][2].__setitem__("provider_is_authority", True),
        "provider may not be authority",
    )


def test_model_never_becomes_authority() -> None:
    expect_failure(
        lambda p: p["classes"][0].__setitem__("model_is_authority", True),
        "model may not be authority",
    )


def test_machine_kv_cannot_impersonate_personal_domain() -> None:
    expect_failure(
        lambda p: p["classes"][3].__setitem__("authority_domain", "PERSON"),
        "authority_domain mismatch",
    )


if __name__ == "__main__":
    tests = [
        test_baseline_passes,
        test_context_share_never_transfers_authority,
        test_direct_cross_class_mutation_forbidden,
        test_provider_never_becomes_authority,
        test_model_never_becomes_authority,
        test_machine_kv_cannot_impersonate_personal_domain,
    ]
    for test in tests:
        test()
    print(f"KV_AI_PERSISTENCE_NEGATIVE_TESTS_PASS={len(tests)}")
