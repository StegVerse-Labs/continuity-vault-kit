#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "conversation_continuity.py"
FIXTURE = ROOT / "examples" / "conversation_continuity" / "sample_session.jsonl"


def run(*args: str, expect: int = 0):
    result = subprocess.run([sys.executable, str(TOOL), *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}\nOUT:{result.stdout}\nERR:{result.stderr}")
    return result


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        manifest = json.loads(run("build", str(FIXTURE), str(out)).stdout)
        assert manifest["event_count"] == 4
        verified = json.loads(run("verify", str(out)).stdout)
        assert verified["verified"] is True
        results = json.loads(run("search", str(out), "bundle retention").stdout)
        assert len(results) == 4
        reconstruction = json.loads(run("reconstruct", str(out), "bundle retention").stdout)
        assert reconstruction["result_type"] == "semantic reconstruction"
        assert reconstruction["source_event_id"] == "evt-003"
        assert "master-records/dist" in reconstruction["reconstructed_conclusion"]

        chained = out / "events.chained.jsonl"
        lines = chained.read_text(encoding="utf-8").splitlines()
        event = json.loads(lines[2])
        event["summary"] = "tampered"
        lines[2] = json.dumps(event, sort_keys=True)
        chained.write_text("\n".join(lines) + "\n", encoding="utf-8")
        failure = run("verify", str(out), expect=2)
        assert "event hash mismatch" in failure.stderr
    print("OK: conversation continuity MVP self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
