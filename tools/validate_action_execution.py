#!/usr/bin/env python3
"""Validate governed action-execution envelopes and receipt fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from execution.adapter import ConnectorResult, ExecutionEnvelopeError, make_receipt, validate_envelope


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("envelope", type=Path)
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()

    try:
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
        validate_envelope(envelope)
        print(f"PASS {args.envelope}")
        if args.results:
            packet = json.loads(args.results.read_text(encoding="utf-8"))
            for case in packet.get("cases", []):
                result = ConnectorResult(
                    status=case["result"],
                    platform_object_id=case.get("platform_object_id"),
                    platform_url=case.get("platform_url"),
                    confirmation=case.get("confirmation"),
                    failure_code=case.get("failure_code"),
                    failure_message=case.get("failure_message"),
                    side_effect_absence_confirmed=case.get("side_effect_absence_confirmed", False),
                )
                receipt = make_receipt(envelope, result, receipt_id=f"receipt:{case['case_id']}")
                if receipt["retry_admissibility"] != case["retry_admissibility"]:
                    raise ExecutionEnvelopeError(
                        f"{case['case_id']}: retry result mismatch"
                    )
                print(f"PASS {case['case_id']} -> {receipt['result']}")
    except (OSError, json.JSONDecodeError, KeyError, ExecutionEnvelopeError) as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
