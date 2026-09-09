#!/usr/bin/env python3
"""Materialize a non-authorizing ephemeral browser projection context from KV receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PURPOSE = "CURRENT_IPHONE_TESTFLIGHT_SIGNING"
ENTRY_SCHEMA = "stegverse.kv.entry-transition-admission/v1"
CAPABILITY_SCHEMA = "stegverse.kv.browser-capability-observation/v1"
OUTPUT_SCHEMA = "stegos.kv-bound-ephemeral-projection-context/v1"


def _canonical_digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    suffix = value[7:]
    if any(c not in "0123456789abcdef" for c in suffix):
        raise ValueError(f"{field} must be sha256:<64 lowercase hex>")
    return value


def validate_entry(entry: dict) -> str:
    if entry.get("schema") != ENTRY_SCHEMA:
        raise ValueError("KV entry receipt schema mismatch")
    if entry.get("purpose") != PURPOSE:
        raise ValueError("KV entry purpose mismatch")
    if entry.get("state") != "ADMITTED":
        raise ValueError("KV entry must be ADMITTED")
    if entry.get("authority_effect") != "NONE":
        raise ValueError("KV entry authority_effect must be NONE")
    if entry.get("continuity_boundary") != "KV":
        raise ValueError("KV entry continuity boundary mismatch")
    return _require_digest(entry.get("transition_commitment"), "transition_commitment")


def validate_capability(capability: dict) -> str:
    if capability.get("schema") != CAPABILITY_SCHEMA:
        raise ValueError("browser capability receipt schema mismatch")
    if capability.get("purpose") != PURPOSE:
        raise ValueError("browser capability purpose mismatch")
    if capability.get("state") != "OBSERVED_COMPATIBLE":
        raise ValueError("browser capability must be OBSERVED_COMPATIBLE")
    if capability.get("authority_effect") != "NONE":
        raise ValueError("browser capability authority_effect must be NONE")
    if capability.get("continuity_boundary") != "KV":
        raise ValueError("browser capability continuity boundary mismatch")
    if capability.get("browser_identity_authority") is not False:
        raise ValueError("browser identity may not be authority")
    return _require_digest(capability.get("capability_commitment"), "capability_commitment")


def materialize(entry: dict, capability: dict) -> dict:
    transition_commitment = validate_entry(entry)
    capability_commitment = validate_capability(capability)
    if entry.get("kv_lineage_id") != capability.get("kv_lineage_id"):
        raise ValueError("KV lineage mismatch")
    if not isinstance(entry.get("kv_lineage_id"), str) or not entry["kv_lineage_id"]:
        raise ValueError("KV lineage id missing")
    admission_commitment = _canonical_digest({
        "schema": ENTRY_SCHEMA,
        "purpose": PURPOSE,
        "state": "ADMITTED",
        "kv_lineage_id": entry["kv_lineage_id"],
        "transition_commitment": transition_commitment,
        "entry_receipt_commitment": _canonical_digest(entry),
    })
    return {
        "schema": OUTPUT_SCHEMA,
        "purpose": PURPOSE,
        "entry_state": "ADMITTED",
        "kv_transition_commitment": transition_commitment,
        "admission_commitment": admission_commitment,
        "browser_capability_state": "OBSERVED_COMPATIBLE",
        "browser_capability_commitment": capability_commitment,
        "persistence_effect": "NONE_EPHEMERAL_CONTEXT_ONLY",
        "authority_effect": "NONE_PROJECTION_GATE_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("entry_receipt", type=Path)
    parser.add_argument("browser_capability_receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        entry = json.loads(args.entry_receipt.read_text(encoding="utf-8"))
        capability = json.loads(args.browser_capability_receipt.read_text(encoding="utf-8"))
        context = materialize(entry, capability)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("KV_EPHEMERAL_BROWSER_PROJECTION_CONTEXT_FAIL")
        print(str(exc))
        return 1
    args.output.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    print("KV_EPHEMERAL_BROWSER_PROJECTION_CONTEXT_PASS")
    print(f"PURPOSE={PURPOSE}")
    print("AUTHORITY_EFFECT=NONE_PROJECTION_GATE_ONLY")
    print("PERSISTENCE_EFFECT=NONE_EPHEMERAL_CONTEXT_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
