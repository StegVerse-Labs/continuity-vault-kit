#!/usr/bin/env python3
"""Validate and query KnowledgeVault actionable incident indexes.

This tool operates on already-authorized incident index material. It does not
open or fetch private source records and deliberately returns opaque evidence
references only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "kv.actionable-incident.v1"
REQUIRED = {
    "schema_version",
    "incident_id",
    "incident_class",
    "title",
    "occurred",
    "status",
    "summary",
    "evidence_refs",
    "action_state",
    "handoff_ref",
}
ALLOWED_BASES = {"DOCUMENTED", "FIRSTHAND", "REPORTED_STATEMENT", "INFERENCE", "OPINION"}
ALLOWED_STATUS = {"OPEN", "PENDING_EXTERNAL", "PENDING_OWNER", "RESOLVED", "CLOSED_UNRESOLVED", "SUPERSEDED"}


class IncidentError(ValueError):
    pass


def _as_strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise IncidentError(f"{field} must be an array of non-empty strings")
    return value


def validate_incident(obj: Any, line_no: int | None = None) -> dict[str, Any]:
    where = f"line {line_no}: " if line_no else ""
    if not isinstance(obj, dict):
        raise IncidentError(where + "incident must be an object")
    missing = sorted(REQUIRED - set(obj))
    if missing:
        raise IncidentError(where + "missing required field(s): " + ", ".join(missing))
    if obj.get("schema_version") != SCHEMA_VERSION:
        raise IncidentError(where + f"schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(obj.get("incident_id"), str) or not obj["incident_id"].strip():
        raise IncidentError(where + "incident_id must be a non-empty string")
    if obj.get("status") not in ALLOWED_STATUS:
        raise IncidentError(where + f"unsupported status {obj.get('status')!r}")
    occurred = obj.get("occurred")
    if not isinstance(occurred, dict) or not isinstance(occurred.get("start"), str) or not occurred["start"]:
        raise IncidentError(where + "occurred.start must be a non-empty string")
    evidence_refs = _as_strings(obj.get("evidence_refs"), "evidence_refs")
    if not evidence_refs:
        raise IncidentError(where + "evidence_refs must contain at least one opaque reference")
    action_state = obj.get("action_state")
    if not isinstance(action_state, dict):
        raise IncidentError(where + "action_state must be an object")
    _as_strings(action_state.get("next_actions"), "action_state.next_actions")
    for i, fact in enumerate(obj.get("facts", [])):
        if not isinstance(fact, dict):
            raise IncidentError(where + f"facts[{i}] must be an object")
        if not isinstance(fact.get("statement"), str) or not fact["statement"].strip():
            raise IncidentError(where + f"facts[{i}].statement must be non-empty")
        if fact.get("basis") not in ALLOWED_BASES:
            raise IncidentError(where + f"facts[{i}].basis is invalid")
        _as_strings(fact.get("evidence_refs"), f"facts[{i}].evidence_refs")
    _as_strings(obj.get("claim_relevance"), "claim_relevance")
    _as_strings(obj.get("related_incident_ids"), "related_incident_ids")
    return obj


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise IncidentError(f"line {line_no}: invalid JSON: {exc.msg}") from exc
            incident = validate_incident(obj, line_no)
            incident_id = incident["incident_id"]
            if incident_id in seen:
                raise IncidentError(f"line {line_no}: duplicate incident_id {incident_id!r}")
            seen.add(incident_id)
            incidents.append(incident)
    return incidents


def searchable_strings(incident: dict[str, Any]) -> Iterable[str]:
    yield str(incident.get("incident_id", ""))
    yield str(incident.get("incident_class", ""))
    yield str(incident.get("title", ""))
    yield str(incident.get("summary", ""))
    for value in incident.get("organizations", []):
        yield str(value)
    for value in incident.get("claim_relevance", []):
        yield str(value)
    disc = incident.get("discontinuity") or {}
    for value in disc.get("types", []):
        yield str(value)
    for fact in incident.get("facts", []):
        yield str(fact.get("statement", ""))


def query_incidents(
    incidents: list[dict[str, Any]],
    terms: list[str],
    incident_class: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    terms_l = [term.casefold() for term in terms if term]
    result: list[dict[str, Any]] = []
    for incident in incidents:
        if incident_class and incident.get("incident_class") != incident_class:
            continue
        if status and incident.get("status") != status:
            continue
        haystack = "\n".join(searchable_strings(incident)).casefold()
        if terms_l and not all(term in haystack for term in terms_l):
            continue
        result.append(incident)
    return result


def bounded_result(incident: dict[str, Any]) -> dict[str, Any]:
    """Return index-level context without source-record payloads."""
    return {
        "incident_id": incident["incident_id"],
        "incident_class": incident.get("incident_class"),
        "title": incident.get("title"),
        "occurred": incident.get("occurred"),
        "status": incident.get("status"),
        "summary": incident.get("summary"),
        "discontinuity": incident.get("discontinuity"),
        "claim_relevance": incident.get("claim_relevance", []),
        "action_state": incident.get("action_state"),
        "evidence_refs": incident.get("evidence_refs", []),
        "handoff_ref": incident.get("handoff_ref"),
        "public_derivative": incident.get("public_derivative"),
    }


def cmd_validate(args: argparse.Namespace) -> int:
    incidents = read_jsonl(Path(args.index))
    print(json.dumps({"valid": True, "incident_count": len(incidents)}, sort_keys=True))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    incidents = read_jsonl(Path(args.index))
    matched = query_incidents(incidents, args.term or [], args.incident_class, args.status)
    payload = {
        "query_path": "HANDOFF->INCIDENT_INDEX->INCIDENT->EVIDENCE_REFS",
        "matched": len(matched),
        "incidents": [bounded_result(item) for item in matched],
        "source_records_opened": 0,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate an INCIDENT_INDEX.jsonl")
    validate.add_argument("index")
    validate.set_defaults(func=cmd_validate)

    query = sub.add_parser("query", help="query index-level incident metadata")
    query.add_argument("index")
    query.add_argument("--term", action="append", help="term that must occur in indexed incident metadata")
    query.add_argument("--incident-class")
    query.add_argument("--status", choices=sorted(ALLOWED_STATUS))
    query.set_defaults(func=cmd_query)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (IncidentError, OSError) as exc:
        print(f"incident-index error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
