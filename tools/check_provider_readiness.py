#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

from reconstructive_memory.readiness import load_and_validate


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_provider_readiness.py <profile.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        report = load_and_validate(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PROVIDER READINESS INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.payload(), indent=2, sort_keys=True))
    if not report.ready:
        print("PROVIDER ACTIVATION BLOCKED", file=sys.stderr)
        return 1
    print("PROVIDER ACTIVATION READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
