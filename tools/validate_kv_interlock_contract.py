#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "schemas" / "kv-interlock-request.schema.json"
RESPONSE = ROOT / "schemas" / "kv-interlock-response.schema.json"


class ContractError(ValueError):
    pass


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def require_exact(value, expected, label: str) -> None:
    if value != expected:
        raise ContractError(f"{label} mismatch: {value!r} != {expected!r}")


def validate() -> dict:
    req = load(REQUEST)
    res = load(RESPONSE)

    require_exact(req["properties"]["schema_version"]["const"], "kv.interlock.request.v1", "request schema version")
    require_exact(res["properties"]["schema_version"]["const"], "kv.interlock.response.v1", "response schema version")

    require_exact(
        req["properties"]["operation"]["enum"],
        ["DISCOVER", "REQUEST", "COMMIT_CANDIDATE"],
        "operation vocabulary",
    )
    require_exact(
        res["properties"]["decision"]["enum"],
        ["ALLOW_BOUNDED_CONTEXT", "REVIEW_REQUIRED", "DENY", "FAIL_CLOSED"],
        "decision vocabulary",
    )

    request_required = {
        "schema_version",
        "operation",
        "request_id",
        "requester",
        "purpose",
        "record_class",
        "requested_scope",
        "minimum_necessary_justification",
        "authority_ref",
        "disclosure_mode",
    }
    missing = sorted(request_required - set(req["required"]))
    if missing:
        raise ContractError(f"request missing required fields: {missing}")

    response_required = {
        "schema_version",
        "request_id",
        "decision",
        "granted_scope",
        "context",
        "source_refs",
        "receipt",
    }
    missing = sorted(response_required - set(res["required"]))
    if missing:
        raise ContractError(f"response missing required fields: {missing}")

    receipt = res["properties"]["receipt"]
    receipt_required = {
        "receipt_id",
        "policy_profile",
        "authority_ref",
        "requested_scope",
        "granted_scope",
        "decision",
        "timestamp",
        "response_hash",
    }
    missing = sorted(receipt_required - set(receipt["required"]))
    if missing:
        raise ContractError(f"receipt missing required fields: {missing}")

    if req.get("additionalProperties") is not False:
        raise ContractError("request contract must fail closed on additional properties")
    if res.get("additionalProperties") is not False:
        raise ContractError("response contract must fail closed on additional properties")
    if receipt.get("additionalProperties") is not False:
        raise ContractError("receipt contract must fail closed on additional properties")

    return {
        "valid": True,
        "protocol": "KV-INTERLOCK-v1",
        "request_schema_version": "kv.interlock.request.v1",
        "response_schema_version": "kv.interlock.response.v1",
        "operations": req["properties"]["operation"]["enum"],
        "decisions": res["properties"]["decision"]["enum"],
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
