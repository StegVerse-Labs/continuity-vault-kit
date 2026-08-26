#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "specs" / "kv-provider-surface-capability-registry.v1.json"

PROVIDERS = {
    "icloud","google_drive","microsoft_onedrive","aws_object_storage",
    "self_hosted_private_cloud","stegcloud"
}
CAPABILITIES = {
    "read","write","background_sync","offline_access","local_cache","atomic_update",
    "conflict_handling","folder_creation","metadata_fidelity","change_notifications",
    "direct_api","native_file_provider","authentication_persistence","resumable_upload",
    "file_size_limits","latency_performance","recovery_export"
}
CAPABILITY_VALUES = {"YES","NO","PARTIAL","UNKNOWN","NOT_APPLICABLE"}
KNOWLEDGE_STATES = {"UNKNOWN","DOCUMENTED","OBSERVED","VERIFIED","CONTRADICTED"}

def fail(msg):
    print(f"KV_PROVIDER_SURFACE_CAPABILITY_REGISTRY=FAIL: {msg}")
    raise SystemExit(1)

def main():
    data = json.loads(REGISTRY.read_text())
    if data.get("schema") != "stegverse.kv.provider-surface-capability-registry/v1":
        fail("schema")
    if data.get("authority_effect") != "NONE":
        fail("authority_effect")
    if set(data.get("provider_families", [])) != PROVIDERS:
        fail("provider_families")
    observations = data.get("observations")
    if not isinstance(observations, list):
        fail("observations")
    for i, obs in enumerate(observations):
        for key in ("provider","device_class","platform","access_surface","knowledge_state","capabilities","preferred_route","fallback_route","evidence"):
            if key not in obs:
                fail(f"observation[{i}].{key}")
        if obs["knowledge_state"] not in KNOWLEDGE_STATES:
            fail(f"observation[{i}].knowledge_state")
        caps = obs["capabilities"]
        if set(caps) != CAPABILITIES:
            fail(f"observation[{i}].capabilities")
        if any(v not in CAPABILITY_VALUES for v in caps.values()):
            fail(f"observation[{i}].capability_value")
        ev = obs["evidence"]
        if not isinstance(ev, dict) or not ev.get("version"):
            fail(f"observation[{i}].evidence")
        if obs["knowledge_state"] == "VERIFIED":
            if ev.get("source_type") in (None, "unknown") or not ev.get("source_ref") or not ev.get("observed_at"):
                fail(f"observation[{i}].verified_without_evidence")
    print("KV_PROVIDER_SURFACE_CAPABILITY_REGISTRY=PASS")

if __name__ == "__main__":
    main()
