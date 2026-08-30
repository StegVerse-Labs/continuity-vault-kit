#!/usr/bin/env python3
"""Validate the KnowledgeVault typed transport capability registry."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "specs" / "kv-transport-capability-registry.v1.json"

REQUIRED_TYPES = {
    "KV_DISTRIBUTION_DOWNLOAD",
    "DEVICE_KV_INTR",
    "PUBLIC_HTTPS_INGRESS",
    "ADJACENT_EXTERNAL_API_EGRESS",
    "NODE_TO_NODE_SYNC",
    "KV_SKAP_INTR",
    "TVC_RELAY",
}
ALLOWED_DIRECTIONS = {"INGRESS", "EGRESS", "BIDIRECTIONAL"}


def validate(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "stegverse.kv.transport-capability-registry/v1":
        failures.append("unexpected registry schema")
    if payload.get("state") != "DEFINED_INACTIVE":
        failures.append("registry must remain DEFINED_INACTIVE")
    if payload.get("device_role") != "EPHEMERAL_ACTIVITY_EDGE":
        failures.append("device role drift")
    if payload.get("kv_role") != "DURABLE_STATE_CONTINUITY_AND_RECONSTRUCTION":
        failures.append("KV role drift")
    if payload.get("credential_authority") != "TV/TVC":
        failures.append("credential authority must remain TV/TVC")
    if payload.get("authority_effect") != "NONE":
        failures.append("registry authority_effect must be NONE")
    if payload.get("runtime_activation_claimed") is not False:
        failures.append("source registry may not claim runtime activation")

    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        failures.append("capabilities must be a non-empty list")
        return failures

    seen: set[str] = set()
    for cap in capabilities:
        ctype = cap.get("capability_type")
        if not isinstance(ctype, str) or not ctype:
            failures.append("capability_type missing")
            continue
        if ctype in seen:
            failures.append(f"duplicate capability_type: {ctype}")
        seen.add(ctype)

        if cap.get("capability_state") != "DEFINED_UNOBSERVED":
            failures.append(f"{ctype}: capability_state must remain DEFINED_UNOBSERVED")
        if cap.get("direction") not in ALLOWED_DIRECTIONS:
            failures.append(f"{ctype}: invalid direction")
        carriers = cap.get("carrier_profiles")
        if not isinstance(carriers, list) or not carriers:
            failures.append(f"{ctype}: carrier_profiles required")

        binding = cap.get("binding_requirements")
        if not isinstance(binding, dict):
            failures.append(f"{ctype}: binding_requirements required")
        else:
            if binding.get("device_node_continuity_required") is not True:
                failures.append(f"{ctype}: device node continuity must be required")
            if binding.get("kv_continuity_binding_required") is not True:
                failures.append(f"{ctype}: KV continuity binding must be required")

        boundaries = cap.get("required_boundaries")
        if not isinstance(boundaries, list) or not boundaries:
            failures.append(f"{ctype}: required_boundaries required")

        receipts = cap.get("receipt_requirements")
        if not isinstance(receipts, dict):
            failures.append(f"{ctype}: receipt_requirements required")
        else:
            for key in (
                "capability_establishment_receipt_required",
                "adjacent_boundary_receipts_required",
                "reconstruction_evidence_required",
            ):
                if receipts.get(key) is not True:
                    failures.append(f"{ctype}: {key} must be true")

        reuse = cap.get("reuse_policy")
        if not isinstance(reuse, dict):
            failures.append(f"{ctype}: reuse_policy required")
        else:
            for key in (
                "reuse_allowed_when_valid",
                "revoked_fails_closed",
                "expired_fails_closed",
                "superseded_fails_closed",
            ):
                if reuse.get(key) is not True:
                    failures.append(f"{ctype}: {key} must be true")

        if cap.get("authority_effect") != "NONE":
            failures.append(f"{ctype}: authority_effect must be NONE")
        if cap.get("runtime_observed") is not False:
            failures.append(f"{ctype}: source registry may not claim runtime observation")

    missing = REQUIRED_TYPES - seen
    extra = seen - REQUIRED_TYPES
    if missing:
        failures.append("missing capability types: " + ",".join(sorted(missing)))
    if extra:
        failures.append("unexpected capability types: " + ",".join(sorted(extra)))

    by_type = {cap["capability_type"]: cap for cap in capabilities if isinstance(cap, dict) and cap.get("capability_type")}
    hil = by_type.get("PUBLIC_HTTPS_INGRESS")
    if hil and "HTTPS" not in hil.get("carrier_profiles", []):
        failures.append("PUBLIC_HTTPS_INGRESS must include HTTPS carrier profile")
    hf = by_type.get("ADJACENT_EXTERNAL_API_EGRESS")
    if hf and hf.get("direction") != "EGRESS":
        failures.append("ADJACENT_EXTERNAL_API_EGRESS must be EGRESS")

    return failures


def main() -> int:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    failures = validate(payload)
    if failures:
        print("KV_TRANSPORT_CAPABILITY_REGISTRY_FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("KV_TRANSPORT_CAPABILITY_REGISTRY_PASS")
    print(f"CAPABILITY_COUNT={len(payload['capabilities'])}")
    print("STATE=DEFINED_INACTIVE")
    print("AUTHORITY_EFFECT=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
