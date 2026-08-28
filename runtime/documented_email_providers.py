"""Load documented email-provider metadata into the provider-neutral adapter registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from runtime.email_continuity import EmailAccountMapping, EmailMappingError
from runtime.email_provider_adapter import ProviderRegistry

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "specs" / "kv-email-provider-registry.v1.json"


@dataclass(frozen=True)
class DocumentedProviderAdapter:
    provider_id: str
    provider_route: str
    domains: frozenset[str]
    auth_mode: str
    minimum_read_permission: str
    evidence_state: str
    evidence_refs: tuple[str, ...]

    def matches_domain(self, domain: str) -> bool:
        return domain.lower() in self.domains

    def session_descriptor(self, mapping: EmailAccountMapping) -> dict:
        if mapping.provider_id != self.provider_id or mapping.provider_route != self.provider_route:
            raise EmailMappingError("provider mapping does not match documented adapter")
        return {
            "provider_id": self.provider_id,
            "provider_route": self.provider_route,
            "authorization_mode": self.auth_mode,
            "minimum_read_permission": self.minimum_read_permission,
            "skap_credential_ref_required": True,
            "evidence_state": self.evidence_state,
            "evidence_refs": list(self.evidence_refs),
            "runtime_verified": False,
            "authority_effect": "NONE",
        }


def load_documented_provider_registry(path: Path = DEFAULT_REGISTRY) -> ProviderRegistry:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != "stegverse.kv.email-provider-registry/v1":
        raise EmailMappingError("email provider registry schema mismatch")
    if data.get("state") != "DOCUMENTED_UNVERIFIED":
        raise EmailMappingError("documented provider loader requires DOCUMENTED_UNVERIFIED state")
    if data.get("authority_effect") != "NONE":
        raise EmailMappingError("provider registry may not grant authority")

    adapters: list[DocumentedProviderAdapter] = []
    seen_domains: set[str] = set()
    for provider in data.get("providers", []):
        domains = {str(value).lower() for value in provider.get("domains", [])}
        if not domains or seen_domains.intersection(domains):
            raise EmailMappingError("provider domains missing or ambiguous")
        seen_domains.update(domains)

        if provider.get("credential_destination") != "SKAP_VAULT":
            raise EmailMappingError("provider credentials must terminate in SKAP Vault")
        if provider.get("kv_secret_storage") is not False:
            raise EmailMappingError("provider registry may not permit KV secret storage")

        evidence = provider.get("evidence", {})
        if evidence.get("state") != "DOCUMENTED" or not evidence.get("source_refs"):
            raise EmailMappingError("documented provider requires source evidence")

        transport = provider.get("transport", {})
        authorization = provider.get("authorization", {})
        if authorization.get("user_authorization_required") is not True:
            raise EmailMappingError("provider access must require user authorization")

        adapters.append(
            DocumentedProviderAdapter(
                provider_id=provider["provider_id"],
                provider_route=transport["route"],
                domains=frozenset(domains),
                auth_mode=authorization["mode"],
                minimum_read_permission=provider["minimum_read_permission"],
                evidence_state="DOCUMENTED_UNVERIFIED",
                evidence_refs=tuple(evidence["source_refs"]),
            )
        )

    if not adapters:
        raise EmailMappingError("provider registry contains no adapters")
    return ProviderRegistry(adapters)
