#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from typing import Any

SKAP_STATES = {"SEALED", "ACTIVE", "ROTATED", "REVOKED", "RECOVERY_ONLY"}
LIFECYCLE_TRANSITIONS = {
    ("SEALED", "ACTIVE"),
    ("SEALED", "RECOVERY_ONLY"),
    ("ACTIVE", "ROTATED"),
    ("ACTIVE", "REVOKED"),
    ("ACTIVE", "RECOVERY_ONLY"),
    ("RECOVERY_ONLY", "ACTIVE"),
    ("RECOVERY_ONLY", "REVOKED"),
}


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


def validate_lifecycle_receipt(receipt: dict[str, Any], prior_receipt: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if receipt.get("schema") != "stegverse.skap.lifecycle_transition_receipt/v1":
        errors.append("unsupported SKAP lifecycle receipt schema")
    transition = (receipt.get("from_state"), receipt.get("to_state"))
    if transition not in LIFECYCLE_TRANSITIONS:
        errors.append("invalid SKAP lifecycle transition")
    if receipt.get("authority_transfer") is not False:
        errors.append("lifecycle receipt must not transfer authority")
    if receipt.get("secret_plaintext_present") is not False:
        errors.append("lifecycle receipt must not contain secret plaintext")
    if receipt.get("to_state") == "ROTATED":
        if receipt.get("outstanding_grants_invalidated") is not True:
            errors.append("rotation must invalidate outstanding grants")
        if receipt.get("revocation_effect") != "NO_NEW_GRANTS":
            errors.append("rotation must block new grants for superseded version")
        if not receipt.get("replacement_secret_ref"):
            errors.append("rotation requires replacement secret reference")
    if receipt.get("to_state") == "REVOKED":
        if receipt.get("outstanding_grants_invalidated") is not True:
            errors.append("revocation must invalidate outstanding grants")
        if receipt.get("revocation_effect") != "BLOCK_ALL_RESOLUTION":
            errors.append("revocation must block all resolution")
    expected_prior = None if prior_receipt is None else prior_receipt.get("receipt_hash")
    if receipt.get("prior_transition_receipt_hash") != expected_prior:
        errors.append("lifecycle prior receipt hash mismatch")
    claimed = receipt.get("receipt_hash")
    body = dict(receipt)
    body.pop("receipt_hash", None)
    if claimed != sha256_uri(body):
        errors.append("lifecycle receipt hash mismatch")
    return errors


def validate_endpoint(proof: dict[str, Any], *, expected_binding: dict[str, str] | None = None) -> list[str]:
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
    for field in ("packet_hash", "operation_hash", "credential_grant_hash", "tls_session_binding_hash"):
        if not str(proof.get(field, "")).startswith("sha256:"):
            errors.append(f"endpoint proof missing cryptographic binding: {field}")
    if expected_binding:
        for field in ("packet_id", "packet_hash", "operation_hash", "credential_grant_hash", "authorized_endpoint_ref", "tls_session_binding_hash"):
            if proof.get(field) != expected_binding.get(field):
                errors.append(f"endpoint proof binding mismatch: {field}")
    verified = proof.get("verification_state") == "VERIFIED"
    if verified:
        if proof.get("credential_resolution_permitted") is not True:
            errors.append("verified endpoint must explicitly gate permitted resolution")
        if proof.get("revocation_rechecked_immediately_before_resolution") is not True:
            errors.append("verified endpoint requires immediate revocation recheck")
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

    activation = {
        "schema": "stegverse.skap.lifecycle_transition_receipt/v1",
        "receipt_id": "skap-life-001",
        "secret_ref": skap["object_id"],
        "credential_version": 1,
        "from_state": "SEALED",
        "to_state": "ACTIVE",
        "transition_reason": "owner-authorized activation",
        "prior_transition_receipt_hash": None,
        "sealed_object_hash_before": "sha256:" + "1" * 64,
        "sealed_object_hash_after": skap["object_hash"],
        "supersedes_credential_version": None,
        "replacement_secret_ref": None,
        "revocation_effect": "NONE",
        "outstanding_grants_invalidated": False,
        "authority_ref": "tvc://authority/example",
        "authority_transfer": False,
        "secret_plaintext_present": False,
        "effective_at": "2026-08-24T20:01:00Z",
    }
    activation["receipt_hash"] = sha256_uri(activation)
    assert not validate_lifecycle_receipt(activation), validate_lifecycle_receipt(activation)

    rotation = {
        "schema": "stegverse.skap.lifecycle_transition_receipt/v1",
        "receipt_id": "skap-life-002",
        "secret_ref": skap["object_id"],
        "credential_version": 2,
        "from_state": "ACTIVE",
        "to_state": "ROTATED",
        "transition_reason": "scheduled rotation",
        "prior_transition_receipt_hash": activation["receipt_hash"],
        "sealed_object_hash_before": skap["object_hash"],
        "sealed_object_hash_after": "sha256:" + "2" * 64,
        "supersedes_credential_version": 1,
        "replacement_secret_ref": "skap://APIs/provider/example-v2",
        "revocation_effect": "NO_NEW_GRANTS",
        "outstanding_grants_invalidated": True,
        "authority_ref": "tvc://authority/example",
        "authority_transfer": False,
        "secret_plaintext_present": False,
        "effective_at": "2026-08-24T20:10:00Z",
    }
    rotation["receipt_hash"] = sha256_uri(rotation)
    assert not validate_lifecycle_receipt(rotation, activation), validate_lifecycle_receipt(rotation, activation)

    expected_binding = {
        "packet_id": "packet-example",
        "packet_hash": "sha256:" + "d" * 64,
        "operation_hash": "sha256:" + "b" * 64,
        "credential_grant_hash": "sha256:" + "e" * 64,
        "authorized_endpoint_ref": "endpoint://example/api",
        "tls_session_binding_hash": "sha256:" + "f" * 64,
    }
    proof = {
        "schema": "stegverse.intr.endpoint_session_proof/v1",
        "proof_id": "endpoint-proof-example",
        **expected_binding,
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
        "revocation_rechecked_immediately_before_resolution": True,
        "authority_transfer": False,
        "failure_disposition": "NOT_APPLICABLE",
    }
    proof["proof_hash"] = sha256_uri(proof)
    assert not validate_endpoint(proof, expected_binding=expected_binding), validate_endpoint(proof, expected_binding=expected_binding)

    cases = []
    bad = copy.deepcopy(skap); bad["plaintext_persisted"] = True; cases.append((validate_skap(bad), "plaintext"))
    bad = copy.deepcopy(skap); bad["lifecycle_state"] = "REVOKED"; bad["revoked_at"] = None; cases.append((validate_skap(bad), "REVOKED"))
    bad = copy.deepcopy(skap); bad["kv_decryption_authority"] = True; cases.append((validate_skap(bad), "KV"))
    bad = copy.deepcopy(rotation); bad["outstanding_grants_invalidated"] = False; cases.append((validate_lifecycle_receipt(bad, activation), "invalidate outstanding grants"))
    bad = copy.deepcopy(rotation); bad["prior_transition_receipt_hash"] = "sha256:" + "0" * 64; cases.append((validate_lifecycle_receipt(bad, activation), "prior receipt"))
    bad = copy.deepcopy(proof); bad["verification_state"] = "FAILED"; bad["credential_resolution_permitted"] = True; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "failed endpoint"))
    bad = copy.deepcopy(proof); bad["redirect_permitted"] = True; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "redirects"))
    bad = copy.deepcopy(proof); bad["same_session_required_for_resolution_and_submission"] = False; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "same authenticated session"))
    bad = copy.deepcopy(proof); bad["packet_hash"] = "sha256:" + "9" * 64; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "packet_hash"))
    bad = copy.deepcopy(proof); bad["credential_grant_hash"] = "sha256:" + "8" * 64; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "credential_grant_hash"))
    bad = copy.deepcopy(proof); bad["tls_session_binding_hash"] = "sha256:" + "7" * 64; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "tls_session_binding_hash"))
    bad = copy.deepcopy(proof); bad["revocation_rechecked_immediately_before_resolution"] = False; cases.append((validate_endpoint(bad, expected_binding=expected_binding), "revocation"))
    for errors, fragment in cases:
        if not errors or not any(fragment.lower() in e.lower() for e in errors):
            raise AssertionError((fragment, errors))
    print("SKAP_ENDPOINT_LIFECYCLE_CONTRACT_SELF_TEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
