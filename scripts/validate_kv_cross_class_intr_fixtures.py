#!/usr/bin/env python3
"""Expand and validate every directed cross-KV-class InTr fixture."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_kv_cross_class_intr_transition import DOMAIN, validate as validate_transition

SPEC = ROOT / "specs/kv-cross-class-intr-transition-fixtures.v1.json"
CLASSES = tuple(DOMAIN)


def digest(seed: str) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def expand_fixture(row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    source = row["source_class"]
    target = row["target_class"]
    fixture_id = row["fixture_id"]
    return {
        "schema": "stegverse.kv.cross-class-intr-transition/v1",
        "transition_id": f"fixture-{fixture_id.lower()}",
        "source": {
            "kv_class": source,
            "authority_domain": DOMAIN[source],
            "state_ref": f"fixture://{source}/state/{fixture_id}",
        },
        "target": {
            "kv_class": target,
            "authority_domain": DOMAIN[target],
            "admission_ref": f"fixture://{target}/admission/{fixture_id}",
        },
        "transport": {
            "protocol": contract["protocol"],
            "interlock_required": contract["interlock_required"],
            "direct_state_mutation": contract["direct_state_mutation"],
        },
        "authority": {
            "authority_transfer": contract["authority_transfer"],
            "context_share_grants_authority": contract["context_share_grants_authority"],
            "model_output_grants_authority": contract["model_output_grants_authority"],
            "provider_grants_authority": contract["provider_grants_authority"],
        },
        "receipt": {
            "required": contract["receipt_required"],
            "source_state_hash": digest(f"{fixture_id}:source"),
            "target_admission_hash": digest(f"{fixture_id}:target"),
            "contains_secret_plaintext": contract["contains_secret_plaintext"],
        },
    }


def validate_fixture_set(value: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if value.get("schema") != "stegverse.kv.cross-class-intr-transition-fixtures/v1":
        failures.append("fixture set schema mismatch")
    fixtures = value.get("fixtures")
    contract = value.get("fixture_contract")
    if not isinstance(fixtures, list):
        return failures + ["fixtures missing"]
    if not isinstance(contract, dict):
        return failures + ["fixture_contract missing"]

    expected = {(source, target) for source in CLASSES for target in CLASSES if source != target}
    observed: set[tuple[str, str]] = set()
    ids: set[str] = set()
    for row in fixtures:
        if not isinstance(row, dict):
            failures.append("fixture row malformed")
            continue
        source, target, fixture_id = row.get("source_class"), row.get("target_class"), row.get("fixture_id")
        if source not in DOMAIN or target not in DOMAIN:
            failures.append("fixture uses unknown KV class")
            continue
        if source == target:
            failures.append("fixture matrix may contain cross-class pairs only")
        pair = (source, target)
        if pair in observed:
            failures.append(f"duplicate fixture pair {source}->{target}")
        observed.add(pair)
        if not isinstance(fixture_id, str) or not fixture_id:
            failures.append("fixture_id required")
        elif fixture_id in ids:
            failures.append(f"duplicate fixture_id {fixture_id}")
        ids.add(str(fixture_id))
        expanded = expand_fixture(row, contract)
        for failure in validate_transition(expanded):
            failures.append(f"{fixture_id}: {failure}")
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing:
        failures.append("missing directed fixture pairs: " + ",".join(f"{a}->{b}" for a, b in missing))
    if extra:
        failures.append("unexpected fixture pairs: " + ",".join(f"{a}->{b}" for a, b in extra))
    if len(fixtures) != 12:
        failures.append("exactly 12 directed cross-class fixtures required")
    return failures


def main() -> int:
    value = json.loads(SPEC.read_text(encoding="utf-8"))
    failures = validate_fixture_set(value)
    if failures:
        print("KV_CROSS_CLASS_INTR_FIXTURES_VALIDATION=FAIL")
        for failure in failures:
            print(f"FAIL={failure}")
        return 1
    print("KV_CROSS_CLASS_INTR_FIXTURES_VALIDATION=PASS")
    print("DIRECTED_PAIR_COUNT=12")
    print("AUTHORITY_TRANSFER=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
