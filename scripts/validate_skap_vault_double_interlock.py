#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "stegverse.kv.skap-vault-double-interlock/v1"
RECEIPT_SCHEMA = "stegverse.intr.boundary_transition_receipt/v1"
EXPECTED_TOPOLOGY = ["DEVICE", "INTR_DEVICE_KV", "KV", "INTR_KV_SKAP", "SKAP_VAULT"]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_uri(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != SCHEMA:
        errors.append("unsupported SKAP Vault double-interlock schema")
    if contract.get("logical_location") != "KV/_Vault/SKAP":
        errors.append("SKAP Vault must remain logically inside KV namespace")
    if contract.get("credential_storage_owner") != "SKAP_VAULT":
        errors.append("credential storage owner must be SKAP_VAULT")
    if contract.get("credential_authority") != "TV/TVC":
        errors.append("credential authority must remain TV/TVC")
    if contract.get("canonical_topology") != EXPECTED_TOPOLOGY:
        errors.append("canonical double-interlock topology mismatch")

    boundaries = contract.get("boundaries") or {}
    device_kv = boundaries.get("device_kv") or {}
    kv_skap = boundaries.get("kv_skap") or {}
    if device_kv.get("connector") != "InTr" or device_kv.get("required") is not True:
        errors.append("Device/KV InTr connector is mandatory")
    if kv_skap.get("connector") != "InTr" or kv_skap.get("required") is not True:
        errors.append("KV/SKAP InTr connector is mandatory")
    if device_kv.get("device_plaintext_persistence") is not False:
        errors.append("Device plaintext persistence forbidden")
    if device_kv.get("device_durable_secret_custody") is not False:
        errors.append("Device durable secret custody forbidden")
    if device_kv.get("kv_direct_credential_access") is not False:
        errors.append("KV direct credential access forbidden")
    if kv_skap.get("kv_plaintext_persistence") is not False:
        errors.append("KV plaintext persistence forbidden")
    if kv_skap.get("kv_decryption_authority") is not False:
        errors.append("KV decryption authority forbidden")
    if kv_skap.get("skap_vault_only_secret_custody") is not True:
        errors.append("SKAP Vault must be sole secret custody boundary")
    if device_kv.get("receipt_required") is not True or kv_skap.get("receipt_required") is not True:
        errors.append("both interlocks require transition receipts")

    storage = contract.get("storage") or {}
    if storage.get("credential_objects") != "_Vault/SKAP/Credentials":
        errors.append("credential objects must live under _Vault/SKAP/Credentials")
    if storage.get("kv_visible_material") != "REFERENCE_CIPHERTEXT_AND_NON_SECRET_EVIDENCE_ONLY":
        errors.append("KV-visible material must remain reference/ciphertext/non-secret evidence only")
    if storage.get("credential_plaintext_location") != "SKAP_VAULT_TRANSIENT_RESOLUTION_ONLY":
        errors.append("credential plaintext may exist only transiently inside SKAP Vault resolution")

    access = contract.get("access_contract") or {}
    for field in (
        "all_credential_reads_require_both_interlocks",
        "all_credential_writes_require_both_interlocks",
        "all_credential_rotations_require_both_interlocks",
        "all_credential_revocations_require_both_interlocks",
        "endpoint_session_verification_required_before_transient_resolution",
    ):
        if access.get(field) is not True:
            errors.append(f"required access invariant missing: {field}")
    for field in ("direct_device_to_skap_access", "direct_kv_to_credential_plaintext_access", "direct_model_to_skap_access", "authority_transfer"):
        if access.get(field) is not False:
            errors.append(f"forbidden access/authority path enabled: {field}")

    receipts = contract.get("transition_receipts") or {}
    if receipts.get("device_kv_receipt_schema") != RECEIPT_SCHEMA or receipts.get("kv_skap_receipt_schema") != RECEIPT_SCHEMA:
        errors.append("boundary receipt schema mismatch")
    if receipts.get("chain_binding_required") is not True or receipts.get("second_receipt_must_bind_first_receipt_hash") is not True:
        errors.append("double-interlock receipt chain binding is mandatory")
    if receipts.get("secret_plaintext_allowed_in_receipts") is not False:
        errors.append("secret plaintext forbidden in boundary receipts")
    return errors


def validate_receipt_chain(device_kv: dict[str, Any], kv_skap: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, receipt in (("device_kv", device_kv), ("kv_skap", kv_skap)):
        if receipt.get("schema") != RECEIPT_SCHEMA:
            errors.append(f"{name} receipt schema invalid")
        if receipt.get("connector") != "InTr":
            errors.append(f"{name} connector must be InTr")
        if receipt.get("secret_plaintext_present") is not False:
            errors.append(f"{name} receipt contains secret plaintext")
        if receipt.get("authority_transfer") is not False:
            errors.append(f"{name} receipt transfers authority")
        claimed = receipt.get("receipt_hash")
        body = dict(receipt); body.pop("receipt_hash", None)
        if claimed != sha256_uri(body):
            errors.append(f"{name} receipt hash mismatch")

    if device_kv.get("from_boundary") != "DEVICE" or device_kv.get("to_boundary") != "KV":
        errors.append("first interlock must be DEVICE->KV")
    if kv_skap.get("from_boundary") != "KV" or kv_skap.get("to_boundary") != "SKAP_VAULT":
        errors.append("second interlock must be KV->SKAP_VAULT")
    if kv_skap.get("prior_boundary_receipt_hash") != device_kv.get("receipt_hash"):
        errors.append("KV/SKAP receipt must bind Device/KV receipt hash")
    if device_kv.get("prior_boundary_receipt_hash") not in (None, ""):
        errors.append("Device/KV receipt must begin the credential boundary chain")
    if device_kv.get("credential_ref") != kv_skap.get("credential_ref"):
        errors.append("credential reference changed between interlocks")
    if device_kv.get("operation_id") != kv_skap.get("operation_id"):
        errors.append("operation binding changed between interlocks")
    return errors


def _receipt(*, boundary_from: str, boundary_to: str, credential_ref: str, operation_id: str, prior: str | None) -> dict[str, Any]:
    body = {
        "schema": RECEIPT_SCHEMA,
        "connector": "InTr",
        "from_boundary": boundary_from,
        "to_boundary": boundary_to,
        "credential_ref": credential_ref,
        "operation_id": operation_id,
        "prior_boundary_receipt_hash": prior,
        "secret_plaintext_present": False,
        "authority_transfer": False,
    }
    return {**body, "receipt_hash": sha256_uri(body)}


def self_test(contract: dict[str, Any]) -> None:
    assert not validate_contract(contract), validate_contract(contract)
    first = _receipt(boundary_from="DEVICE", boundary_to="KV", credential_ref="skap://APIs/coinbase/live", operation_id="op-1", prior=None)
    second = _receipt(boundary_from="KV", boundary_to="SKAP_VAULT", credential_ref="skap://APIs/coinbase/live", operation_id="op-1", prior=first["receipt_hash"])
    assert not validate_receipt_chain(first, second), validate_receipt_chain(first, second)

    cases: list[tuple[list[str], str]] = []
    bad = copy.deepcopy(contract); bad["boundaries"]["device_kv"]["required"] = False; cases.append((validate_contract(bad), "Device/KV"))
    bad = copy.deepcopy(contract); bad["boundaries"]["kv_skap"]["required"] = False; cases.append((validate_contract(bad), "KV/SKAP"))
    bad = copy.deepcopy(contract); bad["boundaries"]["kv_skap"]["kv_decryption_authority"] = True; cases.append((validate_contract(bad), "decryption"))
    bad = copy.deepcopy(contract); bad["boundaries"]["device_kv"]["device_durable_secret_custody"] = True; cases.append((validate_contract(bad), "Device durable"))
    bad = copy.deepcopy(contract); bad["access_contract"]["direct_device_to_skap_access"] = True; cases.append((validate_contract(bad), "direct_device"))
    bad_second = copy.deepcopy(second); bad_second["prior_boundary_receipt_hash"] = "sha256:" + "0" * 64; bad_second["receipt_hash"] = sha256_uri({k:v for k,v in bad_second.items() if k != "receipt_hash"}); cases.append((validate_receipt_chain(first, bad_second), "bind"))
    reversed_first = _receipt(boundary_from="KV", boundary_to="SKAP_VAULT", credential_ref="skap://APIs/coinbase/live", operation_id="op-1", prior=None); cases.append((validate_receipt_chain(reversed_first, second), "first interlock"))
    bad_second = copy.deepcopy(second); bad_second["credential_ref"] = "skap://APIs/coinbase/other"; bad_second["receipt_hash"] = sha256_uri({k:v for k,v in bad_second.items() if k != "receipt_hash"}); cases.append((validate_receipt_chain(first, bad_second), "credential reference"))
    for errors, fragment in cases:
        if not errors or not any(fragment.lower() in error.lower() for error in errors):
            raise AssertionError((fragment, errors))
    print("SKAP_VAULT_DOUBLE_INTERLOCK_SELF_TEST_PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", nargs="?", default="specs/skap-vault-double-interlock.v1.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    errors = validate_contract(contract)
    if errors:
        for error in errors:
            print("ERROR", error)
        return 2
    if args.self_test:
        self_test(contract)
    else:
        print("SKAP_VAULT_DOUBLE_INTERLOCK_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
