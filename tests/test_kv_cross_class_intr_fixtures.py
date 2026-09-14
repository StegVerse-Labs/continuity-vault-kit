from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.validate_kv_cross_class_intr_fixtures import validate_fixture_set

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/kv-cross-class-intr-transition-fixtures.v1.json"


def load():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def expect_failure(mutator, expected_fragment: str):
    value = copy.deepcopy(load())
    mutator(value)
    failures = validate_fixture_set(value)
    assert any(expected_fragment in failure for failure in failures), failures


def test_complete_directed_matrix_passes():
    assert validate_fixture_set(load()) == []


def test_missing_pair_fails():
    expect_failure(lambda v: v["fixtures"].pop(), "missing directed fixture pairs")


def test_duplicate_pair_fails():
    def mutate(v):
        v["fixtures"][-1]["source_class"] = v["fixtures"][0]["source_class"]
        v["fixtures"][-1]["target_class"] = v["fixtures"][0]["target_class"]
    expect_failure(mutate, "duplicate fixture pair")


def test_same_class_pair_fails():
    def mutate(v):
        v["fixtures"][0]["target_class"] = v["fixtures"][0]["source_class"]
    expect_failure(mutate, "cross-class pairs only")


def test_authority_transfer_mutation_fails_every_expanded_fixture():
    expect_failure(lambda v: v["fixture_contract"].__setitem__("authority_transfer", True), "authority_transfer must be false")


def test_direct_mutation_mutation_fails():
    expect_failure(lambda v: v["fixture_contract"].__setitem__("direct_state_mutation", True), "direct cross-class state mutation is forbidden")


def test_secret_plaintext_mutation_fails():
    expect_failure(lambda v: v["fixture_contract"].__setitem__("contains_secret_plaintext", True), "receipt may not contain secret plaintext")


def test_receipt_requirement_cannot_be_disabled():
    expect_failure(lambda v: v["fixture_contract"].__setitem__("receipt_required", False), "receipt is mandatory")
