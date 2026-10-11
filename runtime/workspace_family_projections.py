"""Read-only delivery of capability-family KV projections to the WorkSpace page (Site#1509 P4 delivery).

Family producers (CryptoBot portfolio, calendars, email, ...) emit their own read-only KV projections
with ``stegverse.kv.workspace-projection-metadata/v1`` metadata; the authorized KV writer persists each
one under ``_System/Workspace/projections/<name>.json``. This module only reads that directory, checks
that every file is a PERSONAL, non-authorizing projection carrying its own metadata, refuses secrets
and duplicate schemas (an ambiguous source is never resolved by picking one), and returns the list for
the DEVICE_KV query path to deliver. It writes nothing, contacts no provider, re-stamps no metadata
and grants no authority. The personal workspace and tasks projections travel under their own record
classes and are refused here.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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

PROJECTIONS_REL = WORKSPACE_REL / "projections"
DELIVERY_SCHEMA = "stegverse.kv.workspace-family-projections/v1"
OWN_CLASS_SCHEMAS = {
    "stegverse.kv.personal-workspace-projection/v1",
    "stegverse.kv.workspace-tasks-projection/v1",
    "stegverse.kv.workspace-continuity-checkpoint/v1",
}
_SCHEMA_PATTERN = re.compile(r"^stegverse\.kv\.[a-z0-9-]+-projection/v[0-9]+$")
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$")
FLAG_KEYS = ("credential_material_present", "provider_operation_authorized", "workspace_grants_authority", "trade_authority_granted")


def _read_projection(root: Path, path: Path) -> dict[str, Any]:
    name = path.name
    _require(_NAME_PATTERN.match(name) is not None, "family_projection_name_invalid:" + name)
    _require(root in path.resolve().parents, "workspace_path_escape")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise WorkspaceProjectionError("family_projection_unreadable:" + name) from exc
    _require(isinstance(value, dict), "family_projection_object_required:" + name)
    schema = value.get("schema")
    _require(isinstance(schema, str) and _SCHEMA_PATTERN.match(schema) is not None, "family_projection_schema_invalid:" + name)
    _require(schema not in OWN_CLASS_SCHEMAS, "family_projection_schema_reserved:" + name)
    _require(value.get("workspace_type") == "PERSONAL", "family_projection_workspace_type_invalid:" + name)
    _require(value.get("authority_effect") == "NONE", "family_projection_authority_invalid:" + name)
    for flag in ("credential_material_present", "provider_operation_authorized", "workspace_grants_authority"):
        _require(value.get(flag) is False, "family_projection_flag_invalid:" + name + ":" + flag)
    if "trade_authority_granted" in value:
        _require(value["trade_authority_granted"] is False, "family_projection_trade_authority_invalid:" + name)
    meta = value.get("projection_metadata")
    _require(isinstance(meta, dict) and meta.get("schema") == METADATA_SCHEMA, "family_projection_metadata_invalid:" + name)
    _require(meta.get("workspace_type") == "PERSONAL" and meta.get("authority_effect") == "NONE", "family_projection_metadata_context_invalid:" + name)
    _require(isinstance(meta.get("observed_at"), str) and bool(meta["observed_at"]), "family_projection_metadata_observed_at_missing:" + name)
    # The contract's own boolean authority flags (validated above) contain the word "credential"; scan everything else.
    _reject_secrets({k: v for k, v in value.items() if k not in FLAG_KEYS}, name)
    return value


def get_personal_family_projections(*, kv_data_root: Path, clock: Callable[[], datetime] = _utc_now) -> dict[str, Any]:
    root = _root(kv_data_root)
    context = _read_optional(root, "workspace.json")
    directory = (root / PROJECTIONS_REL).resolve()
    _require(root in directory.parents, "workspace_path_escape")
    projections: list[dict[str, Any]] = []
    sources: dict[str, Any] = {}
    seen: set[str] = set()
    if directory.is_dir():
        for path in sorted(p for p in directory.iterdir() if p.is_file()):
            value = _read_projection(root, path)
            _require(value["schema"] not in seen, "family_projection_schema_ambiguous:" + value["schema"])
            seen.add(value["schema"])
            projections.append(value)
            sources[path.name] = value
    produced = clock()
    _require(isinstance(produced, datetime) and produced.tzinfo is not None, "projection_clock_must_be_timezone_aware")
    canonical = json.dumps(sources, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    revision = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "schema": DELIVERY_SCHEMA,
        "state": "KV_FAMILY_PROJECTIONS_PROJECTED" if projections else "KV_FAMILY_PROJECTIONS_EMPTY",
        "workspace_type": "PERSONAL",
        "projections": projections,
        "projection_schemas": [p["schema"] for p in projections],
        "credential_material_present": False,
        "provider_operation_authorized": False,
        "workspace_grants_authority": False,
        "action_authority": "NONE",
        "projection_metadata": {
            "schema": METADATA_SCHEMA,
            "observed_at": produced.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "observed_at_semantics": "KV_PROJECTION_PRODUCTION_TIME",
            "source_revision": revision,
            "provenance_ref": "kv-workspace-family-projections-source:sha256:" + revision,
            "workspace_type": "PERSONAL",
            "workspace_id": _context_ref(context, "workspace_id"),
            "owner_principal_id": _context_ref(context, "owner_principal_id"),
            "grant_state": "UNKNOWN",
            "revocation_epoch": None,
            "authority_effect": "NONE",
        },
        "authority_effect": "NONE",
    }
