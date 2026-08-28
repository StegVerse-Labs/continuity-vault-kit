#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    ROOT / "KV_COINBASE_FINANCE_INGRESS_MIRROR_HANDOFF.md",
    ROOT / "runtime" / "coinbase_finance_ingress.py",
    ROOT / "tests" / "test_coinbase_finance_ingress.py",
]

for path in required:
    if not path.exists():
        raise SystemExit(f"missing Coinbase finance ingress artifact: {path.relative_to(ROOT)}")

runtime = required[1].read_text(encoding="utf-8")
handoff = required[0].read_text(encoding="utf-8")

for marker in [
    "direct_source_verified",
    "session_verified",
    "READ_ONLY",
    "provider_operation_authorized",
    "execution_authority",
]:
    if marker not in runtime:
        raise SystemExit(f"missing Coinbase finance ingress invariant: {marker}")

for forbidden in ["COINBASE_API_KEY", "COINBASE_API_SECRET", "password =", "access_token ="]:
    if forbidden in runtime:
        raise SystemExit(f"credential-bearing implementation prohibited: {forbidden}")

if "does not log in to Coinbase" not in handoff:
    raise SystemExit("handoff must preserve existing TVC/SKAP authentication ownership")

print("KV Coinbase finance ingress static checks: PASS")
