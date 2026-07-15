#!/usr/bin/env python3
"""Validate governed delegation policy files without third-party dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from delegation.decision import DelegationError, validate_delegation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False

    for path in args.paths:
        try:
            policy = json.loads(path.read_text(encoding="utf-8"))
            validate_delegation(policy)
            print(f"PASS {path}")
        except (OSError, json.JSONDecodeError, DelegationError) as exc:
            failed = True
            print(f"FAIL {path}: {exc}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
