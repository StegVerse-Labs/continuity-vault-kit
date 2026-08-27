#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "specs" / "kv-provider-surface-capability-registry.v1.json"

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
REGISTRY_STATES = {"INSTALLED_UNVERIFIED","DOCUMENTED_UNVERIFIED","PARTIALLY_VERIFIED","VERIFIED"}
SOURCE_TYPES = {"provider_documentation","stegverse_observation","conformance_test","unknown"}

def fail(msg):
    print(f"KV_PROVIDER_SURFACE_CAPABILITY_REGISTRY=FAIL: {msg}")
    raise SystemExit(1)

def main():
    registry = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REGISTRY
    data = json.loads(registry.read_text())
    if data.get("schema") != "stegverse.kv.provider-surface-capability-registry/v1":
        fail("schema")
    if data.get("authority_effect") != "NONE":
        fail("authority_effect")
    if data.get("state") not in REGISTRY_STATES:
        fail("state")
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
        if ev.get("source_type") not in SOURCE_TYPES:
            fail(f"observation[{i}].source_type")
        if obs["knowledge_state"] == "DOCUMENTED":
            if ev.get("source_type") != "provider_documentation" or not ev.get("source_ref") or not ev.get("observed_at"):
                fail(f"observation[{i}].documented_without_provider_evidence")
        if obs["knowledge_state"] == "OBSERVED":
            if ev.get("source_type") not in {"stegverse_observation","conformance_test"} or not ev.get("source_ref") or not ev.get("observed_at"):
                fail(f"observation[{i}].observed_without_stegverse_evidence")
        if obs["knowledge_state"] == "VERIFIED":
            if ev.get("source_type") in (None, "unknown") or not ev.get("source_ref") or not ev.get("observed_at"):
                fail(f"observation[{i}].verified_without_evidence")
    verified_count = sum(1 for obs in observations if obs.get("knowledge_state") == "VERIFIED")
    state = data.get("state")
    if state == "INSTALLED_UNVERIFIED" and observations:
        fail("installed_unverified_with_observations")
    if state == "DOCUMENTED_UNVERIFIED" and verified_count:
        fail("documented_unverified_contains_verified_observation")
    if state == "PARTIALLY_VERIFIED" and verified_count == 0:
        fail("partially_verified_without_verified_observation")
    if state == "VERIFIED" and (not observations or verified_count != len(observations)):
        fail("verified_registry_contains_nonverified_observation")
    print("KV_PROVIDER_SURFACE_CAPABILITY_REGISTRY=PASS")

if __name__ == "__main__":
    main()
