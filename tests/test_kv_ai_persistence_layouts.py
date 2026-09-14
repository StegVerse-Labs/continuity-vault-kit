from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.validate_kv_ai_persistence_layouts import validate

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/kv-ai-persistence-layouts.v1.json"


def load():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def expect_failure(mutator, expected_fragment: str):
    value = copy.deepcopy(load())
    mutator(value)
    failures = validate(value)
    assert any(expected_fragment in failure for failure in failures), failures


def test_baseline_passes():
    assert validate(load()) == []


def test_requires_exact_four_classes():
    expect_failure(lambda v: v["layouts"].pop(), "exact four KV classes required")


def test_organizational_layout_requires_policy_domain():
    def mutate(v):
        row = next(x for x in v["layouts"] if x["kv_class"] == "ORGANIZATIONAL_KV")
        row["state_domains"] = [x for x in row["state_domains"] if x["name"] != "policy"]
    expect_failure(mutate, "ORGANIZATIONAL_KV missing state domains: policy")


def test_stegverse_layout_cannot_make_model_authority():
    def mutate(v):
        next(x for x in v["layouts"] if x["kv_class"] == "STEGVERSE_KV")["model_is_authority"] = True
    expect_failure(mutate, "STEGVERSE_KV model may not be authority")


def test_machine_layout_cannot_make_provider_authority():
    def mutate(v):
        next(x for x in v["layouts"] if x["kv_class"] == "MACHINE_KV")["provider_is_authority"] = True
    expect_failure(mutate, "MACHINE_KV provider may not be authority")


def test_direct_cross_class_mutation_remains_forbidden():
    def mutate(v):
        next(x for x in v["layouts"] if x["kv_class"] == "ORGANIZATIONAL_KV")["direct_cross_class_mutation"] = True
    expect_failure(mutate, "ORGANIZATIONAL_KV direct cross-class mutation must be forbidden")


def test_every_state_domain_requires_intr_admission():
    def mutate(v):
        row = next(x for x in v["layouts"] if x["kv_class"] == "MACHINE_KV")
        row["state_domains"][0]["mutable_only_after_intr_admission"] = False
    expect_failure(mutate, "MACHINE_KV state domain must require InTr admission")


def test_rejects_parent_traversal_path():
    def mutate(v):
        row = next(x for x in v["layouts"] if x["kv_class"] == "STEGVERSE_KV")
        row["state_domains"][0]["relative_path"] = "../escape"
    expect_failure(mutate, "STEGVERSE_KV unsafe state domain path")


def test_shared_intr_invariant_cannot_be_disabled():
    expect_failure(lambda v: v["shared_invariants"].__setitem__("intr_required", False), "shared invariant intr_required mismatch")
