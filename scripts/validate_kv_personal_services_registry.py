#!/usr/bin/env python3
"""Validate the pre-Interlock KnowledgeVault personal services registry."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "specs" / "kv-personal-services-registry.v1.json"

ALLOWED_CLASSES = {"KV_NATIVE", "KV_DEVICE", "KV_DEVICE_PROVIDER"}


def validate(payload: dict) -> list[str]:
    failures: list[str] = []
    if payload.get("schema") != "stegverse.kv.personal-services-registry/v1":
        failures.append("unexpected registry schema")
    if payload.get("state") != "INSTALLED_INACTIVE":
        failures.append("registry must remain INSTALLED_INACTIVE before activation")
    if payload.get("interlock_activation_required_for_install") is not False:
        failures.append("Interlock activation must not be required for installation")
    if payload.get("authority_effect") != "NONE":
        failures.append("registry authority_effect must be NONE")
    for key in (
        "runtime_activation_claimed",
        "network_activation_claimed",
        "credential_activation_claimed",
        "provider_activation_claimed",
    ):
        if payload.get(key) is not False:
            failures.append(f"{key} must be false")

    services = payload.get("services")
    if not isinstance(services, list) or not services:
        failures.append("services must be a non-empty list")
        return failures

    if payload.get("service_count") != len(services):
        failures.append("service_count does not match services")

    seen: set[str] = set()
    for service in services:
        sid = service.get("service_id")
        if not isinstance(sid, str) or not sid:
            failures.append("service_id missing")
            continue
        if sid in seen:
            failures.append(f"duplicate service_id: {sid}")
        seen.add(sid)
        if service.get("service_class") not in ALLOWED_CLASSES:
            failures.append(f"{sid}: invalid service_class")
        if service.get("install_state") != "INSTALLED_INACTIVE":
            failures.append(f"{sid}: install_state must remain INSTALLED_INACTIVE")
        if service.get("authority_effect") != "NONE":
            failures.append(f"{sid}: authority_effect must be NONE")
        surfaces = service.get("kv_surfaces")
        if not isinstance(surfaces, list) or not surfaces:
            failures.append(f"{sid}: at least one existing KV surface is required")
        if service.get("service_class") == "KV_NATIVE" and service.get("provider_dependency") == "EXTERNAL_REQUIRED":
            failures.append(f"{sid}: KV_NATIVE may not require an external provider")

    return failures


def main() -> int:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    failures = validate(payload)
    if failures:
        print("KV_PERSONAL_SERVICES_REGISTRY_FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("KV_PERSONAL_SERVICES_REGISTRY_PASS")
    print(f"SERVICE_COUNT={len(payload['services'])}")
    print("STATE=INSTALLED_INACTIVE")
    print("AUTHORITY_EFFECT=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
