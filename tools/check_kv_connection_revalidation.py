#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "KV_CONNECTION_REVALIDATION_PROOF_MIRROR_HANDOFF.md",
 "schemas/kv-connection-conformance-proof.schema.json",
 "schemas/kv-connection-readback-proof.schema.json",
 "runtime/connection_revalidation.py",
 "tests/test_connection_revalidation.py"
]
for rel in required:
    if not (ROOT/rel).is_file(): raise SystemExit(f"missing connection revalidation artifact: {rel}")
for rel in [x for x in required if x.endswith(".json")]:
    json.loads((ROOT/rel).read_text(encoding="utf-8"))
runtime=(ROOT/"runtime/connection_revalidation.py").read_text(encoding="utf-8")
for marker in ["direct source verification required","provider session verification required","private KV readback verification required","revalidation proof predates","provider operation authority prohibited","credential material prohibited","verify_connection"]:
    if marker not in runtime: raise SystemExit(f"missing revalidation invariant: {marker}")
print("KV connection revalidation static checks: PASS")
