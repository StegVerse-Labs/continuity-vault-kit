"""Private-KV persistence for governed storage-provider operations.

This module persists provider-operation requests and already-admitted runtime results.
It does not authenticate providers, resolve credentials, open sessions, access remote
storage, move data, synchronize KVs, or decide Interlock/InTr admission.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

from runtime.kv_storage_provider_adapter import REQUEST_SCHEMA, SUPPORTED_OPERATIONS

STATE_SCHEMA = "stegverse.kv.storage-provider-state/v1"
RECEIPT_SCHEMA = "stegverse.kv.storage-provider-operation-receipt/v1"


class KVProviderOperationStateError(ValueError):
    pass


def canonical_paths(kv_root: Path) -> dict[str, Path]:
    root = kv_root.expanduser().resolve()
    base = root / "_System" / "Instances" / "Providers"
    return {
        "root": base,
        "requests": base / "Requests",
        "receipts": base / "Receipts",
        "state": base / "provider-state.json",
    }


def initialize_store(kv_root: Path, *, instance_id: str, kv_set_id: str) -> Dict[str, Any]:
    if not instance_id.startswith("kvi_"):
        raise KVProviderOperationStateError("instance_id must use kvi_ identifier")
    if not kv_set_id.strip():
        raise KVProviderOperationStateError("kv_set_id is required")
    paths = canonical_paths(kv_root)
    paths["requests"].mkdir(parents=True, exist_ok=True)
    paths["receipts"].mkdir(parents=True, exist_ok=True)
    if not paths["state"].exists():
        payload = {
            "schema": STATE_SCHEMA,
            "instance_id": instance_id,
            "kv_set_id": kv_set_id.strip(),
            "providers": {},
            "authority_effect": "NONE",
            "credential_material_present": False,
        }
        paths["state"].write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return load_state(kv_root)


def load_state(kv_root: Path) -> Dict[str, Any]:
    path = canonical_paths(kv_root)["state"]
    if not path.is_file():
        raise KVProviderOperationStateError("provider operation store is not initialized")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise KVProviderOperationStateError("provider state is unreadable") from exc
    if value.get("schema") != STATE_SCHEMA:
        raise KVProviderOperationStateError("unexpected provider state schema")
    if value.get("authority_effect") != "NONE":
        raise KVProviderOperationStateError("provider state cannot grant authority")
    if value.get("credential_material_present") is not False:
        raise KVProviderOperationStateError("provider state cannot contain credential material")
    if not isinstance(value.get("providers"), dict):
        raise KVProviderOperationStateError("providers must be an object")
    return value


def _validate_pending_request(request: Dict[str, Any]) -> None:
    if request.get("schema") != REQUEST_SCHEMA:
        raise KVProviderOperationStateError("unexpected provider request schema")
    if request.get("governance_state") != "PENDING_INTERLOCK_INTR":
        raise KVProviderOperationStateError("only pending governed requests may be source-persisted")
    if request.get("operation") not in SUPPORTED_OPERATIONS:
        raise KVProviderOperationStateError("unsupported provider operation")
    if request.get("credential_material_present") is not False:
        raise KVProviderOperationStateError("provider request cannot contain credential material")
    for field in (
        "provider_session_established",
        "provider_operation_executed",
        "data_moved",
        "replication_started",
        "activation_effect",
    ):
        if request.get(field) is not False:
            raise KVProviderOperationStateError(f"pending provider request cannot claim {field}")
    if request.get("authority_effect") != "NONE":
        raise KVProviderOperationStateError("provider request cannot grant authority")
    if not str(request.get("request_id") or "").startswith("kvprov_"):
        raise KVProviderOperationStateError("request_id invalid")
    if not str(request.get("instance_id") or "").startswith("kvi_"):
        raise KVProviderOperationStateError("instance_id invalid")
    if not str(request.get("kv_set_id") or "").strip():
        raise KVProviderOperationStateError("kv_set_id required")
    if not str(request.get("provider_id") or "").strip():
        raise KVProviderOperationStateError("provider_id required")


def persist_operation_request(kv_root: Path, request: Dict[str, Any]) -> Path:
    _validate_pending_request(request)
    state = load_state(kv_root)
    if state["instance_id"] != request["instance_id"]:
        raise KVProviderOperationStateError("instance_id mismatch")
    if state["kv_set_id"] != request["kv_set_id"]:
        raise KVProviderOperationStateError("kv_set_id mismatch")
    path = canonical_paths(kv_root)["requests"] / f"{request['request_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(copy.deepcopy(request), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def apply_admitted_result(
    kv_root: Path,
    *,
    request: Dict[str, Any],
    admission: Dict[str, Any],
) -> Dict[str, Any]:
    """Materialize an already-admitted provider result without deciding admission."""
    _validate_pending_request(request)
    if admission.get("governance_state") != "ADMITTED":
        raise KVProviderOperationStateError("provider result requires ADMITTED governance evidence")
    if admission.get("request_id") != request.get("request_id"):
        raise KVProviderOperationStateError("admission request binding mismatch")

    interlock_ref = str(admission.get("interlock_receipt_ref") or "").strip()
    intr_ref = str(admission.get("intr_receipt_ref") or "").strip()
    if not interlock_ref or not intr_ref:
        raise KVProviderOperationStateError("Interlock and InTr receipt references are required")
    if admission.get("authority_effect") not in (None, "NONE"):
        raise KVProviderOperationStateError("provider result cannot grant source authority")
    if admission.get("credential_material_present") is not False:
        raise KVProviderOperationStateError("provider result cannot persist credential material")

    credential_ref = str(admission.get("skap_credential_ref") or "").strip()
    if request.get("skap_credential_ref_required") is True and not credential_ref:
        raise KVProviderOperationStateError("SKAP credential reference required")

    operation = request["operation"]
    executed = admission.get("provider_operation_executed")
    if executed is not True:
        raise KVProviderOperationStateError("admitted provider result must prove operation execution")

    state = load_state(kv_root)
    if state["instance_id"] != request["instance_id"] or state["kv_set_id"] != request["kv_set_id"]:
        raise KVProviderOperationStateError("provider result instance binding mismatch")

    provider_id = request["provider_id"]
    prior = copy.deepcopy(state["providers"].get(provider_id, {
        "connection_state": "DISCONNECTED",
        "verified": False,
        "last_request_id": None,
        "last_operation": None,
        "last_interlock_receipt_ref": None,
        "last_intr_receipt_ref": None,
        "last_skap_credential_ref": None,
        "last_result_ref": None,
    }))

    if operation == "CONNECT":
        connection_state = "CONNECTED"
    elif operation == "VERIFY":
        if prior["connection_state"] == "DISCONNECTED":
            raise KVProviderOperationStateError("cannot verify a disconnected provider")
        connection_state = prior["connection_state"]
    elif operation == "DISCONNECT":
        connection_state = "DISCONNECTED"
    else:
        if prior["connection_state"] == "DISCONNECTED":
            raise KVProviderOperationStateError(f"{operation} requires a connected provider")
        connection_state = prior["connection_state"]

    verified = prior["verified"]
    if operation == "VERIFY":
        verified = True
    elif operation in {"CONNECT", "DISCONNECT"}:
        verified = False

    data_moved = bool(admission.get("data_moved", False))
    replication_started = bool(admission.get("replication_started", False))
    if operation in {"CONNECT", "VERIFY", "DISCONNECT"} and (data_moved or replication_started):
        raise KVProviderOperationStateError(f"{operation} cannot claim data movement or replication")
    if operation == "READ" and replication_started:
        raise KVProviderOperationStateError("READ cannot claim replication")
    if operation == "SYNC" and admission.get("replication_started") is not True:
        raise KVProviderOperationStateError("SYNC requires replication evidence")

    result_ref = str(admission.get("provider_result_ref") or "").strip()
    if not result_ref:
        raise KVProviderOperationStateError("provider_result_ref required")

    provider_state = {
        "connection_state": connection_state,
        "verified": verified,
        "last_request_id": request["request_id"],
        "last_operation": operation,
        "last_interlock_receipt_ref": interlock_ref,
        "last_intr_receipt_ref": intr_ref,
        "last_skap_credential_ref": credential_ref,
        "last_result_ref": result_ref,
        "authority_effect": "NONE",
        "credential_material_present": False,
    }
    state["providers"][provider_id] = provider_state
    state["authority_effect"] = "NONE"
    state["credential_material_present"] = False
    canonical_paths(kv_root)["state"].write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "request_id": request["request_id"],
        "instance_id": request["instance_id"],
        "kv_set_id": request["kv_set_id"],
        "provider_id": provider_id,
        "operation": operation,
        "governance_state": "ADMITTED",
        "provider_operation_executed": True,
        "data_moved": data_moved,
        "replication_started": replication_started,
        "interlock_receipt_ref": interlock_ref,
        "intr_receipt_ref": intr_ref,
        "skap_credential_ref": credential_ref,
        "provider_result_ref": result_ref,
        "authority_effect": "NONE",
        "credential_material_present": False,
    }
    receipt_path = canonical_paths(kv_root)["receipts"] / f"{request['request_id']}.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return copy.deepcopy(state)
