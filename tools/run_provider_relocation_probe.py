#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"runtime"))
from provider_relocation import evaluate  # noqa: E402

request={
 "schema":"stegverse.kv.provider-relocation-request/v1",
 "relocation_id":"probe-icloud-google-drive",
 "kv_id":"kv-probe",
 "source_provider":"iCloud",
 "destination_provider":"Google Drive",
 "source_continuity_root":"a"*64,
 "destination_continuity_root":"a"*64,
 "kv_identity_preserved":True,
 "continuity_transition":"PRESERVED",
 "transport":{"protocol":"InTr","interlock_verified":True,"intr_bound":True},
 "authority":{"source_provider_is_kv_authority":False,"destination_provider_is_kv_authority":False,"credential_authority":"TV/TVC"}
}
print(json.dumps(evaluate(request),indent=2,sort_keys=True))
