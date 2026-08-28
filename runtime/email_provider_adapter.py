"""Provider discovery/session interface for KnowledgeVault email continuity.

Concrete provider adapters implement this contract outside ordinary KV secret state.
Discovery may identify a provider route, but authentication/session verification
must remain separate and requires a bound SKAP credential reference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from runtime.email_continuity import EmailAccountMapping, EmailMappingError, create_mapping


class EmailProviderAdapter(Protocol):
    provider_id: str
    provider_route: str

    def matches_domain(self, domain: str) -> bool: ...

    def session_descriptor(self, mapping: EmailAccountMapping) -> dict: ...


@dataclass
class ProviderRegistry:
    adapters: list[EmailProviderAdapter]

    def discover(self, email_address: str) -> EmailAccountMapping:
        if "@" not in email_address:
            raise EmailMappingError("valid email address required")
        domain = email_address.rsplit("@", 1)[1].strip().lower()
        matches = [adapter for adapter in self.adapters if adapter.matches_domain(domain)]
        if len(matches) != 1:
            raise EmailMappingError("provider discovery must resolve exactly one supported route")
        adapter = matches[0]
        return create_mapping(
            email_address=email_address,
            provider_id=adapter.provider_id,
            provider_route=adapter.provider_route,
        )

    def descriptor_for(self, mapping: EmailAccountMapping) -> dict:
        matches = [
            adapter for adapter in self.adapters
            if adapter.provider_id == mapping.provider_id
            and adapter.provider_route == mapping.provider_route
        ]
        if len(matches) != 1:
            raise EmailMappingError("mapped provider adapter unavailable or ambiguous")
        descriptor = matches[0].session_descriptor(mapping)
        if not isinstance(descriptor, dict):
            raise EmailMappingError("provider session descriptor must be an object")
        forbidden = {"password", "secret", "token", "access_token", "refresh_token", "app_password"}
        if forbidden.intersection({str(key).lower() for key in descriptor}):
            raise EmailMappingError("provider session descriptor may not contain raw credential material")
        return descriptor
