"""Read-only delivery of the stored WorkSpace continuity checkpoint and its transition decision (Site#1509 WS-ASSISTANT delivery).

The authorized KV writer (registry decision BLK3) persists the current checkpoint at
``_System/Workspace/continuity-checkpoint.json`` and the last accepted one at
``_System/Workspace/continuity-checkpoint.previous.json``, both exactly
``stegverse.kv.workspace-continuity-checkpoint/v1``. This module reads them, verifies the transition
with ``runtime/workspace_continuity_checkpoint.verify_transition`` against the workspace context
(owner principal, PERSONAL, workspace id) and returns ``{checkpoint, decision}`` for the DEVICE_KV
query path to deliver. No anchor verifier is available here, so the decision can never be ALLOW /
VERIFIED from this reader: a well-linked chain yields FAIL_CLOSED CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE
with replay UNKNOWN, and chain faults yield the verifier's DENY. It writes nothing and grants no authority.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from runtime.workspace_continuity_checkpoint import CHECKPOINT_SCHEMA, RESULT_SCHEMA, verify_transition
from runtime.workspace_projection import (
    METADATA_SCHEMA,
    WORKSPACE_REL,
    WorkspaceProjectionError,
    _context_ref,
    _read_optional,
    _reject_secrets,
    _require,
    _root,
    _utc_now,
)

CHECKPOINT_FILE = "continuity-checkpoint.json"
PREVIOUS_FILE = "continuity-checkpoint.previous.json"
DELIVERY_SCHEMA = "stegverse.kv.workspace-continuity-checkpoint-delivery/v1"


def _read_checkpoint(root: Path, name: str) -> dict[str, Any] | None:
    path = (root / WORKSPACE_REL / name).resolve()
    _require(root in path.parents, "workspace_path_escape")
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WorkspaceProjectionError("checkpoint_file_unreadable:" + name) from exc
    _require(isinstance(value, dict), "checkpoint_file_object_required:" + name)
    _require(value.get("schema") == CHECKPOINT_SCHEMA, "checkpoint_file_schema_invalid:" + name)
    _reject_secrets(value, name)
    return value


def get_personal_continuity_checkpoint(*, kv_data_root: Path, clock: Callable[[], datetime] = _utc_now) -> dict[str, Any]:
    root = _root(kv_data_root)
    context = _read_optional(root, "workspace.json")
    current = _read_checkpoint(root, CHECKPOINT_FILE)
    previous = _read_checkpoint(root, PREVIOUS_FILE)
    decision: dict[str, Any] | None = None
    if current is not None:
        owner = _context_ref(context, "owner_principal_id")
        _require(owner is not None, "checkpoint_context_owner_required")
        decision = verify_transition(
            previous,
            current,
            principal_id=owner,
            workspace_type="PERSONAL",
            workspace_id=_context_ref(context, "workspace_id"),
            anchor_verifier=None,
        )
        _require(decision.get("schema") == RESULT_SCHEMA and decision.get("authority_effect") == "NONE", "checkpoint_decision_invalid")
        _require(decision.get("disposition") != "ALLOW", "checkpoint_decision_cannot_be_verified_here")
    else:
        _require(previous is None, "checkpoint_previous_without_current")
    produced = clock()
    _require(isinstance(produced, datetime) and produced.tzinfo is not None, "projection_clock_must_be_timezone_aware")
    sources = {CHECKPOINT_FILE: current, PREVIOUS_FILE: previous}
    canonical = json.dumps(sources, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema": DELIVERY_SCHEMA,
        "state": "KV_CHECKPOINT_PROJECTED" if current is not None else "KV_CHECKPOINT_ABSENT",
        "workspace_type": "PERSONAL",
        "checkpoint": current,
        "decision": decision,
        "anchor_verified": False,
        "credential_material_present": False,
        "provider_operation_authorized": False,
        "workspace_grants_authority": False,
        "action_authority": "NONE",
        "projection_metadata": {
            "schema": METADATA_SCHEMA,
            "observed_at": produced.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "observed_at_semantics": "KV_PROJECTION_PRODUCTION_TIME",
            "source_revision": revision,
            "provenance_ref": "kv-workspace-continuity-checkpoint-source:sha256:" + revision,
            "workspace_type": "PERSONAL",
            "workspace_id": _context_ref(context, "workspace_id"),
            "owner_principal_id": _context_ref(context, "owner_principal_id"),
            "grant_state": "UNKNOWN",
            "revocation_epoch": None,
            "authority_effect": "NONE",
        },
        "authority_effect": "NONE",
    }
