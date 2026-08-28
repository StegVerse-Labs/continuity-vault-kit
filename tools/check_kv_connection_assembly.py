#!/usr/bin/env python3
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "KV_CONNECTION_ASSEMBLY_SOURCE_MIRROR_HANDOFF.md",
    "schemas/kv-connection-assembly.schema.json",
    "schemas/kv-source-change-observation.schema.json",
    "schemas/kv-connection-health-receipt.schema.json",
    "schemas/kv-connection-assembly-registry.schema.json",
    "specs/kv-connection-assembly-registry.v1.json",
    "runtime/connection_assembly.py",
    "runtime/source_change_monitor.py",
    "tests/test_connection_assembly.py",
    "tests/test_source_change_monitor.py",
]
for rel in required:
    if not (ROOT/rel).is_file(): raise SystemExit(f"missing connection assembly artifact: {rel}")
for rel in [x for x in required if x.endswith(".json")]:
    json.loads((ROOT/rel).read_text(encoding="utf-8"))
assembly=(ROOT/"runtime/connection_assembly.py").read_text(encoding="utf-8")
monitor=(ROOT/"runtime/source_change_monitor.py").read_text(encoding="utf-8")
handoff=(ROOT/"KV_CONNECTION_ASSEMBLY_SOURCE_MIRROR_HANDOFF.md").read_text(encoding="utf-8")
for marker in ["READ_ONLY","TV/TVC","SKAP_REFERENCE","credential_material_present","provider_operation_authorized"]:
    if marker not in assembly: raise SystemExit(f"missing connection assembly invariant: {marker}")
for marker in ["REVALIDATION_REQUIRED","BLOCKED_SOURCE_CHANGE","provider"]:
    if marker not in monitor: raise SystemExit(f"missing source monitor invariant: {marker}")
for forbidden in ["store passwords","provider login by itself"]:
    if forbidden not in handoff: raise SystemExit(f"handoff missing boundary: {forbidden}")
print("KV connection assembly static checks: PASS")
