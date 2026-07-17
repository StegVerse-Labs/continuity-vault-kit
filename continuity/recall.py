"""Deterministic, dependency-light conversation continuity recall.

Canonical events are append-only. Derived indexes are disposable and rebuildable.
The engine never presents reconstructed or inferred material as exact source text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

FIDELITY = {"exact", "semantic_reconstruction", "inference", "integrity_only", "unavailable"}
CURRENT_DECISIONS = {"decision_accepted", "decision_revised"}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def event_hash(event: dict[str, Any]) -> str:
    return sha256(event)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_chain(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    expected_previous: str | None = None
    seen: set[str] = set()
    last_time: datetime | None = None
    for position, event in enumerate(events):
        required = {"event_id", "timestamp", "actor", "event_type", "topic", "content_hash", "resulting_state_hash", "retention_class", "fidelity"}
        missing = required - event.keys()
        if missing:
            raise ValueError(f"event {position} missing fields: {sorted(missing)}")
        if event["event_id"] in seen:
            raise ValueError(f"duplicate event_id: {event['event_id']}")
        if event["fidelity"] not in FIDELITY:
            raise ValueError(f"invalid fidelity: {event['fidelity']}")
        if event.get("previous_event_hash") != expected_previous:
            raise ValueError(f"event {event['event_id']} breaks previous-event chain")
        timestamp = _time(event["timestamp"])
        if last_time and timestamp < last_time:
            raise ValueError(f"event {event['event_id']} is out of chronological order")
        content = event.get("content")
        if content is not None and sha256(content) != event["content_hash"]:
            raise ValueError(f"event {event['event_id']} content hash mismatch")
        if content is None and event["fidelity"] in {"exact", "semantic_reconstruction"}:
            raise ValueError(f"event {event['event_id']} claims recoverable fidelity without content")
        validated.append(event)
        seen.add(event["event_id"])
        expected_previous = event_hash(event)
        last_time = timestamp
    return validated


def build_index(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(events)
    by_topic: dict[str, list[str]] = {}
    by_subject: dict[str, list[str]] = {}
    superseded: set[str] = set()
    implemented: set[str] = set()
    for event in rows:
        by_topic.setdefault(event["topic"].lower(), []).append(event["event_id"])
        subject = event.get("subject_id")
        if subject:
            by_subject.setdefault(subject, []).append(event["event_id"])
        if event["event_type"] == "decision_superseded" and event.get("supersedes"):
            superseded.add(event["supersedes"])
        if event["event_type"] == "implementation_recorded" and subject:
            implemented.add(subject)
    return {
        "event_count": len(rows),
        "by_topic": by_topic,
        "by_subject": by_subject,
        "superseded_subjects": sorted(superseded),
        "implemented_subjects": sorted(implemented),
        "index_hash": sha256(rows),
    }


def archive_readiness(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = validate_chain(events)
    superseded = {e["supersedes"] for e in rows if e["event_type"] == "decision_superseded" and e.get("supersedes")}
    accepted = {e.get("subject_id") for e in rows if e["event_type"] in CURRENT_DECISIONS and e.get("subject_id") not in superseded}
    completed: set[str] = set()
    blockers: dict[str, list[str]] = {}
    for subject in sorted(s for s in accepted if s):
        implementations = [e for e in rows if e["event_type"] == "implementation_recorded" and e.get("subject_id") == subject]
        if not implementations:
            blockers[subject] = ["implementation_missing"]
            continue
        latest = implementations[-1].get("content") or {}
        missing = list(latest.get("remaining", []))
        status = latest.get("status")
        if status not in {"complete", "released", "propagated"}:
            missing.insert(0, f"implementation_status:{status or 'unknown'}")
        if missing:
            blockers[subject] = missing
        else:
            completed.add(subject)
    return {"ready": not blockers, "active_goals": sorted(s for s in accepted if s), "completed_goals": sorted(completed), "blockers": blockers}


def recall(events: Iterable[dict[str, Any]], query: str, since: str | None = None, until: str | None = None) -> dict[str, Any]:
    rows = validate_chain(events)
    lower = _time(since) if since else None
    upper = _time(until) if until else None
    scoped = [e for e in rows if (not lower or _time(e["timestamp"]) >= lower) and (not upper or _time(e["timestamp"]) <= upper)]
    terms = {term.lower().strip("?!.,") for term in query.split() if len(term.strip("?!.,")) > 2}
    matches = [e for e in scoped if any(term in e["topic"].lower() or term in canonical_json(e.get("content")).decode("utf-8").lower() for term in terms)]
    if not matches:
        return {"query": query, "result_type": "unavailable", "current_status": "not_found", "supporting_events": [], "verification": "chain_confirmed"}
    superseded_subjects = {e["supersedes"] for e in rows if e["event_type"] == "decision_superseded" and e.get("supersedes")}
    accepted = [e for e in matches if e["event_type"] in CURRENT_DECISIONS and e.get("subject_id") not in superseded_subjects]
    current = accepted[-1] if accepted else matches[-1]
    subject = current.get("subject_id")
    implementations = [e for e in rows if e["event_type"] == "implementation_recorded" and e.get("subject_id") == subject]
    fidelity_rank = ["exact", "semantic_reconstruction", "inference", "integrity_only", "unavailable"]
    return {
        "query": query,
        "time_window": {"since": since, "until": until},
        "topic": current["topic"],
        "historical_conclusion": current.get("content"),
        "current_status": "active" if current["event_type"] in CURRENT_DECISIONS else current["event_type"],
        "implementation": implementations[-1].get("content") if implementations else None,
        "implemented": bool(implementations),
        "superseded": bool(subject and subject in superseded_subjects),
        "exact_wording_available": any(e["fidelity"] == "exact" and e.get("content") is not None for e in matches),
        "result_type": min((e["fidelity"] for e in matches), key=fidelity_rank.index),
        "supporting_events": [e["event_id"] for e in matches],
        "verification": "chain_confirmed",
        "verification_root": event_hash(rows[-1]),
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("query")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--index-out", type=Path)
    parser.add_argument("--archive-readiness", action="store_true")
    args = parser.parse_args()
    events = load_jsonl(args.events)
    validated = validate_chain(events)
    if args.index_out:
        args.index_out.write_text(json.dumps(build_index(validated), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = archive_readiness(validated) if args.archive_readiness else recall(validated, args.query, args.since, args.until)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
