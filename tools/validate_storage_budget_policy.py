#!/usr/bin/env python3
"""Dependency-light validator for governed storage budget policies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def validate_policy(policy: dict[str, Any]) -> None:
    required_top = {
        "schema_version", "policy_id", "policy_version", "reconstruction_goal",
        "material_properties", "capacity_budget", "capture_plan",
        "budget_exhaustion_behavior", "receipt_policy",
    }
    missing = sorted(required_top - policy.keys())
    _require(not missing, f"missing top-level fields: {missing}")
    _require(policy["schema_version"] == "0.1", "schema_version must be 0.1")

    properties = policy["material_properties"]
    _require(isinstance(properties, list) and properties, "material_properties must be non-empty")
    required_properties: set[str] = set()
    omitted_properties: set[str] = set()
    for item in properties:
        name = item.get("property")
        requirement = item.get("requirement")
        refs = item.get("coverage_refs", [])
        _require(name and requirement, "each material property needs property and requirement")
        if requirement == "required":
            _require(bool(refs), f"required property {name} has no coverage_refs")
            required_properties.add(name)
        elif requirement == "omitted":
            _require(not refs, f"omitted property {name} must not have coverage_refs")
            _require(bool(item.get("omission_reason")), f"omitted property {name} needs omission_reason")
            omitted_properties.add(name)

    budget = policy["capacity_budget"]
    _require(budget.get("ephemeral_compute_excluded") is True, "ephemeral compute must be excluded")
    _require(int(budget.get("continuity_receipt_reserve_bytes", 0)) > 0, "continuity receipt reserve must be positive")
    _require(float(budget.get("replication_allowance", 0)) >= 1, "replication allowance must be at least 1")
    allocations = sum(int(budget.get(k, 0)) for k in ("local_bytes", "protected_evidence_bytes", "archival_bytes", "continuity_receipt_reserve_bytes"))
    _require(allocations <= int(budget["max_bytes_per_episode"]), "durable allocations exceed episode budget")

    streams = policy["capture_plan"].get("streams", [])
    _require(streams, "capture plan must contain streams")
    stream_ids = {s.get("stream_ref") for s in streams}
    _require(None not in stream_ids and len(stream_ids) == len(streams), "stream_ref values must be unique and non-empty")
    covered = {p for stream in streams if stream.get("enabled") for p in stream.get("covered_properties", [])}
    _require(required_properties <= covered, f"required properties lack enabled stream coverage: {sorted(required_properties - covered)}")
    declared_omissions = set(policy["capture_plan"].get("declared_omissions", []))
    _require(omitted_properties <= declared_omissions, "all omitted properties must be declared by capture_plan")

    for rule in policy.get("adaptive_sampling_rules", []):
        _require(rule.get("required_properties_preserved") is True, f"adaptive rule {rule.get('rule_id')} may drop required properties")
        _require(rule.get("receipt_required") is True, f"adaptive rule {rule.get('rule_id')} must require receipt")
        _require(set(rule.get("affected_stream_refs", [])) <= stream_ids, f"adaptive rule {rule.get('rule_id')} references unknown stream")

    for rule in policy.get("fidelity_elevation_rules", []):
        _require(rule.get("authority_required") is True, f"elevation rule {rule.get('rule_id')} must require authority")
        _require(rule.get("receipt_required") is True, f"elevation rule {rule.get('rule_id')} must require receipt")
        _require(set(rule.get("affected_stream_refs", [])) <= stream_ids, f"elevation rule {rule.get('rule_id')} references unknown stream")

    for substitution in policy.get("sensor_substitutions", []):
        _require(set(substitution.get("replaced_stream_refs", [])) <= stream_ids, "substitution references unknown replaced stream")
        _require(set(substitution.get("substitute_stream_refs", [])) <= stream_ids, "substitution references unknown substitute stream")
        lost_required = required_properties & set(substitution.get("lost_properties", []))
        _require(not lost_required, f"substitution silently loses required properties: {sorted(lost_required)}")

    behavior = policy["budget_exhaustion_behavior"]
    loss = policy.get("capability_loss_policy")
    if behavior in {"preserve_continuity_only", "fail_closed_for_declared_goal", "end_episode_capture"}:
        _require(isinstance(loss, dict), "capability_loss_policy required for goal-ending behavior")
        _require(loss.get("emit_declaration") is True, "capability loss must emit declaration")
        _require(loss.get("goal_may_remain_satisfied_after_required_property_loss") is False, "required-property loss cannot preserve goal satisfaction")

    events = set(policy["receipt_policy"].get("events", []))
    _require("initial_capture_plan" in events, "initial_capture_plan receipt is required")
    _require("budget_exhaustion" in events, "budget_exhaustion receipt is required")
    _require(policy["receipt_policy"].get("integrity_algorithm") in {"sha256", "sha384", "sha512", "blake3"}, "unsupported integrity algorithm")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        try:
            validate_policy(json.loads(path.read_text(encoding="utf-8")))
            print(f"PASS {path}")
        except (OSError, json.JSONDecodeError, PolicyError) as exc:
            failed = True
            print(f"FAIL {path}: {exc}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
