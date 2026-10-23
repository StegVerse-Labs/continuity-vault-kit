"""Bind canonical Task Registry event custody to the existing governed KV provider path.

This module does not authenticate providers, resolve credentials, decide Interlock/InTr
admission, execute provider I/O, or grant authority. It converts an already-validated
Task Registry sovereign-KV projection request into the canonical provider-neutral
WRITE request used by continuity-vault-kit and validates the resulting admitted
provider receipt against the exact event hash.
"""

from __future__ import annotations

from typing import Any, Dict

from runtime.kv_storage_provider_adapter import build_operation_request, default_registry

PROJECTION_REQUEST_SCHEMA = "stegverse.task-registry-sovereign-kv-projection-request/v1"
PROJECTION_RECEIPT_SCHEMA = "stegverse.task-registry-sovereign-kv-projection-receipt/v1"
PROVIDER_RECEIPT_SCHEMA = "stegverse.kv.storage-provider-operation-receipt/v1"
BINDING_SCHEMA = "stegverse.kv.task-registry-event-custody-binding/v1"
CUSTODY_CLASS = "STEGVERSE_SOVEREIGN_KV"


class TaskRegistryEventCustodyBindingError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskRegistryEventCustodyBindingError(message)


def build_task_registry_event_custody_binding(
    *,
    projection_request: Dict[str, Any],
    provider_id: str,
    instance_id: str,
    kv_set_id: str,
    storage_locator: str | None = None,
) -> Dict[str, Any]:
    _require(projection_request.get("schema") == PROJECTION_REQUEST_SCHEMA, "unexpected projection request schema")
    _require(projection_request.get("custody_class") == CUSTODY_CLASS, "unexpected custody class")
    _require(projection_request.get("authority_effect") == "NONE", "projection request cannot grant authority")
    event = projection_request.get("exact_event")
    _require(isinstance(event, dict), "exact_event required")
    event_sha256 = projection_request.get("event_sha256")
    _require(isinstance(event_sha256, str) and event_sha256.startswith("sha256:"), "event_sha256 required")
    _require(event.get("event_sha256") == event_sha256, "exact_event hash binding mismatch")
    _require(event.get("authority_effect") == "NONE", "exact event cannot grant authority")

    adapter = default_registry().get(provider_id)
    provider_write_request = build_operation_request(
        adapter=adapter,
        instance_id=instance_id,
        kv_set_id=kv_set_id,
        operation="WRITE",
        storage_locator=storage_locator,
        requested_by="task-registry-coordination",
        object_ref=event_sha256,
    )

    return {
        "schema": BINDING_SCHEMA,
        "task_id": projection_request.get("task_id"),
        "session_id": projection_request.get("session_id"),
        "event_sha256": event_sha256,
        "predecessor_event_sha256": projection_request.get("predecessor_event_sha256"),
        "custody_class": CUSTODY_CLASS,
        "provider_id": provider_id,
        "kv_instance_ref": instance_id,
        "kv_set_id": kv_set_id,
        "provider_write_request": provider_write_request,
        "interlock_intr_admission_required": True,
        "skap_credential_reference_required": True,
        "provider_result_evidence_required": True,
        "exact_hash_readback_required": True,
        "credential_material_present": False,
        "authority_effect": "NONE",
    }


def validate_task_registry_event_custody_result(
    *,
    binding: Dict[str, Any],
    provider_receipt: Dict[str, Any],
    stored_event_sha256: str,
) -> Dict[str, Any]:
    _require(binding.get("schema") == BINDING_SCHEMA, "unexpected custody binding schema")
    request = binding.get("provider_write_request")
    _require(isinstance(request, dict), "provider write request required")
    _require(provider_receipt.get("schema") == PROVIDER_RECEIPT_SCHEMA, "provider receipt schema mismatch")
    _require(provider_receipt.get("request_id") == request.get("request_id"), "provider receipt request mismatch")
    _require(provider_receipt.get("instance_id") == request.get("instance_id"), "provider receipt instance mismatch")
    _require(provider_receipt.get("kv_set_id") == request.get("kv_set_id"), "provider receipt set mismatch")
    _require(provider_receipt.get("provider_id") == request.get("provider_id"), "provider receipt provider mismatch")
    _require(provider_receipt.get("operation") == "WRITE", "provider receipt must prove WRITE")
    _require(provider_receipt.get("governance_state") == "ADMITTED", "provider WRITE requires ADMITTED governance")
    _require(provider_receipt.get("provider_operation_executed") is True, "provider WRITE execution evidence required")
    _require(bool(str(provider_receipt.get("interlock_receipt_ref") or "").strip()), "Interlock receipt required")
    _require(bool(str(provider_receipt.get("intr_receipt_ref") or "").strip()), "InTr receipt required")
    _require(bool(str(provider_receipt.get("skap_credential_ref") or "").strip()), "SKAP credential reference required")
    _require(bool(str(provider_receipt.get("provider_result_ref") or "").strip()), "provider result evidence required")
    _require(provider_receipt.get("credential_material_present") is False, "credential material prohibited")
    _require(provider_receipt.get("authority_effect") == "NONE", "provider receipt cannot grant authority")
    _require(request.get("object_ref") == binding.get("event_sha256"), "provider request object_ref must bind exact event hash")
    _require(stored_event_sha256 == binding.get("event_sha256"), "stored event hash readback mismatch")

    return {
        "schema": PROJECTION_RECEIPT_SCHEMA,
        "task_id": binding.get("task_id"),
        "session_id": binding.get("session_id"),
        "event_sha256": binding["event_sha256"],
        "stored_event_sha256": stored_event_sha256,
        "custody_class": CUSTODY_CLASS,
        "provider_adapter_ref": f"continuity-vault-kit:runtime/kv_storage_provider_adapter.py#{request['provider_id']}",
        "interlock_intr_receipt_ref": f"{provider_receipt['interlock_receipt_ref']}|{provider_receipt['intr_receipt_ref']}",
        "kv_instance_ref": request["instance_id"],
        "provider_operation_request_id": request["request_id"],
        "provider_result_ref": provider_receipt["provider_result_ref"],
        "skap_credential_ref": provider_receipt["skap_credential_ref"],
        "exact_hash_readback_verified": True,
        "authority_effect": "NONE",
    }


# --- additive: vault-lineage record type (class B consumes-extension for KV-SKAP-VAULT-FUNCTIONAL-001) ---
# KV-SKAP-VAULT-FUNCTIONAL-001 reconstructs a principal's vault from its receipt-hash lineage alone; the durable
# custody location that lineage is read from on any device is this Goal's sovereign-KV custody path. The record
# below carries an exported lineage (stegverse.kv-skap-vault-lineage/v1) through the same provider WRITE contract
# as Task Registry events. Everything above is unchanged: the projection-request schema, the event binding and
# its receipt keep their bytes (tests/test_sovereign_kv_vault_lineage_record.py pins their digests).
import hashlib as _hashlib
import json as _json

from runtime.kv_storage_provider_adapter import build_vault_lineage_readback_request, vault_lineage_registry

VAULT_LINEAGE_SOURCE_SCHEMA = "stegverse.kv-skap-vault-lineage/v1"
VAULT_LINEAGE_RECORD_SCHEMA = "stegverse.task-registry-sovereign-kv-vault-lineage-record/v1"
VAULT_LINEAGE_BINDING_SCHEMA = "stegverse.kv.vault-lineage-custody-binding/v1"
VAULT_LINEAGE_RECEIPT_SCHEMA = "stegverse.task-registry-sovereign-kv-vault-lineage-receipt/v1"
RECORD_TYPES = ("TASK_REGISTRY_EVENT", "KV_SKAP_VAULT_LINEAGE")
_MATERIAL_KEYS = ("secret", "password", "private_key", "token", "credential_material", "key_material", "plaintext")


def _sha256_uri(value: Any) -> str:
    raw = _json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + _hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _no_material(value: Any, path: str = "lineage") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            _require(not any(m in lowered for m in _MATERIAL_KEYS) or lowered.endswith("_ref"),
                     f"credential or key material is not custody content: {path}.{key}")
            _no_material(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _no_material(item, f"{path}[{index}]")


def build_vault_lineage_record(*, exported_lineage: Dict[str, Any], session_id: str | None = None) -> Dict[str, Any]:
    """Wrap an exported KV/SKAP Vault lineage as a sovereign-KV custody record. The chain is checked
    structurally and every receipt hash is re-derived; nothing is minted or decided here."""
    _require(isinstance(exported_lineage, dict), "exported_lineage required")
    _require(exported_lineage.get("schema") == VAULT_LINEAGE_SOURCE_SCHEMA, "unexpected vault lineage schema")
    receipts = exported_lineage.get("receipts")
    _require(isinstance(receipts, list) and bool(receipts), "vault lineage must hold at least one receipt")
    principal = exported_lineage.get("principal_ref")
    previous = None
    for index, receipt in enumerate(receipts):
        _require(isinstance(receipt, dict), f"receipt {index} must be an object")
        _require(receipt.get("sequence") == index, f"receipt {index} sequence break")
        _require(receipt.get("previous_receipt_hash") == previous, f"receipt {index} does not chain")
        _require(receipt.get("principal_ref") == principal, f"receipt {index} principal mismatch")
        body = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        _require(receipt.get("receipt_hash") == _sha256_uri(body), f"receipt {index} hash mismatch")
        previous = receipt["receipt_hash"]
    _require(exported_lineage.get("head") == previous, "lineage head must equal the last receipt hash")
    _no_material(exported_lineage)
    return {
        "schema": VAULT_LINEAGE_RECORD_SCHEMA,
        "record_type": "KV_SKAP_VAULT_LINEAGE",
        "task_id": exported_lineage.get("task_id"),
        "session_id": session_id,
        "principal_ref": principal,
        "lineage_sha256": _sha256_uri(exported_lineage),
        "head_receipt_hash": previous,
        "receipt_count": len(receipts),
        "custody_class": CUSTODY_CLASS,
        "exact_lineage": exported_lineage,
        "credential_material_present": False,
        "authority_effect": "NONE",
    }


def build_vault_lineage_custody_binding(
    *,
    lineage_record: Dict[str, Any],
    provider_id: str,
    instance_id: str,
    kv_set_id: str,
    storage_locator: str | None = None,
) -> Dict[str, Any]:
    _require(lineage_record.get("schema") == VAULT_LINEAGE_RECORD_SCHEMA, "unexpected vault lineage record schema")
    _require(lineage_record.get("record_type") == "KV_SKAP_VAULT_LINEAGE", "unexpected record type")
    _require(lineage_record.get("custody_class") == CUSTODY_CLASS, "unexpected custody class")
    _require(lineage_record.get("authority_effect") == "NONE", "lineage record cannot grant authority")
    _require(lineage_record.get("credential_material_present") is False, "credential material prohibited")
    rebuilt = build_vault_lineage_record(exported_lineage=lineage_record.get("exact_lineage"),
                                         session_id=lineage_record.get("session_id"))
    _require(rebuilt == lineage_record, "lineage record does not re-derive from its exact lineage")

    adapter = vault_lineage_registry().get(provider_id)
    lineage_sha256 = lineage_record["lineage_sha256"]
    write_request = build_operation_request(
        adapter=adapter,
        instance_id=instance_id,
        kv_set_id=kv_set_id,
        operation="WRITE",
        storage_locator=storage_locator,
        requested_by="kv-skap-vault",
        object_ref=lineage_sha256,
    )
    readback_request = build_vault_lineage_readback_request(
        adapter=adapter, instance_id=instance_id, kv_set_id=kv_set_id,
        lineage_sha256=lineage_sha256, storage_locator=storage_locator)
    return {
        "schema": VAULT_LINEAGE_BINDING_SCHEMA,
        "record_type": "KV_SKAP_VAULT_LINEAGE",
        "task_id": lineage_record.get("task_id"),
        "principal_ref": lineage_record["principal_ref"],
        "lineage_sha256": lineage_sha256,
        "head_receipt_hash": lineage_record["head_receipt_hash"],
        "receipt_count": lineage_record["receipt_count"],
        "custody_class": CUSTODY_CLASS,
        "provider_id": provider_id,
        "kv_instance_ref": instance_id,
        "kv_set_id": kv_set_id,
        "provider_write_request": write_request,
        "provider_readback_request": readback_request,
        "interlock_intr_admission_required": True,
        "skap_credential_reference_required": True,
        "provider_result_evidence_required": True,
        "exact_hash_readback_required": True,
        "credential_material_present": False,
        "authority_effect": "NONE",
    }


VAULT_LINEAGE_CUSTODY_GOAL = "TASK-REGISTRY-SOVEREIGN-KV-EVENT-CUSTODY-001"
VAULT_LINEAGE_CUSTODY_PREDICATE = "AUTHENTIC_ADMITTED_PROVIDER_WRITE_AND_EXACT_EVENT_HASH_READBACK_FROM_SOVEREIGN_KV"
VAULT_LINEAGE_CUSTODY_RETRY = ("runtime.task_registry_event_sovereign_kv_binding.validate_vault_lineage_custody_result "
                               "(StegVerse-Labs/continuity-vault-kit); python -m unittest "
                               "tests.test_sovereign_kv_vault_lineage_record")


# Two sequential credential layers (StegVerse-Labs/.github#3330 rev 1, LC-KV-03/08): a custody result is admitted only
# when the provider receipt binds a layer-1 KV-access receipt (INTR_DEVICE_KV, minted by KVInterlockRuntime.handle for
# a currently admitted healthy node) and a layer-2 SKAP-access receipt (INTR_KV_SKAP, minted by the separate layer-2
# gate inside KV, prior_receipt_hash == the layer-1 receipt). Both are verified against the gates' own receipt stores
# through access_receipt_verifier; a non-empty string is never accepted. This module mints neither receipt.
KV_ACCESS_LAYER1_REFUSED = "KV_ACCESS_LAYER1_REFUSED"
SKAP_ACCESS_LAYER2_REFUSED = "SKAP_ACCESS_LAYER2_REFUSED"
LAYER_PREDICATES = {
    KV_ACCESS_LAYER1_REFUSED: "KV_REACHABLE_ONLY_VIA_INTR_FROM_HEALTHY_NODE",
    SKAP_ACCESS_LAYER2_REFUSED: "SKAP_ACCESS_REQUIRES_PRIOR_LAYER1_KV_ACCESS_RECEIPT",
}


class VaultLineageAccessLayerRefused(TaskRegistryEventCustodyBindingError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code


def _is_sha256_uri(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71 \
        and all(c in "0123456789abcdef" for c in value[7:])


def _require_access_layers(provider_receipt: Dict[str, Any], verifier: Any) -> tuple[str, str]:
    kv_hash = provider_receipt.get("kv_access_receipt_hash")
    skap_hash = provider_receipt.get("skap_access_receipt_hash")
    if not _is_sha256_uri(kv_hash):
        raise VaultLineageAccessLayerRefused(KV_ACCESS_LAYER1_REFUSED, (
            "the provider receipt binds no layer-1 kv_access_receipt_hash; custody is reached only through "
            "KVInterlockRuntime.handle (INTR_DEVICE_KV) from a currently admitted healthy node"))
    if not _is_sha256_uri(skap_hash):
        raise VaultLineageAccessLayerRefused(SKAP_ACCESS_LAYER2_REFUSED, (
            "the provider receipt binds no layer-2 skap_access_receipt_hash; custody records enter or leave the SKAP "
            "Vault only through the INTR_KV_SKAP gate whose prior_receipt_hash is the layer-1 receipt"))
    if verifier is None:
        raise VaultLineageAccessLayerRefused(KV_ACCESS_LAYER1_REFUSED, (
            "no access_receipt_verifier was supplied, so the layer receipts cannot be checked against the gates' "
            "receipt stores; supply the layer-2 gate's verify_access_chain"))
    try:
        out = verifier(kv_hash, skap_hash)
    except Exception as exc:  # a verifier fault is a refusal, never an admission
        out = {"failure_code": KV_ACCESS_LAYER1_REFUSED,
               "required_evidence_or_repair": f"the access-layer verifier raised {type(exc).__name__}"}
    if not isinstance(out, dict) or out.get("disposition") != "ALLOW":
        code = out.get("failure_code") if isinstance(out, dict) else None
        detail = out.get("required_evidence_or_repair") if isinstance(out, dict) else None
        raise VaultLineageAccessLayerRefused(code if code in LAYER_PREDICATES else KV_ACCESS_LAYER1_REFUSED,
                                             detail or "the access-layer receipts did not verify")
    return kv_hash, skap_hash


def vault_lineage_custody_fail_closed(code: str, detail: str, *, failure_class: str = "B",
                                      failed_predicate: str = VAULT_LINEAGE_CUSTODY_PREDICATE) -> Dict[str, Any]:
    """Six-field FAIL_CLOSED disposition for the vault-lineage custody handoff (never an exception)."""
    return {
        "schema": VAULT_LINEAGE_RECEIPT_SCHEMA,
        "record_type": "KV_SKAP_VAULT_LINEAGE",
        "disposition": "FAIL_CLOSED",
        "failure_code": code,
        "failed_predicate": failed_predicate,
        "required_evidence_or_repair": detail,
        "retry_entrypoint": VAULT_LINEAGE_CUSTODY_RETRY,
        "owning_existing_goal": VAULT_LINEAGE_CUSTODY_GOAL,
        "next_attempt": "on the next admitted provider WRITE receipt and custody read-back for this lineage",
        "failure_class": failure_class,
        "exact_hash_readback_verified": False,
        "authority_effect": "NONE",
    }


def validate_vault_lineage_custody_result(
    *,
    binding: Dict[str, Any],
    provider_receipt: Dict[str, Any],
    read_back_lineage: Dict[str, Any],
    access_receipt_verifier: Any = None,
) -> Dict[str, Any]:
    """E0 terminal of the durable-custody validation handoff. Returns a disposition, never raises: ALLOW with the
    custody receipt, or a six-field FAIL_CLOSED naming what the provider receipt or read-back lacks."""
    try:
        return _validate_vault_lineage_custody_result_strict(
            binding=binding, provider_receipt=provider_receipt, read_back_lineage=read_back_lineage,
            access_receipt_verifier=access_receipt_verifier)
    except VaultLineageAccessLayerRefused as exc:
        return vault_lineage_custody_fail_closed(exc.code, str(exc), failed_predicate=LAYER_PREDICATES[exc.code])
    except TaskRegistryEventCustodyBindingError as exc:
        return vault_lineage_custody_fail_closed(
            "VAULT_LINEAGE_CUSTODY_RESULT_NOT_VERIFIED",
            f"{exc}; supply an admitted provider WRITE receipt for the bound request and the exact read-back lineage")
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        return vault_lineage_custody_fail_closed(
            "VAULT_LINEAGE_CUSTODY_INPUT_MALFORMED",
            f"malformed binding, provider receipt or read-back ({type(exc).__name__}: {exc}); "
            "rebuild them with build_vault_lineage_custody_binding and the provider adapter")


def _validate_vault_lineage_custody_result_strict(
    *,
    binding: Dict[str, Any],
    provider_receipt: Dict[str, Any],
    read_back_lineage: Dict[str, Any],
    access_receipt_verifier: Any = None,
) -> Dict[str, Any]:
    """The admitted provider WRITE receipt plus the lineage read back from custody: the read-back bytes must
    re-derive to the bound lineage hash and head, so reconstruction on any device starts from exactly them."""
    _require(isinstance(binding, dict) and isinstance(provider_receipt, dict), "binding and provider receipt required")
    _require(binding.get("schema") == VAULT_LINEAGE_BINDING_SCHEMA, "unexpected vault lineage binding schema")
    request = binding.get("provider_write_request")
    _require(isinstance(request, dict), "provider write request required")
    _require(provider_receipt.get("schema") == PROVIDER_RECEIPT_SCHEMA, "provider receipt schema mismatch")
    for field in ("request_id", "instance_id", "kv_set_id", "provider_id"):
        _require(provider_receipt.get(field) == request.get(field), f"provider receipt {field} mismatch")
    _require(provider_receipt.get("operation") == "WRITE", "provider receipt must prove WRITE")
    _require(provider_receipt.get("governance_state") == "ADMITTED", "provider WRITE requires ADMITTED governance")
    _require(provider_receipt.get("provider_operation_executed") is True, "provider WRITE execution evidence required")
    for field, label in (("interlock_receipt_ref", "Interlock receipt"), ("intr_receipt_ref", "InTr receipt"),
                         ("skap_credential_ref", "SKAP credential reference"),
                         ("provider_result_ref", "provider result evidence")):
        _require(bool(str(provider_receipt.get(field) or "").strip()), f"{label} required")
    _require(provider_receipt.get("credential_material_present") is False, "credential material prohibited")
    _require(provider_receipt.get("authority_effect") == "NONE", "provider receipt cannot grant authority")
    _require(request.get("object_ref") == binding.get("lineage_sha256"), "provider request object_ref must bind the lineage hash")
    readback = build_vault_lineage_record(exported_lineage=read_back_lineage)
    _require(readback["lineage_sha256"] == binding.get("lineage_sha256"), "read-back lineage hash mismatch")
    _require(readback["head_receipt_hash"] == binding.get("head_receipt_hash"), "read-back lineage head mismatch")
    kv_access_receipt_hash, skap_access_receipt_hash = _require_access_layers(provider_receipt, access_receipt_verifier)
    return {
        "schema": VAULT_LINEAGE_RECEIPT_SCHEMA,
        "record_type": "KV_SKAP_VAULT_LINEAGE",
        "disposition": "ALLOW",
        "task_id": binding.get("task_id"),
        "principal_ref": binding.get("principal_ref"),
        "lineage_sha256": binding["lineage_sha256"],
        "read_back_lineage_sha256": readback["lineage_sha256"],
        "head_receipt_hash": binding["head_receipt_hash"],
        "receipt_count": binding["receipt_count"],
        "custody_class": CUSTODY_CLASS,
        "provider_adapter_ref": f"continuity-vault-kit:runtime/kv_storage_provider_adapter.py#{request['provider_id']}",
        "interlock_intr_receipt_ref": f"{provider_receipt['interlock_receipt_ref']}|{provider_receipt['intr_receipt_ref']}",
        "kv_instance_ref": request["instance_id"],
        "provider_operation_request_id": request["request_id"],
        "provider_readback_request_id": binding["provider_readback_request"]["request_id"],
        "provider_result_ref": provider_receipt["provider_result_ref"],
        "skap_credential_ref": provider_receipt["skap_credential_ref"],
        "kv_access_receipt_hash": kv_access_receipt_hash,
        "skap_access_receipt_hash": skap_access_receipt_hash,
        "exact_hash_readback_verified": True,
        "authority_effect": "NONE",
    }
