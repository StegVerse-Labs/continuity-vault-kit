#!/usr/bin/env python3
"""Validate concrete KV AI persistence layouts against canonical class invariants."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/kv-ai-persistence-layouts.v1.json"

EXPECTED = {
    "PERSONAL_KV": ("PERSON", "PERSONAL_ASSISTANT_AI", {"continuity", "personal_resources", "personal_modules", "ai_review", "receipts"}),
    "ORGANIZATIONAL_KV": ("ORGANIZATION", "ORGANIZATIONAL_AI", {"policy", "roles", "delegations", "shared_resources", "workflows", "institutional_memory", "receipts"}),
    "STEGVERSE_KV": ("STEGVERSE_ECOSYSTEM", "STEGVERSE_AI", {"ecosystem_state", "service_registry", "governance_state", "worker_state", "evidence", "recovery", "receipts"}),
    "MACHINE_KV": ("MACHINE_EXECUTION_ENTITY", "EXECUTION_AGENT", {"node_identity", "workloads", "assignments", "execution_state", "liveness", "checkpoints", "reconstruction", "receipts"}),
}


def validate(value: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if value.get("schema") != "stegverse.kv.ai-persistence-layouts/v1":
        failures.append("schema mismatch")
    layouts = value.get("layouts")
    if not isinstance(layouts, list):
        return failures + ["layouts missing"]
    observed = {item.get("kv_class"): item for item in layouts if isinstance(item, dict)}
    if set(observed) != set(EXPECTED):
        failures.append("exact four KV classes required")
    for kv_class, (authority, role, domains) in EXPECTED.items():
        row = observed.get(kv_class)
        if not isinstance(row, dict):
            continue
        if row.get("authority_domain") != authority:
            failures.append(f"{kv_class} authority_domain mismatch")
        if row.get("ai_role") != role:
            failures.append(f"{kv_class} ai_role mismatch")
        if row.get("direct_cross_class_mutation") is not False:
            failures.append(f"{kv_class} direct cross-class mutation must be forbidden")
        if row.get("provider_is_authority") is not False:
            failures.append(f"{kv_class} provider may not be authority")
        if row.get("model_is_authority") is not False:
            failures.append(f"{kv_class} model may not be authority")
        state_domains = row.get("state_domains")
        if not isinstance(state_domains, list):
            failures.append(f"{kv_class} state_domains missing")
            continue
        names = {item.get("name") for item in state_domains if isinstance(item, dict)}
        missing = sorted(domains - names)
        if missing:
            failures.append(f"{kv_class} missing state domains: {','.join(missing)}")
        paths: set[str] = set()
        for item in state_domains:
            if not isinstance(item, dict):
                failures.append(f"{kv_class} malformed state domain")
                continue
            path = item.get("relative_path")
            if not isinstance(path, str) or not path or path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
                failures.append(f"{kv_class} unsafe state domain path")
            elif path in paths:
                failures.append(f"{kv_class} duplicate state domain path")
            else:
                paths.add(path)
            if item.get("mutable_only_after_intr_admission") is not True:
                failures.append(f"{kv_class} state domain must require InTr admission")
        receipt_root = row.get("receipt_root")
        if not isinstance(receipt_root, str) or receipt_root not in paths:
            failures.append(f"{kv_class} receipt_root must name a state domain path")
        cap_root = row.get("capability_ref_root")
        if not isinstance(cap_root, str) or not cap_root:
            failures.append(f"{kv_class} capability_ref_root required")
    invariants = value.get("shared_invariants")
    required = {
        "skap_required": True,
        "intr_required": True,
        "cross_class_receipt_required": True,
        "least_authority": True,
        "fail_closed_on_ambiguous_scope": True,
    }
    if not isinstance(invariants, dict):
        failures.append("shared_invariants missing")
    else:
        for key, expected in required.items():
            if invariants.get(key) is not expected:
                failures.append(f"shared invariant {key} mismatch")
    return failures


def main() -> int:
    value = json.loads(SPEC.read_text(encoding="utf-8"))
    failures = validate(value)
    if failures:
        print("KV_AI_PERSISTENCE_LAYOUTS_VALIDATION=FAIL")
        for failure in failures:
            print(f"FAIL={failure}")
        return 1
    print("KV_AI_PERSISTENCE_LAYOUTS_VALIDATION=PASS")
    print("KV_LAYOUT_CLASS_COUNT=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
