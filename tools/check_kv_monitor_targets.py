#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "KV_MONITOR_TARGETS_CANONICAL_STATE_MIRROR_HANDOFF.md",
 "schemas/kv-provider-monitor-targets.schema.json",
 "vault_template/KnowledgeVault/_System/Connections/Monitor_Targets.json",
 "runtime/connection_monitor_targets.py",
 "tests/test_connection_monitor_targets.py"
]
for rel in required:
    if not (ROOT/rel).is_file(): raise SystemExit(f"missing KV monitor target artifact: {rel}")
json.loads((ROOT/"schemas/kv-provider-monitor-targets.schema.json").read_text())
template=json.loads((ROOT/"vault_template/KnowledgeVault/_System/Connections/Monitor_Targets.json").read_text())
if template!={"schema":"stegverse.kv.provider-monitor-targets/v1","authority_effect":"NONE","targets":[]}:
    raise SystemExit("monitor target template must remain empty and non-authorizing")
runtime=(ROOT/"runtime/connection_monitor_targets.py").read_text()
for marker in ["https","embedded URL credentials prohibited","allowed_host mismatch","authority effect must remain NONE"]:
    if marker not in runtime: raise SystemExit(f"missing monitor target invariant: {marker}")
print("KV monitor target static checks: PASS")
