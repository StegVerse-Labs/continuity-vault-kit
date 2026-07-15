#!/usr/bin/env python3
"""Local-first conversation continuity MVP.

Builds canonical hash-chained conversation events, a Merkle root, searchable
index records, and provenance-bearing historical reconstructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

GENESIS = "0" * 64
SCHEMA = "stegverse.conversation-event.v1"
RETENTION = {"integrity-only", "reconstructable", "full-fidelity"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def event_body(event: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in event.items() if k != "event_hash"}


def calculate_event_hash(event: dict[str, Any]) -> str:
    return sha256(canonical_bytes(event_body(event)))


def validate_source_event(raw: dict[str, Any], position: int) -> None:
    required = {"event_id", "timestamp", "actor", "event_type", "retention_class", "topic"}
    missing = sorted(required - raw.keys())
    if missing:
        raise ValueError(f"event {position}: missing {', '.join(missing)}")
    if raw["retention_class"] not in RETENTION:
        raise ValueError(f"event {position}: invalid retention_class")
    if raw["retention_class"] == "full-fidelity" and "content" not in raw:
        raise ValueError(f"event {position}: full-fidelity requires content")
    if raw["retention_class"] == "reconstructable" and not any(k in raw for k in ("summary", "content")):
        raise ValueError(f"event {position}: reconstructable requires summary or content")


def normalize_event(raw: dict[str, Any], previous_hash: str, position: int) -> dict[str, Any]:
    validate_source_event(raw, position)
    retention = raw["retention_class"]
    content = raw.get("content")
    record: dict[str, Any] = {
        "schema": SCHEMA,
        "sequence": position,
        "event_id": raw["event_id"],
        "timestamp": raw["timestamp"],
        "actor": raw["actor"],
        "event_type": raw["event_type"],
        "retention_class": retention,
        "topic": raw["topic"],
        "status": raw.get("status", "recorded"),
        "previous_event_hash": previous_hash,
        "content_sha256": sha256(canonical_bytes(content)) if content is not None else raw.get("content_sha256"),
        "summary": raw.get("summary") if retention in {"reconstructable", "full-fidelity"} else None,
        "content": content if retention == "full-fidelity" else None,
        "references": raw.get("references", []),
        "supersedes": raw.get("supersedes"),
        "artifact": raw.get("artifact"),
        "metadata": raw.get("metadata", {}),
    }
    record["event_hash"] = calculate_event_hash(record)
    return record


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return sha256(b"")
    layer = hashes[:]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [sha256(bytes.fromhex(layer[i]) + bytes.fromhex(layer[i + 1])) for i in range(0, len(layer), 2)]
    return layer[0]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def build(source: Path, output_dir: Path) -> dict[str, Any]:
    previous = GENESIS
    events = []
    for position, raw in enumerate(read_jsonl(source), 1):
        event = normalize_event(raw, previous, position)
        events.append(event)
        previous = event["event_hash"]
    root = merkle_root([e["event_hash"] for e in events])
    manifest = {
        "schema": "stegverse.conversation-continuity-manifest.v1",
        "source": source.name,
        "event_count": len(events),
        "chain_tip": previous,
        "merkle_root": root,
        "retention_counts": {name: sum(e["retention_class"] == name for e in events) for name in sorted(RETENTION)},
    }
    index = [{
        "event_id": e["event_id"], "sequence": e["sequence"], "timestamp": e["timestamp"],
        "actor": e["actor"], "event_type": e["event_type"], "topic": e["topic"],
        "status": e["status"], "retention_class": e["retention_class"],
        "summary": e["summary"], "artifact": e["artifact"], "supersedes": e["supersedes"],
        "event_hash": e["event_hash"], "merkle_root": root,
    } for e in events]
    write_jsonl(output_dir / "events.chained.jsonl", events)
    write_jsonl(output_dir / "continuity.index.jsonl", index)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify(output_dir: Path) -> dict[str, Any]:
    events = read_jsonl(output_dir / "events.chained.jsonl")
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    previous = GENESIS
    for position, event in enumerate(events, 1):
        if event.get("sequence") != position:
            raise ValueError(f"sequence mismatch at {position}")
        if event.get("previous_event_hash") != previous:
            raise ValueError(f"previous hash mismatch at {position}")
        calculated = calculate_event_hash(event)
        if event.get("event_hash") != calculated:
            raise ValueError(f"event hash mismatch at {position}")
        previous = calculated
    root = merkle_root([e["event_hash"] for e in events])
    if manifest.get("event_count") != len(events):
        raise ValueError("event count mismatch")
    if manifest.get("chain_tip") != previous:
        raise ValueError("chain tip mismatch")
    if manifest.get("merkle_root") != root:
        raise ValueError("Merkle root mismatch")
    return {"verified": True, "event_count": len(events), "chain_tip": previous, "merkle_root": root}


def search(output_dir: Path, query: str) -> list[dict[str, Any]]:
    terms = [t.casefold() for t in query.split() if t]
    results = []
    for record in read_jsonl(output_dir / "continuity.index.jsonl"):
        haystack = canonical_bytes(record).decode("utf-8").casefold()
        score = sum(haystack.count(term) for term in terms)
        if score:
            results.append({"score": score, **record})
    return sorted(results, key=lambda r: (-r["score"], r["sequence"]))


def reconstruct(output_dir: Path, topic: str) -> dict[str, Any]:
    verify(output_dir)
    matches = [r for r in read_jsonl(output_dir / "continuity.index.jsonl") if topic.casefold() in r["topic"].casefold()]
    if not matches:
        raise ValueError(f"no events found for topic: {topic}")
    accepted = [r for r in matches if r["event_type"] in {"decision_accepted", "decision_revised"} and r["status"] in {"accepted", "active"}]
    selected = accepted[-1] if accepted else matches[-1]
    fidelity = "exact" if selected["retention_class"] == "full-fidelity" else ("semantic reconstruction" if selected["retention_class"] == "reconstructable" else "integrity-only")
    return {
        "topic": selected["topic"],
        "reconstructed_conclusion": selected.get("summary"),
        "result_type": fidelity,
        "current_status": selected["status"],
        "source_event_id": selected["event_id"],
        "source_event_hash": selected["event_hash"],
        "supporting_event_ids": [r["event_id"] for r in matches],
        "event_count": len(matches),
        "merkle_root": selected["merkle_root"],
        "exact_content_available": selected["retention_class"] == "full-fidelity",
        "artifact": selected.get("artifact"),
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build"); b.add_argument("source", type=Path); b.add_argument("output", type=Path)
    v = sub.add_parser("verify"); v.add_argument("output", type=Path)
    s = sub.add_parser("search"); s.add_argument("output", type=Path); s.add_argument("query")
    r = sub.add_parser("reconstruct"); r.add_argument("output", type=Path); r.add_argument("topic")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "build": result = build(args.source, args.output)
        elif args.command == "verify": result = verify(args.output)
        elif args.command == "search": result = search(args.output, args.query)
        else: result = reconstruct(args.output, args.topic)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
