#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "kv-interlock-intr-envelope.schema.json"
SPEC = ROOT / "specs" / "kv-interlock-intr-envelope.v1.json"


class EnvelopeError(ValueError):
    pass


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EnvelopeError(f"{path} must contain an object")
    return value


def validate_contract() -> dict:
    schema = load(SCHEMA)
    spec = load(SPEC)

    if schema["properties"]["schema"]["const"] != "stegverse.kv-interlock.intr-envelope/v1":
        raise EnvelopeError("unexpected envelope schema id")
    if schema["properties"]["protocol"]["const"] != "InTr":
        raise EnvelopeError("protocol must remain InTr")
    if schema["properties"]["operation"]["enum"] != ["DISCOVER", "REQUEST", "COMMIT_CANDIDATE"]:
        raise EnvelopeError("operation vocabulary drift")
    if schema["properties"]["authority"]["properties"]["authority_transfer"]["const"] is not False:
        raise EnvelopeError("transport may not transfer authority")
    if schema["properties"]["authority"]["properties"]["credential_authority_effect"]["const"] != "NONE":
        raise EnvelopeError("generic KV interlock transport may not create credential authority")
    if "credential_grant" in schema["properties"]:
        raise EnvelopeError("generic KV interlock envelope must not require credential semantics")

    required = set(schema["required"])
    for key in {
        "packet_id", "direction", "source_role", "next_role", "request_id",
        "operation", "payload_schema_version", "payload_hash",
        "sealed_material_ref", "authority", "boundary_proof", "receipt_policy",
    }:
        if key not in required:
            raise EnvelopeError(f"required field missing: {key}")

    if spec["direction"] != "REQUEST":
        raise EnvelopeError("canonical example must be a request")
    if (spec["source_role"], spec["next_role"]) != ("DEVICE", "KV"):
        raise EnvelopeError("request direction must be DEVICE -> KV")
    if spec["payload_schema_version"] != "kv.interlock.request.v1":
        raise EnvelopeError("request payload schema version mismatch")
    if spec["authority"]["authority_transfer"] is not False:
        raise EnvelopeError("example authority transfer detected")
    if spec["receipt_policy"]["receipt_contains_payload_plaintext"] is not False:
        raise EnvelopeError("receipt plaintext is prohibited")
    if spec["receipt_policy"]["ambiguous_disposition"] != "FAIL_CLOSED":
        raise EnvelopeError("ambiguous bounded context transport must fail closed")

    serialized = json.dumps(spec, sort_keys=True)
    for forbidden in ("credential_grant", "03_Records/", "private_custody_ref", "secret_plaintext"):
        if forbidden in serialized:
            raise EnvelopeError(f"generic envelope contains prohibited material: {forbidden}")

    return {
        "valid": True,
        "schema": "stegverse.kv-interlock.intr-envelope/v1",
        "request_path": "DEVICE->KV",
        "response_path": "KV->DEVICE",
        "credential_specific": False,
        "authority_effect": "NONE",
    }


def main() -> int:
    print(json.dumps(validate_contract(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
