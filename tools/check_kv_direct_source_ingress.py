#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    ROOT / "KV_DIRECT_SOURCE_INGRESS_MIRROR_HANDOFF.md",
    ROOT / "schemas" / "kv-direct-source-ingress-request.schema.json",
    ROOT / "schemas" / "kv-direct-source-ingress-receipt.schema.json",
    ROOT / "runtime" / "direct_source_ingress.py",
    ROOT / "tests" / "test_direct_source_ingress.py",
]

for path in required:
    if not path.exists():
        raise SystemExit(f"missing direct-source ingress artifact: {path.relative_to(ROOT)}")

request_schema = json.loads(required[1].read_text(encoding="utf-8"))
receipt_schema = json.loads(required[2].read_text(encoding="utf-8"))

if request_schema["properties"]["requested_access"].get("const") != "READ_ONLY":
    raise SystemExit("direct-source ingress must remain read-only")
if request_schema["properties"]["direct_source_required"].get("const") is not True:
    raise SystemExit("direct-source-required invariant missing")
if request_schema["properties"]["authority_effect"].get("const") != "NONE":
    raise SystemExit("request authority must remain NONE")
if receipt_schema["properties"]["authority_effect"].get("const") != "NONE":
    raise SystemExit("receipt authority must remain NONE")

text = "\n".join(path.read_text(encoding="utf-8") for path in [required[0], required[3]])
for phrase in ["SKAP", "direct source", "FAIL_CLOSED", "READ_ONLY"]:
    if phrase not in text:
        raise SystemExit(f"missing direct-source invariant: {phrase}")

print("KV direct-source ingress static checks: PASS")
