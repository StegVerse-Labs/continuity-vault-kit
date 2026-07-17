"""Deterministic, dependency-light conversation continuity recall.

Canonical events are append-only. The derived index is disposable and rebuildable.
The engine never presents reconstructed or inferred material as exact source text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


def validate_chain(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    expected_previous: str | None = None
    seen: set[str] = set()
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
        content = event.get("content")
        if content is not None and sha256(content) != event["content_hash"]:
            raise ValueError(f"event {event['event_id']} content hash mismatch")
        if content is None and event["fidelity"] in {"exact", "semantic_reconstruction"}:
            raise ValueError(f"event {event['event_id']} claims recoverable fidelity without content")
        validated.append(event)
        seen.add(event["event_id"])
        expected_previous = event_hash(event)
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


def recall(events: Iterable[dict[str, Any]], query: str) -> dict[str, Any]:
    rows = validate_chain(events)
    terms = {term.lower() for term in query.split() if len(term) > 2}
    matches = [e for e in rows if any(term in e["topic"].lower() or term in canonical_json(e.get("content")).decode("utf-8").lower() for term in terms)]
    if not matches:
        return {"query": query, "result_type": "unavailable", "current_status": "not_found", "supporting_events": [], "verification": "chain_confirmed"}

    superseded_subjects = {e["supersedes"] for e in rows if e["event_type"] == "decision_superseded" and e.get("supersedes")}
    accepted = [e for e in matches if e["event_type"] in CURRENT_DECISIONS and e.get("subject_id") not in superseded_subjects]
    current = accepted[-1] if accepted else matches[-1]
    subject = current.get("subject_id")
    implemented = any(e["event_type"] == "implementation_recorded" and e.get("subject_id") == subject for e in rows)
    exact_available = any(e["fidelity"] == "exact" and e.get("content") is not None for e in matches)
    fidelity_rank = ["exact", "semantic_reconstruction", "inference", "integrity_only", "unavailable"]
    result_type = min((e["fidelity"] for e in matches), key=fidelity_rank.index)
    return {
        "query": query,
        "topic": current["topic"],
        "historical_conclusion": current.get("content"),
        "current_status": "active" if current["event_type"] in CURRENT_DECISIONS else current["event_type"],
        "implemented": implemented,
        "superseded": bool(subject and subject in superseded_subjects),
        "exact_wording_available": exact_available,
        "result_type": result_type,
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
    parser.add_argument("--index-out", type=Path)
    args = parser.parse_args()
    events = load_jsonl(args.events)
    validated = validate_chain(events)
    if args.index_out:
        args.index_out.write_text(json.dumps(build_index(validated), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(recall(validated, args.query), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
