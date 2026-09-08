"""Private-KV persistence for inter-instance relationship requests and state.

This module materializes relationship records inside an admitted local/private KV root.
It does not perform provider login, data movement, replication, AI exposure, or grant
Interlock/InTr authority.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

from runtime.kv_instance_relationships import (
    TRANSITION_SCHEMA,
    KVRelationshipTier,
    relationship_record,
)

STATE_SCHEMA = "stegverse.kv.relationship-state/v1"


class KVRelationshipStateError(ValueError):
    pass


def canonical_paths(kv_root: Path) -> dict[str, Path]:
    root = kv_root.expanduser().resolve()
    base = root / "_System" / "Instances" / "Relationships"
    return {
        "root": base,
        "requests": base / "Requests",
        "state": base / "relationship-state.json",
        "receipts": base / "Receipts",
    }


def initialize_store(kv_root: Path, *, kv_set_id: str, instance_id: str) -> Dict[str, Any]:
    if not kv_set_id.strip():
        raise KVRelationshipStateError("kv_set_id is required")
    if not instance_id.startswith("kvi_"):
        raise KVRelationshipStateError("instance_id must use kvi_ identifier")
    paths = canonical_paths(kv_root)
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["requests"].mkdir(parents=True, exist_ok=True)
    paths["receipts"].mkdir(parents=True, exist_ok=True)
    if not paths["state"].exists():
        state = {
            "schema": STATE_SCHEMA,
            "kv_set_id": kv_set_id.strip(),
            "instance_id": instance_id,
            "relationship": relationship_record(KVRelationshipTier.NOT_CONNECTED),
            "governance_state": "NOT_CONNECTED",
            "last_admitted_request_id": None,
            "last_interlock_receipt_ref": None,
            "last_intr_receipt_ref": None,
            "authority_effect": "NONE",
            "activation_effect": False,
        }
        paths["state"].write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return load_state(kv_root)


def load_state(kv_root: Path) -> Dict[str, Any]:
    path = canonical_paths(kv_root)["state"]
    if not path.is_file():
        raise KVRelationshipStateError("relationship state store is not initialized")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise KVRelationshipStateError("relationship state is unreadable") from exc
    if state.get("schema") != STATE_SCHEMA:
        raise KVRelationshipStateError("unexpected relationship state schema")
    if state.get("authority_effect") != "NONE" or state.get("activation_effect") is not False:
        raise KVRelationshipStateError("source relationship state cannot claim authority or activation")
    return state


def persist_transition_request(kv_root: Path, request: Dict[str, Any]) -> Path:
    if request.get("schema") != TRANSITION_SCHEMA:
        raise KVRelationshipStateError("unexpected transition request schema")
    if request.get("governance_state") != "PENDING_INTERLOCK_INTR":
        raise KVRelationshipStateError("only pending governed requests may be source-persisted")
    if request.get("authority_effect") != "NONE" or request.get("activation_effect") is not False:
        raise KVRelationshipStateError("transition request cannot claim authority or activation")
    if request.get("data_moved") is not False or request.get("replication_started") is not False or request.get("ai_corpus_exposed") is not False:
        raise KVRelationshipStateError("pending request cannot claim runtime effects")
    request_id = str(request.get("request_id") or "")
    if not request_id.startswith("kvrel_"):
        raise KVRelationshipStateError("request_id invalid")
    path = canonical_paths(kv_root)["requests"] / f"{request_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = copy.deepcopy(request)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def apply_admitted_transition(
    kv_root: Path,
    *,
    request: Dict[str, Any],
    admission: Dict[str, Any],
) -> Dict[str, Any]:
    """Materialize an already-admitted relationship transition.

    This function is intentionally evidence-gated. It does not decide admission.
    The caller must supply authentic runtime admission evidence references.
    """
    if request.get("schema") != TRANSITION_SCHEMA:
        raise KVRelationshipStateError("unexpected transition request schema")
    if admission.get("governance_state") != "ADMITTED":
        raise KVRelationshipStateError("transition requires ADMITTED governance evidence")
    if admission.get("request_id") != request.get("request_id"):
        raise KVRelationshipStateError("admission request binding mismatch")
    interlock_ref = str(admission.get("interlock_receipt_ref") or "").strip()
    intr_ref = str(admission.get("intr_receipt_ref") or "").strip()
    if not interlock_ref or not intr_ref:
        raise KVRelationshipStateError("Interlock and InTr receipt references are required")
    if admission.get("authority_effect") not in {None, "NONE"}:
        raise KVRelationshipStateError("admission evidence cannot create source authority")

    current = load_state(kv_root)
    if current.get("kv_set_id") != request.get("kv_set_id"):
        raise KVRelationshipStateError("kv_set_id mismatch")
    if current.get("relationship", {}).get("tier") != request.get("current_tier"):
        raise KVRelationshipStateError("current tier does not match persisted state")

    target = str(request.get("target_tier") or "")
    try:
        relationship = relationship_record(KVRelationshipTier[target])
    except Exception as exc:
        raise KVRelationshipStateError("target tier invalid") from exc

    next_state = {
        **current,
        "relationship": relationship,
        "governance_state": "ADMITTED",
        "last_admitted_request_id": request["request_id"],
        "last_interlock_receipt_ref": interlock_ref,
        "last_intr_receipt_ref": intr_ref,
        "authority_effect": "NONE",
        "activation_effect": False,
    }
    canonical_paths(kv_root)["state"].write_text(json.dumps(next_state, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    receipt = {
        "schema": "stegverse.kv.relationship-transition-receipt/v1",
        "request_id": request["request_id"],
        "kv_set_id": request["kv_set_id"],
        "from_tier": request["current_tier"],
        "to_tier": target,
        "interlock_receipt_ref": interlock_ref,
        "intr_receipt_ref": intr_ref,
        "authority_effect": "NONE",
        "activation_effect": False,
    }
    receipt_path = canonical_paths(kv_root)["receipts"] / f"{request['request_id']}.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return copy.deepcopy(next_state)
