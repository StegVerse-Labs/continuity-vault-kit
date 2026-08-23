#!/usr/bin/env python3
"""Reconcile actionable HANDOFF state against an incident index.

The tool works only on already-authorized machine-readable handoff metadata and
incident-index material. It does not open source personal records.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from incident_index import IncidentError, read_jsonl

HANDOFF_SCHEMA = "kv.actionable-handoff-state.v1"
CLOSED = {"RESOLVED", "CLOSED_UNRESOLVED", "SUPERSEDED"}


class ReconcileError(ValueError):
    pass


def parse_time(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ReconcileError(f"{field} must be a non-empty timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReconcileError(f"{field} must be ISO-8601") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def read_handoff(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReconcileError(f"invalid handoff JSON: {exc.msg}") from exc
    if not isinstance(obj, dict):
        raise ReconcileError("handoff must be an object")
    if obj.get("schema_version") != HANDOFF_SCHEMA:
        raise ReconcileError(f"schema_version must be {HANDOFF_SCHEMA!r}")
    for field in ("handoff_id", "workstream", "updated_at", "source_index_ref"):
        if not isinstance(obj.get(field), str) or not obj[field]:
            raise ReconcileError(f"{field} must be a non-empty string")
    for field in ("incident_ids", "active_incident_ids"):
        value = obj.get(field)
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            raise ReconcileError(f"{field} must be an array of non-empty strings")
        if len(value) != len(set(value)):
            raise ReconcileError(f"{field} must not contain duplicates")
    parse_time(obj["updated_at"], "updated_at")
    if obj.get("index_updated_at") is not None:
        parse_time(obj["index_updated_at"], "index_updated_at")
    return obj


def reconcile(handoff: dict[str, Any], incidents: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {item["incident_id"]: item for item in incidents}
    index_ids = set(by_id)
    declared_ids = set(handoff["incident_ids"])
    declared_active = set(handoff["active_incident_ids"])
    expected_active = {incident_id for incident_id, item in by_id.items() if item.get("status") not in CLOSED}

    missing_from_index = sorted(declared_ids - index_ids)
    missing_from_handoff = sorted(index_ids - declared_ids)
    active_missing = sorted(declared_active - index_ids)
    active_state_conflicts = sorted(
        incident_id for incident_id in declared_active & index_ids if by_id[incident_id].get("status") in CLOSED
    )
    unlisted_active = sorted(expected_active - declared_active)

    handoff_time = parse_time(handoff["updated_at"], "updated_at")
    index_time = None
    if handoff.get("index_updated_at"):
        index_time = parse_time(handoff["index_updated_at"], "index_updated_at")

    states: list[str] = []
    if missing_from_index or active_missing or active_state_conflicts:
        states.append("HANDOFF_CONFLICT")
    if missing_from_handoff or unlisted_active:
        states.append("HANDOFF_STALE")
    if index_time is not None and index_time > handoff_time:
        states.append("HANDOFF_STALE")
    if index_time is not None and handoff_time > index_time and missing_from_index:
        states.append("INDEX_STALE")
    if not states:
        states = ["CLEAR"]

    return {
        "reconcile_path": "HANDOFF_STATE->INCIDENT_INDEX->CONSISTENCY_CHECK",
        "source_records_opened": 0,
        "states": sorted(set(states)),
        "details": {
            "missing_from_index": missing_from_index,
            "missing_from_handoff": missing_from_handoff,
            "active_missing": active_missing,
            "active_state_conflicts": active_state_conflicts,
            "unlisted_active": unlisted_active,
        },
        "incident_count": len(incidents),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff_state")
    parser.add_argument("incident_index")
    args = parser.parse_args(argv)
    try:
        handoff = read_handoff(Path(args.handoff_state))
        incidents = read_jsonl(Path(args.incident_index))
        result = reconcile(handoff, incidents)
    except (OSError, IncidentError, ReconcileError) as exc:
        print(f"incident-reconcile error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["states"] == ["CLEAR"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
