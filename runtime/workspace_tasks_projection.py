"""Personal KV WorkSpace tasks and commitments projection: stegverse.kv.workspace-tasks-projection/v1.

Read-only producer for Site#1509 WS-TASKS. It projects `_System/Workspace/tasks.json`
(schema stegverse.kv.workspace-tasks/v1) into a presentation projection carrying tasks,
commitments and a derived timeline, bound to the same projection metadata contract as the
Workspace projection (stegverse.kv.workspace-projection-metadata/v1). It writes nothing,
grants nothing, and marks every row as not action-eligible: completing, scheduling or
withdrawing anything is a governed transition that needs an admitted manifest elsewhere.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from runtime.workspace_projection import (
    SCHEMAS as WORKSPACE_SCHEMAS,
    WorkspaceProjectionError,
    _context_ref,
    _reject_secrets,
    _root,
    _utc_now,
)

TASKS_FILE = "tasks.json"
TASKS_SOURCE_SCHEMA = "stegverse.kv.workspace-tasks/v1"
PROJECTION_SCHEMA = "stegverse.kv.workspace-tasks-projection/v1"
METADATA_SCHEMA = "stegverse.kv.workspace-projection-metadata/v1"
TASK_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED"}
COMMITMENT_STATUSES = {"PROPOSED", "ACTIVE", "FULFILLED", "WITHDRAWN", "REVOKED"}
WORKSPACE_REL = Path("_System/Workspace")


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise WorkspaceProjectionError(reason)


def _read(root: Path, name: str, schema: str) -> dict[str, Any] | None:
    path = (root / WORKSPACE_REL / name).resolve()
    _require(root in path.parents, "workspace_path_escape")
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - exercised through the error type
        raise WorkspaceProjectionError("workspace_file_unreadable:" + name) from exc
    _require(isinstance(value, dict), "workspace_file_object_required:" + name)
    _require(value.get("schema") == schema, "workspace_file_schema_invalid:" + name)
    _require(value.get("authority_effect") == "NONE", "workspace_file_authority_invalid:" + name)
    _reject_secrets(value, name)
    return value


def _rows(value: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    rows = value.get(key, [])
    _require(isinstance(rows, list), "workspace_rows_invalid:" + key)
    _require(all(isinstance(row, dict) for row in rows), "workspace_row_object_required:" + key)
    return [dict(row) for row in rows]


def _iso(value: Any, field: str) -> str | None:
    if value is None:
        return None
    _require(isinstance(value, str) and value, field + "_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkspaceProjectionError(field + "_invalid") from exc
    _require(parsed.tzinfo is not None, field + "_timezone_required")
    return value


def _non_empty(value: Any, field: str) -> str:
    _require(isinstance(value, str) and value, field + "_required")
    return value


def _task(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["task_id"] = _non_empty(row.get("task_id"), "task_id")
    result["title"] = _non_empty(row.get("title"), "task_title")
    _require(row.get("status") in TASK_STATUSES, "task_status_invalid")
    result["due_at"] = _iso(row.get("due_at"), "task_due_at")
    result["created_at"] = _iso(row.get("created_at"), "task_created_at")
    result["source_ref"] = row.get("source_ref") if isinstance(row.get("source_ref"), str) else None
    result["action_eligible"] = False
    result["execution_requires_admitted_manifest"] = True
    result["authority_effect"] = "NONE"
    return result


def _commitment(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result["commitment_id"] = _non_empty(row.get("commitment_id"), "commitment_id")
    result["statement"] = _non_empty(row.get("statement"), "commitment_statement")
    _require(row.get("status") in COMMITMENT_STATUSES, "commitment_status_invalid")
    result["counterparty_principal_id"] = row.get("counterparty_principal_id") if isinstance(row.get("counterparty_principal_id"), str) else None
    result["due_at"] = _iso(row.get("due_at"), "commitment_due_at")
    result["source_ref"] = row.get("source_ref") if isinstance(row.get("source_ref"), str) else None
    result["action_eligible"] = False
    result["execution_requires_admitted_manifest"] = True
    result["authority_effect"] = "NONE"
    return result


def _timeline(tasks: list[dict[str, Any]], commitments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derived presentation order: dated items by due_at, then undated; never a schedule or an instruction."""
    items: list[dict[str, Any]] = []
    for t in tasks:
        items.append({"kind": "task", "id": t["task_id"], "label": t["title"], "status": t["status"], "due_at": t["due_at"], "action_eligible": False, "execution_requires_admitted_manifest": True, "authority_effect": "NONE"})
    for c in commitments:
        items.append({"kind": "commitment", "id": c["commitment_id"], "label": c["statement"], "status": c["status"], "due_at": c["due_at"], "action_eligible": False, "execution_requires_admitted_manifest": True, "authority_effect": "NONE"})
    items.sort(key=lambda i: (i["due_at"] is None, i["due_at"] or "", i["kind"], i["id"]))
    return items


def _metadata(sources: dict[str, Any], context: dict[str, Any] | None, clock: Callable[[], datetime]) -> dict[str, Any]:
    produced = clock()
    _require(isinstance(produced, datetime) and produced.tzinfo is not None, "projection_clock_must_be_timezone_aware")
    canonical = json.dumps(sources, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema": METADATA_SCHEMA,
        "observed_at": produced.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "observed_at_semantics": "KV_PROJECTION_PRODUCTION_TIME",
        "source_revision": revision,
        "provenance_ref": "kv-workspace-tasks-source:sha256:" + revision,
        "workspace_type": "PERSONAL",
        "workspace_id": _context_ref(context, "workspace_id"),
        "owner_principal_id": _context_ref(context, "owner_principal_id"),
        "grant_state": "UNKNOWN",
        "revocation_epoch": None,
        "authority_effect": "NONE",
    }


def get_personal_tasks_projection(*, kv_data_root: Path, clock: Callable[[], datetime] = _utc_now) -> dict[str, Any]:
    root = _root(kv_data_root)
    context = _read(root, "workspace.json", WORKSPACE_SCHEMAS["workspace.json"])
    source = _read(root, TASKS_FILE, TASKS_SOURCE_SCHEMA)
    tasks = [_task(row) for row in _rows(source, "tasks")]
    commitments = [_commitment(row) for row in _rows(source, "commitments")]
    ids = [t["task_id"] for t in tasks] + [c["commitment_id"] for c in commitments]
    _require(len(ids) == len(set(ids)), "task_or_commitment_id_duplicate")
    metadata = _metadata({"workspace.json": context, TASKS_FILE: source}, context, clock)
    return {
        "schema": PROJECTION_SCHEMA,
        "state": "KV_TASKS_PROJECTED" if (tasks or commitments) else "KV_TASKS_EMPTY",
        "workspace_type": "PERSONAL",
        "tasks": tasks,
        "commitments": commitments,
        "timeline": _timeline(tasks, commitments),
        "credential_material_present": False,
        "provider_operation_authorized": False,
        "workspace_grants_authority": False,
        "action_authority": "NONE",
        "projection_metadata": metadata,
        "authority_effect": "NONE",
    }
