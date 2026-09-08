"""Bounded MyKV projection for KnowledgeVault multi-instance state.

This module exposes instance/storage/relationship metadata only. It never includes
private KV content, credentials, provider tokens, or provider-operation authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from runtime.kv_relationship_state_store import canonical_paths as relationship_paths

PROJECTION_SCHEMA = "stegverse.kv.my-kv-instance-projection/v1"
SET_PROJECTION_SCHEMA = "stegverse.kv.my-kv-set-projection/v1"
INSTANCE_RECORD = Path("_System/Instances/instance.json")


class MyKVProjectionError(ValueError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise MyKVProjectionError(f"unreadable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise MyKVProjectionError(f"expected object: {path}")
    return value


def build_instance_projection(kv_root: Path) -> dict[str, Any]:
    root = kv_root.expanduser().resolve()
    instance_path = root / INSTANCE_RECORD
    if not instance_path.is_file():
        raise MyKVProjectionError("instance identity record missing")
    instance = _read_json(instance_path)

    instance_id = str(instance.get("instance_id") or "")
    kv_set_id = str(instance.get("kv_set_id") or "")
    if not instance_id.startswith("kvi_") or not kv_set_id:
        raise MyKVProjectionError("invalid instance identity")

    storage = instance.get("storage") or {}
    if not isinstance(storage, dict):
        raise MyKVProjectionError("storage metadata invalid")

    state_path = relationship_paths(root)["state"]
    if state_path.is_file():
        state = _read_json(state_path)
        if state.get("instance_id") != instance_id or state.get("kv_set_id") != kv_set_id:
            raise MyKVProjectionError("relationship state identity binding mismatch")
        relationship = state.get("relationship") or {}
        relationship_tier = str(relationship.get("tier") or "NOT_CONNECTED")
        relationship_governance_state = str(state.get("governance_state") or "NOT_CONNECTED")
        last_admitted_request_id = state.get("last_admitted_request_id")
    else:
        relationship_tier = str((instance.get("relationship") or {}).get("tier") or "NOT_CONNECTED")
        relationship_governance_state = "NOT_CONNECTED"
        last_admitted_request_id = None

    requests_dir = relationship_paths(root)["requests"]
    pending_request_ids = []
    if requests_dir.is_dir():
        for path in sorted(requests_dir.glob("kvrel_*.json")):
            try:
                request = _read_json(path)
            except MyKVProjectionError:
                continue
            if request.get("governance_state") == "PENDING_INTERLOCK_INTR":
                pending_request_ids.append(str(request.get("request_id") or path.stem))

    return {
        "schema": PROJECTION_SCHEMA,
        "instance_id": instance_id,
        "instance_number": instance.get("instance_number"),
        "logical_name": instance.get("logical_name"),
        "kv_set_id": kv_set_id,
        "storage": {
            "medium": storage.get("medium"),
            "locator": storage.get("locator"),
            "provider_authority_effect": "NONE",
        },
        "relationship": {
            "tier": relationship_tier,
            "governance_state": relationship_governance_state,
            "last_admitted_request_id": last_admitted_request_id,
            "pending_request_ids": pending_request_ids,
        },
        "management": {
            "request_connect_supported": True,
            "request_disconnect_supported": True,
            "request_tier_change_supported": True,
            "provider_mutation_authorized": False,
            "relationship_mutation_authorized": False,
        },
        "private_content_included": False,
        "credential_material_included": False,
        "authority_effect": "NONE_STATUS_ONLY",
        "activation_effect": False,
    }


def build_set_projection(kv_roots: Iterable[Path]) -> dict[str, Any]:
    projections = [build_instance_projection(root) for root in kv_roots]
    if not projections:
        raise MyKVProjectionError("at least one KV instance is required")
    set_ids = {item["kv_set_id"] for item in projections}
    if len(set_ids) != 1:
        raise MyKVProjectionError("all projected instances must share one kv_set_id")
    projections.sort(key=lambda item: (int(item.get("instance_number") or 0), item["instance_id"]))
    return {
        "schema": SET_PROJECTION_SCHEMA,
        "kv_set_id": next(iter(set_ids)),
        "instances": projections,
        "instance_count": len(projections),
        "private_content_included": False,
        "credential_material_included": False,
        "authority_effect": "NONE_STATUS_ONLY",
        "activation_effect": False,
    }
