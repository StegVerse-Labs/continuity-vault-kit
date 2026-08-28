#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "ORG_SECURITY_POSTURE_MIRROR_HANDOFF.md",
 "schemas/kv-organization-security-posture.schema.json",
 "schemas/kv-organization-posture-change-receipt.schema.json",
 "policy/organization-security-postures.v1.json",
 "runtime/organization_security_posture.py",
 "tests/test_organization_security_posture.py"
]
for rel in required:
    if not (ROOT/rel).is_file(): raise SystemExit("missing "+rel)
for rel in [x for x in required if x.endswith(".json")]:
    json.loads((ROOT/rel).read_text(encoding="utf-8"))
src="\n".join((ROOT/rel).read_text(encoding="utf-8") for rel in [
 "runtime/organization_security_posture.py",
 "policy/organization-security-postures.v1.json",
 "schemas/kv-organization-security-posture.schema.json"
])
for marker in ["GOVERNMENT_HIGH_CONTROL","P1_REPLAY","P2_RECONSTRUCTION","HISTORICAL_SCOPE_REQUIRES_EXPLICIT_AUTHORIZATION","NONE_POLICY_ONLY","CLEARANCE_OR_COMPARTMENT_DENIED"]:
    if marker not in src: raise SystemExit("missing invariant "+marker)
print("organization security posture static checks: PASS")
