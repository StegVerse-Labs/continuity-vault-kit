#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    ROOT / "reconstructive_memory" / "core.py",
    ROOT / "reconstructive_memory" / "access.py",
    ROOT / "reconstructive_memory" / "routing.py",
    ROOT / "reconstructive_memory" / "proofs.py",
    ROOT / "reconstructive_memory" / "ingestion.py",
    ROOT / "reconstructive_memory" / "lifecycle.py",
    ROOT / "reconstructive_memory" / "session.py",
    ROOT / "schemas" / "reconstructive-memory-event.v0.1.json",
    ROOT / "schemas" / "reconstructive-memory-access-receipt.v0.1.json",
    ROOT / "docs" / "RECONSTRUCTIVE_AI_MEMORY.md",
)

SCHEMAS = REQUIRED[7:9]


def fail(message: str) -> None:
    raise SystemExit(f"RECONSTRUCTIVE MEMORY VALIDATION FAILED: {message}")


def main() -> int:
    for path in REQUIRED:
        if not path.is_file():
            fail(f"missing required file: {path.relative_to(ROOT)}")

    for schema in SCHEMAS:
        try:
            data = json.loads(schema.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"invalid schema {schema.relative_to(ROOT)}: {exc}")
        if data.get("type") != "object" or not data.get("required"):
            fail(f"schema is incomplete: {schema.relative_to(ROOT)}")

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_reconstructive_memory*.py"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        fail("unit tests failed")

    print("RECONSTRUCTIVE MEMORY VALIDATION PASSED")
    print("- minimal chain: present")
    print("- pair/epoch authorization: present")
    print("- dual proof verification boundary: present")
    print("- minimized chat ingestion boundary: present")
    print("- key unwrap boundary: present")
    print("- opaque routing: present")
    print("- expiring single-use capability controls: present")
    print("- protected-object tombstone controls: present")
    print("- coordinated reconstruction session: present")
    print("- plaintext-free access receipt: present")
    print("- production cryptography: NOT CLAIMED")
    print("- live Ecosystem Chat transport integration: NOT CLAIMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
