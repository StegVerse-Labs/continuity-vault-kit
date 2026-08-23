#!/usr/bin/env python3
"""Synthetic-only tests for actionable HANDOFF/index reconciliation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "incident_reconcile.py"
HANDOFF = ROOT / "tests" / "fixtures" / "actionable_handoff_state.synthetic.json"
INDEX = ROOT / "tests" / "fixtures" / "actionable_incidents.synthetic.jsonl"


def run(handoff: Path, index: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), str(handoff), str(index)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


def test_clear_state() -> None:
    result = run(HANDOFF, INDEX)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["states"] == ["CLEAR"]
    assert payload["source_records_opened"] == 0
    assert payload["reconcile_path"] == "HANDOFF_STATE->INCIDENT_INDEX->CONSISTENCY_CHECK"


def test_handoff_stale_when_incident_missing_from_handoff() -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["incident_ids"] = ["SYNTH-VA-001"]
    handoff["active_incident_ids"] = ["SYNTH-VA-001"]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "handoff.json"
        path.write_text(json.dumps(handoff), encoding="utf-8")
        result = run(path, INDEX)
    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert "HANDOFF_STALE" in payload["states"]
    assert payload["details"]["missing_from_handoff"] == ["SYNTH-VA-002"]


def test_handoff_conflict_for_unknown_active_incident() -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["incident_ids"].append("SYNTH-VA-999")
    handoff["active_incident_ids"].append("SYNTH-VA-999")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "handoff.json"
        path.write_text(json.dumps(handoff), encoding="utf-8")
        result = run(path, INDEX)
    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert "HANDOFF_CONFLICT" in payload["states"]
    assert payload["details"]["active_missing"] == ["SYNTH-VA-999"]


def test_invalid_handoff_fails_closed() -> None:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    handoff["schema_version"] = "wrong"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "handoff.json"
        path.write_text(json.dumps(handoff), encoding="utf-8")
        result = run(path, INDEX)
    assert result.returncode == 2
    assert "schema_version" in result.stderr


def main() -> int:
    tests = [
        test_clear_state,
        test_handoff_stale_when_incident_missing_from_handoff,
        test_handoff_conflict_for_unknown_active_incident,
        test_invalid_handoff_fails_closed,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS {len(tests)} incident-reconcile tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
