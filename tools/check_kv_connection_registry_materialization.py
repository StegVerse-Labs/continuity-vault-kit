#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
  "KV_CONNECTION_REGISTRY_MATERIALIZATION_MIRROR_HANDOFF.md",
  "vault_template/KnowledgeVault/_System/Connections/Connection_Assemblies.json",
  "vault_template/KnowledgeVault/_System/Connections/Source_Changes/README.md",
  "vault_template/KnowledgeVault/_System/Connections/Health/README.md",
  "runtime/connection_registry_store.py",
  "tests/test_connection_registry_store.py",
]
for rel in required:
  if not (ROOT/rel).is_file(): raise SystemExit(f"missing connection registry materialization artifact: {rel}")
template=json.loads((ROOT/required[1]).read_text(encoding="utf-8"))
if template!={"schema":"stegverse.kv.connection-assembly-registry/v1","state":"EMPTY","authority_effect":"NONE","assemblies":[]}:
  raise SystemExit("connection registry template must remain empty and non-authorizing")
runtime=(ROOT/"runtime/connection_registry_store.py").read_text(encoding="utf-8")
for marker in ["_System","Connections","Source_Changes","Health","provider operation authority prohibited","credential material prohibited"]:
  if marker not in runtime: raise SystemExit(f"missing materialization invariant: {marker}")
print("KV connection registry materialization static checks: PASS")
