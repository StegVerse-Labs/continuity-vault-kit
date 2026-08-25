#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

SKAP_STATES = {"SEALED", "ACTIVE", "ROTATED", "REVOKED", "RECOVERY_ONLY"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_uri(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_skap(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if obj.get("schema") != "stegverse.skap.sealed_object/v1":
        errors.append("unsupported SKAP object schema")
    if obj.get("lifecycle_state") not in SKAP_STATES:
        errors.append("invalid lifecycle state")
    if not str(obj.get("object_id", "")).startswith("skap://"):
        errors.append("object_id must use skap://")
    if obj.get("plaintext_persisted") is not False:
        errors.append("plaintext must never be persisted")
    if obj.get("kv_decryption_authority") is not False:
        errors.append("KV must not have decryption authority")
    if obj.get("device_secret_custody_authority") is not False:
        errors.append("Device must not inherit secret custody")
    if obj.get("model_secret_access") is not False:
        errors.append("model must not access secret material")
    state = obj.get("lifecycle_state")
    if state == "ACTIVE" and not obj.get("activated_at"):
        errors.append("ACTIVE requires activated_at")
    if state == "ROTATED" and not obj.get("rotated_at"):
        errors.append("ROTATED requires rotated_at")
    if state == "REVOKED" and not obj.get("revoked_at"):
        errors.append("REVOKED requires revoked_at")
    if state == "RECOVERY_ONLY" and not obj.get("recovery_only_at"):
        errors.append("RECOVERY_ONLY requires recovery_only_at")
    claimed = obj.get("object_hash")
    body = dict(obj)
    body.pop("object_hash", None)
    if claimed != sha256_uri(body):
        errors.append("SKAP object hash mismatch")
    return errors


def validate_endpoint(proof: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if proof.get("schema") != "stegverse.intr.endpoint_session_proof/v1":
        errors.append("unsupported endpoint proof schema")
    if proof.get("scheme") != "https":
        errors.append("endpoint proof requires https")
    if proof.get("same_session_required_for_resolution_and_submission") is not True:
        errors.append("same authenticated session must be required")
    if proof.get("redirect_permitted") is not False:
        errors.append("redirects must be prohibited")
    if proof.get("authority_transfer") is not False:
        errors.append("endpoint proof must not transfer authority")
    verified = proof.get("verification_state") == "VERIFIED"
    if verified:
        if proof.get("credential_resolution_permitted") is not True:
            errors.append("verified endpoint must explicitly gate permitted resolution")
        if proof.get("failure_disposition") != "NOT_APPLICABLE":
            errors.append("verified endpoint must not carry failure disposition")
    else:
        if proof.get("credential_resolution_permitted") is not False:
            errors.append("failed endpoint must block credential resolution")
        if proof.get("failure_disposition") != "FAIL_CLOSED":
            errors.append("failed endpoint must fail closed")
    claimed = proof.get("proof_hash")
    body = dict(proof)
    body.pop("proof_hash", None)
    if claimed != sha256_uri(body):
        errors.append("endpoint proof hash mismatch")
    return errors


def self_test() -> None:
    skap = {
        "schema": "stegverse.skap.sealed_object/v1",
        "object_id": "skap://APIs/provider/example",
        "secret_class": "API_CREDENTIAL",
        "provider": "example",
        "account_ref": None,
        "lifecycle_state": "ACTIVE",
        "credential_version": 1,
        "supersedes_object_hash": None,
        "sealed_material_ref": "sealed://example-object",
        "sealed_material_hash": "sha256:" + "a" * 64,
        "wrapping_policy_ref": "policy://skap/default",
        "allowed_purposes": ["llm.inference"],
        "allowed_endpoint_refs": ["endpoint://example/api"],
        "plaintext_persisted": False,
        "kv_decryption_authority": False,
        "device_secret_custody_authority": False,
        "model_secret_access": False,
        "created_at": "2026-08-24T20:00:00Z",
        "activated_at": "2026-08-24T20:01:00Z",
        "rotated_at": None,
        "revoked_at": None,
        "recovery_only_at": None,
    }
    skap["object_hash"] = sha256_uri(skap)
    assert not validate_skap(skap), validate_skap(skap)

    proof = {
        "schema": "stegverse.intr.endpoint_session_proof/v1",
        "proof_id": "endpoint-proof-example",
        "packet_id": "packet-example",
        "operation_hash": "sha256:" + "b" * 64,
        "authorized_endpoint_ref": "endpoint://example/api",
        "resolved_host": "api.example.test",
        "scheme": "https",
        "port": 443,
        "path_prefix": "/v1/",
        "tls_session_ref": "tls-session://example",
        "peer_identity_ref": "peer://example",
        "certificate_chain_hash": "sha256:" + "c" * 64,
        "verification_state": "VERIFIED",
        "verified_at": "2026-08-24T20:02:00Z",
        "same_session_required_for_resolution_and_submission": True,
        "redirect_permitted": False,
        "credential_resolution_permitted": True,
        "authority_transfer": False,
        "failure_disposition": "NOT_APPLICABLE",
    }
    proof["proof_hash"] = sha256_uri(proof)
    assert not validate_endpoint(proof), validate_endpoint(proof)

    cases = []
    bad = copy.deepcopy(skap); bad["plaintext_persisted"] = True; cases.append((validate_skap(bad), "plaintext"))
    bad = copy.deepcopy(skap); bad["lifecycle_state"] = "REVOKED"; bad["revoked_at"] = None; cases.append((validate_skap(bad), "REVOKED"))
    bad = copy.deepcopy(skap); bad["kv_decryption_authority"] = True; cases.append((validate_skap(bad), "KV"))
    bad = copy.deepcopy(proof); bad["verification_state"] = "FAILED"; bad["credential_resolution_permitted"] = True; cases.append((validate_endpoint(bad), "failed endpoint"))
    bad = copy.deepcopy(proof); bad["redirect_permitted"] = True; cases.append((validate_endpoint(bad), "redirects"))
    bad = copy.deepcopy(proof); bad["same_session_required_for_resolution_and_submission"] = False; cases.append((validate_endpoint(bad), "same authenticated session"))
    for errors, fragment in cases:
        if not errors or not any(fragment.lower() in e.lower() for e in errors):
            raise AssertionError((fragment, errors))
    print("SKAP_ENDPOINT_CONTRACT_SELF_TEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
