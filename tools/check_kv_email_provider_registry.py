#!/usr/bin/env python3
"""Validate the documented KnowledgeVault email-provider adapter registry."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "specs" / "kv-email-provider-registry.v1.json"


def load_registry(path: Path = REGISTRY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "stegverse.kv.email-provider-registry/v1":
        errors.append("registry schema mismatch")
    if data.get("state") != "DOCUMENTED_UNVERIFIED":
        errors.append("initial provider registry must remain DOCUMENTED_UNVERIFIED")
    if data.get("authority_effect") != "NONE":
        errors.append("provider registry must not grant authority")

    seen_domains: set[str] = set()
    providers = data.get("providers")
    if not isinstance(providers, list) or not providers:
        errors.append("at least one provider required")
        return errors

    for provider in providers:
        provider_id = provider.get("provider_id", "<missing>")
        domains = provider.get("domains", [])
        if not isinstance(domains, list) or not domains:
            errors.append(f"{provider_id}: domains required")
            continue
        overlap = seen_domains.intersection(domains)
        if overlap:
            errors.append(f"{provider_id}: ambiguous domains {sorted(overlap)}")
        seen_domains.update(domains)

        if provider.get("credential_destination") != "SKAP_VAULT":
            errors.append(f"{provider_id}: credential destination must be SKAP_VAULT")
        if provider.get("kv_secret_storage") is not False:
            errors.append(f"{provider_id}: KV secret storage must be false")

        authorization = provider.get("authorization", {})
        if authorization.get("user_authorization_required") is not True:
            errors.append(f"{provider_id}: explicit user authorization required")
        if authorization.get("mode") not in {"OAUTH2_DELEGATED", "APP_SPECIFIC_PASSWORD"}:
            errors.append(f"{provider_id}: unsupported authorization mode")

        permission = provider.get("minimum_read_permission")
        if not isinstance(permission, str) or not permission:
            errors.append(f"{provider_id}: minimum read permission required")

        evidence = provider.get("evidence", {})
        refs = evidence.get("source_refs")
        if evidence.get("state") != "DOCUMENTED":
            errors.append(f"{provider_id}: evidence state must be DOCUMENTED")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(ref, str) and ref.startswith("https://") for ref in refs
        ):
            errors.append(f"{provider_id}: authoritative HTTPS evidence refs required")
        if not isinstance(evidence.get("observed_on"), str) or not evidence["observed_on"]:
            errors.append(f"{provider_id}: evidence observation date required")

    return errors


def main() -> int:
    errors = validate(load_registry())
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: documented KV email-provider registry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
