#!/usr/bin/env python3
"""Deterministic semantic validator for the SKAP/InTr review candidate.

This validator is intentionally dependency-free. JSON Schema validation may be run
separately; this file enforces topology and authority semantics that are easier to
express deterministically in code.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

EXPECTED_ROLES = ["SKAP", "KV", "DEVICE", "EXTERNAL_NETWORK", "ENDPOINT"]
EXPECTED_EDGES = [
    ("SKAP", "KV"),
    ("KV", "DEVICE"),
    ("DEVICE", "EXTERNAL_NETWORK"),
    ("EXTERNAL_NETWORK", "ENDPOINT"),
]
EXPECTED_PATH = "SKAP <-InTr-> KV <-InTr-> Device <-InTr-> External Network <-InTr-> Endpoint"
EXPECTED_GATE = "VERIFIED_INTENDED_ENDPOINT_SESSION_AND_VALID_OPERATION_GRANT"


def validate(candidate: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if candidate.get("schema") != "stegverse.skap_intr.review_candidate/v1":
        errors.append("unsupported schema")
    if candidate.get("status") != "REVIEW_CANDIDATE":
        errors.append("status must remain REVIEW_CANDIDATE until review acceptance")

    protocol = candidate.get("protocol", {})
    expected_protocol = {
        "name": "Interlock/Transport",
        "abbreviation": "InTr",
        "relationship_symbol": "<-InTr->",
        "bidirectional": True,
        "authority_transfer": False,
        "fail_mode": "FAIL_CLOSED",
    }
    for key, value in expected_protocol.items():
        if protocol.get(key) != value:
            errors.append(f"protocol.{key} must equal {value!r}")

    nodes = candidate.get("nodes")
    if not isinstance(nodes, list):
        errors.append("nodes must be a list")
        nodes = []
    roles = [n.get("role") for n in nodes if isinstance(n, dict)]
    if roles != EXPECTED_ROLES:
        errors.append(f"node role order must be exactly {EXPECTED_ROLES}")
    if len(set(roles)) != len(roles):
        errors.append("node roles must be unique")

    by_role = {n.get("role"): n for n in nodes if isinstance(n, dict)}
    for role in EXPECTED_ROLES:
        node = by_role.get(role)
        if not node:
            continue
        claims = node.get("authority_claims", {})
        if role == "SKAP":
            if claims.get("secret_custody") is not True:
                errors.append("SKAP must explicitly own secret custody")
            for field in ("identity", "continuity", "governance", "execution"):
                if claims.get(field) is not False:
                    errors.append(f"SKAP must not claim {field} authority")
        else:
            for field in ("identity", "continuity", "governance", "execution", "secret_custody"):
                if claims.get(field) is not False:
                    errors.append(f"{role} must not inherit {field} authority in this review candidate")
        if role != "ENDPOINT" and node.get("may_hold_plaintext_secret") is not False:
            errors.append(f"{role} must not hold plaintext secret material")

    relationships = candidate.get("relationships")
    if not isinstance(relationships, list):
        errors.append("relationships must be a list")
        relationships = []
    edges = [(r.get("left"), r.get("right")) for r in relationships if isinstance(r, dict)]
    if edges != EXPECTED_EDGES:
        errors.append(f"InTr adjacency must be exactly {EXPECTED_EDGES}")
    for rel in relationships:
        if not isinstance(rel, dict):
            errors.append("relationship entries must be objects")
            continue
        if rel.get("protocol") != "InTr":
            errors.append(f"{rel.get('id')}: protocol must be InTr")
        if rel.get("bidirectional") is not True:
            errors.append(f"{rel.get('id')}: InTr must be bidirectional")
        if rel.get("verify_next_boundary_before_interpretation") is not True:
            errors.append(f"{rel.get('id')}: next boundary must be verified before interpretation")
        if rel.get("authority_transfer") is not False:
            errors.append(f"{rel.get('id')}: InTr must not transfer authority")
        if rel.get("protected_payload_sealed_in_transit") is not True:
            errors.append(f"{rel.get('id')}: protected payload must remain sealed in transit")
        if rel.get("receipt_required") is not True:
            errors.append(f"{rel.get('id')}: receipt is required")

    invariants = candidate.get("global_invariants", {})
    if invariants.get("canonical_path") != EXPECTED_PATH:
        errors.append("canonical_path mismatch")
    if invariants.get("non_adjacent_direct_edges_allowed") is not False:
        errors.append("non-adjacent direct edges must be prohibited")
    if invariants.get("secret_resolution_gate") != EXPECTED_GATE:
        errors.append("secret resolution must require verified intended endpoint/session plus valid operation grant")
    if invariants.get("return_path_uses_intr") is not True:
        errors.append("return path must use InTr")
    if invariants.get("return_path_secret_plaintext_allowed") is not False:
        errors.append("return path must not carry secret plaintext")
    if invariants.get("ambiguous_transition_disposition") != "FAIL_CLOSED":
        errors.append("ambiguous transitions must fail closed")
    if invariants.get("model_output_grants_execution_authority") is not False:
        errors.append("model output must not grant execution authority")

    return errors


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("candidate must be a JSON object")
    return value


def require_rejected(base: dict[str, Any], mutate, expected_fragment: str) -> None:
    candidate = copy.deepcopy(base)
    mutate(candidate)
    errors = validate(candidate)
    if not errors:
        raise AssertionError(f"negative fixture unexpectedly passed: {expected_fragment}")
    if not any(expected_fragment in error for error in errors):
        raise AssertionError(f"negative fixture rejected for wrong reason: wanted {expected_fragment!r}, got {errors!r}")


def self_test(base: dict[str, Any]) -> None:
    baseline_errors = validate(base)
    if baseline_errors:
        raise AssertionError("baseline candidate failed: " + "; ".join(baseline_errors))

    require_rejected(
        base,
        lambda c: c["relationships"].__setitem__(1, {**c["relationships"][1], "right": "ENDPOINT"}),
        "InTr adjacency",
    )
    require_rejected(
        base,
        lambda c: c["relationships"][0].__setitem__("authority_transfer", True),
        "must not transfer authority",
    )
    require_rejected(
        base,
        lambda c: c["relationships"][2].__setitem__("protected_payload_sealed_in_transit", False),
        "protected payload must remain sealed",
    )
    require_rejected(
        base,
        lambda c: c["global_invariants"].__setitem__("secret_resolution_gate", "ARRIVAL_AT_ANY_ENDPOINT"),
        "secret resolution",
    )
    require_rejected(
        base,
        lambda c: c["global_invariants"].__setitem__("return_path_secret_plaintext_allowed", True),
        "return path must not carry secret plaintext",
    )
    require_rejected(
        base,
        lambda c: c["nodes"][2]["authority_claims"].__setitem__("secret_custody", True),
        "DEVICE must not inherit secret_custody authority",
    )
    require_rejected(
        base,
        lambda c: c["nodes"][3].__setitem__("may_hold_plaintext_secret", True),
        "EXTERNAL_NETWORK must not hold plaintext secret material",
    )
    print("SKAP_INTR_REVIEW_CANDIDATE_SELF_TEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    candidate = load(args.candidate)
    errors = validate(candidate)
    if errors:
        print(json.dumps({"decision": "BLOCK", "errors": errors}, indent=2, sort_keys=True))
        return 1

    if args.self_test:
        self_test(candidate)

    print(json.dumps({
        "decision": "ALLOW_REVIEW",
        "schema": candidate["schema"],
        "status": candidate["status"],
        "topology": candidate["global_invariants"]["canonical_path"],
        "semantic_errors": []
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
