#!/usr/bin/env python3
"""Validate cross-KV-class InTr transitions and authority isolation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "kv-cross-class-intr-transition.example.v1.json"

DOMAIN = {
    "PERSONAL_KV": "PERSON",
    "ORGANIZATIONAL_KV": "ORGANIZATION",
    "STEGVERSE_KV": "STEGVERSE_ECOSYSTEM",
    "MACHINE_KV": "MACHINE_EXECUTION_ENTITY",
}


def validate(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "stegverse.kv.cross-class-intr-transition/v1":
        failures.append("unexpected schema")

    source = payload.get("source", {})
    target = payload.get("target", {})
    for label, endpoint in (("source", source), ("target", target)):
        kv_class = endpoint.get("kv_class")
        if kv_class not in DOMAIN:
            failures.append(f"{label}: unknown kv_class")
        elif endpoint.get("authority_domain") != DOMAIN[kv_class]:
            failures.append(f"{label}: authority_domain mismatch")

    transport = payload.get("transport", {})
    if transport.get("protocol") != "InTr":
        failures.append("cross-class transport must be InTr")
    if transport.get("interlock_required") is not True:
        failures.append("cross-class transition requires Interlock")
    if transport.get("direct_state_mutation") is not False:
        failures.append("direct cross-class state mutation is forbidden")

    authority = payload.get("authority", {})
    for key in (
        "authority_transfer",
        "context_share_grants_authority",
        "model_output_grants_authority",
        "provider_grants_authority",
    ):
        if authority.get(key) is not False:
            failures.append(f"{key} must be false")

    receipt = payload.get("receipt", {})
    if receipt.get("required") is not True:
        failures.append("receipt is mandatory")
    if receipt.get("contains_secret_plaintext") is not False:
        failures.append("receipt may not contain secret plaintext")
    for key in ("source_state_hash", "target_admission_hash"):
        value = receipt.get(key)
        if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
            failures.append(f"{key} must be sha256-prefixed 64-hex digest")

    return failures


def main() -> int:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    failures = validate(payload)
    if failures:
        print("KV_CROSS_CLASS_INTR_TRANSITION_FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("KV_CROSS_CLASS_INTR_TRANSITION_PASS")
    print("AUTHORITY_TRANSFER=false")
    print("DIRECT_STATE_MUTATION=false")
    print("RECEIPT_REQUIRED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
