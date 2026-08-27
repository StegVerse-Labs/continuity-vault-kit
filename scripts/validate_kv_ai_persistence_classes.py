#!/usr/bin/env python3
"""Validate StegVerse KV AI persistence class invariants."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "kv-ai-persistence-classes.v1.json"

EXPECTED = {
    "PERSONAL_KV": ("PERSON", "PERSONAL_ASSISTANT_AI"),
    "ORGANIZATIONAL_KV": ("ORGANIZATION", "ORGANIZATIONAL_AI"),
    "STEGVERSE_KV": ("STEGVERSE_ECOSYSTEM", "STEGVERSE_AI"),
    "MACHINE_KV": ("MACHINE_EXECUTION_ENTITY", "EXECUTION_AGENT"),
}


def validate(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "stegverse.kv.ai-persistence-classes/v1":
        failures.append("unexpected schema")

    classes = payload.get("classes")
    if not isinstance(classes, list):
        return failures + ["classes must be a list"]

    seen: set[str] = set()
    for item in classes:
        kv_class = item.get("kv_class")
        if kv_class in seen:
            failures.append(f"duplicate kv_class: {kv_class}")
        seen.add(kv_class)

        if kv_class not in EXPECTED:
            failures.append(f"unknown kv_class: {kv_class}")
            continue

        authority_domain, ai_role = EXPECTED[kv_class]
        if item.get("authority_domain") != authority_domain:
            failures.append(f"{kv_class}: authority_domain mismatch")
        if item.get("ai_role") != ai_role:
            failures.append(f"{kv_class}: ai_role mismatch")
        if item.get("skap_required") is not True:
            failures.append(f"{kv_class}: SKAP must be required")
        if item.get("intr_required") is not True:
            failures.append(f"{kv_class}: InTr must be required")
        if item.get("provider_is_authority") is not False:
            failures.append(f"{kv_class}: provider may not be authority")
        if item.get("model_is_authority") is not False:
            failures.append(f"{kv_class}: model may not be authority")
        state = item.get("persistent_state")
        if not isinstance(state, list) or not state:
            failures.append(f"{kv_class}: persistent_state must be non-empty")

    missing = set(EXPECTED) - seen
    if missing:
        failures.append("missing kv classes: " + ",".join(sorted(missing)))

    invariants = payload.get("cross_class_invariants", {})
    if invariants.get("authority_transfer_on_context_share") is not False:
        failures.append("context sharing must not transfer authority")
    if invariants.get("direct_cross_class_state_mutation") is not False:
        failures.append("direct cross-class state mutation must be forbidden")
    if invariants.get("intr_receipt_required") is not True:
        failures.append("cross-class transition must require InTr receipt")
    if invariants.get("least_authority") is not True:
        failures.append("least-authority invariant must be true")
    if invariants.get("fail_closed_on_ambiguous_scope") is not True:
        failures.append("ambiguous authority scope must fail closed")

    return failures


def main() -> int:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    failures = validate(payload)
    if failures:
        print("KV_AI_PERSISTENCE_CLASSES_FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("KV_AI_PERSISTENCE_CLASSES_PASS")
    print("KV_CLASS_COUNT=4")
    print("AUTHORITY_TRANSFER_ON_CONTEXT_SHARE=false")
    print("DIRECT_CROSS_CLASS_STATE_MUTATION=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
