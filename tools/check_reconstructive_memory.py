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
    ROOT / "reconstructive_memory" / "transport.py",
    ROOT / "reconstructive_memory" / "replay.py",
    ROOT / "reconstructive_memory" / "lifecycle.py",
    ROOT / "reconstructive_memory" / "session.py",
    ROOT / "reconstructive_memory" / "journal.py",
    ROOT / "reconstructive_memory" / "authority.py",
    ROOT / "reconstructive_memory" / "master_records.py",
    ROOT / "reconstructive_memory" / "master_records_state.py",
    ROOT / "reconstructive_memory" / "deployment.py",
    ROOT / "reconstructive_memory" / "provider_activation.py",
    ROOT / "schemas" / "reconstructive-memory-event.v0.1.json",
    ROOT / "schemas" / "reconstructive-memory-access-receipt.v0.1.json",
    ROOT / "docs" / "RECONSTRUCTIVE_AI_MEMORY.md",
    ROOT / "docs" / "PRODUCTION_PROVIDER_ACTIVATION.md",
)

SCHEMAS = REQUIRED[15:17]


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
    print("- minimal chain and bounded reconstruction: present")
    print("- pair/epoch and dual-proof authorization: present")
    print("- authenticated chat transport: present")
    print("- durable compare-and-swap replay state: present")
    print("- minimized chat ingestion and opaque routing: present")
    print("- expiring capability and tombstone controls: present")
    print("- coordinated session and plaintext-free journal: present")
    print("- authoritative receipt/capability commit boundary: present")
    print("- durable Master-Records outbox lifecycle: present")
    print("- external CAS store and delivery adapter contracts: present")
    print("- concrete provider selection and deployment receipt gate: present")
    print("- external resource identifiers and credentials: UNCONFIGURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
