#!/usr/bin/env python3
"""Self-contained tests for tools/incident_index.py using synthetic-only data."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "incident_index.py"
FIXTURE = ROOT / "tests" / "fixtures" / "actionable_incidents.synthetic.jsonl"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_validate_fixture() -> None:
    result = run("validate", str(FIXTURE))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"incident_count": 2, "valid": True}


def test_bounded_query_does_not_open_source_records() -> None:
    result = run("query", str(FIXTURE), "--term", "communication", "--term", "failure")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["query_path"] == "HANDOFF->INCIDENT_INDEX->INCIDENT->EVIDENCE_REFS"
    assert payload["source_records_opened"] == 0
    assert payload["matched"] == 1
    incident = payload["incidents"][0]
    assert incident["incident_id"] == "SYNTH-VA-002"
    assert "facts" not in incident
    assert all(ref.startswith("kv://synthetic/") for ref in incident["evidence_refs"])


def test_claim_relevance_query() -> None:
    result = run("query", str(FIXTURE), "--term", "GI")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["matched"] == 2


def test_duplicate_ids_fail_closed() -> None:
    first = FIXTURE.read_text(encoding="utf-8").splitlines()[0]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.jsonl"
        path.write_text(first + "\n" + first + "\n", encoding="utf-8")
        result = run("validate", str(path))
    assert result.returncode == 2
    assert "duplicate incident_id" in result.stderr


def test_invalid_fact_basis_fails_closed() -> None:
    obj = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    obj["facts"][0]["basis"] = "MODEL_GUESS"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.jsonl"
        path.write_text(json.dumps(obj) + "\n", encoding="utf-8")
        result = run("validate", str(path))
    assert result.returncode == 2
    assert "basis is invalid" in result.stderr


def main() -> int:
    tests = [
        test_validate_fixture,
        test_bounded_query_does_not_open_source_records,
        test_claim_relevance_query,
        test_duplicate_ids_fail_closed,
        test_invalid_fact_basis_fails_closed,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} incident-index tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
