"""Provider-neutral KnowledgeVault email mapping and SKAP credential binding.

This module does not authenticate to any mail provider and does not read mail.
It creates deterministic mailbox mappings, requires a SKAP Vault credential
reference before session verification, and never accepts raw credential material.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from email.utils import parseaddr


class EmailMappingError(ValueError):
    pass


def _normalize_email(value: str) -> str:
    _, address = parseaddr(value)
    address = address.strip().lower()
    if not address or "@" not in address or address.startswith("@") or address.endswith("@"):
        raise EmailMappingError("valid email address required")
    local, domain = address.rsplit("@", 1)
    if not local or "." not in domain:
        raise EmailMappingError("valid routable email address required")
    return address


def mapping_id_for(email_address: str) -> str:
    normalized = _normalize_email(email_address)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"kv-email:{digest}"


@dataclass(frozen=True)
class EmailAccountMapping:
    schema: str
    mapping_id: str
    email_address: str
    provider_id: str
    provider_route: str
    mapping_state: str
    skap_credential_ref: str | None
    credential_secret_present_in_kv: bool
    authority_effect: str

    def to_dict(self) -> dict:
        return asdict(self)


def create_mapping(*, email_address: str, provider_id: str, provider_route: str) -> EmailAccountMapping:
    normalized = _normalize_email(email_address)
    if not provider_id.strip() or not provider_route.strip():
        raise EmailMappingError("provider_id and provider_route are required")
    return EmailAccountMapping(
        schema="stegverse.kv.email-account-mapping/v1",
        mapping_id=mapping_id_for(normalized),
        email_address=normalized,
        provider_id=provider_id.strip(),
        provider_route=provider_route.strip(),
        mapping_state="MAPPED_CREDENTIAL_REQUIRED",
        skap_credential_ref=None,
        credential_secret_present_in_kv=False,
        authority_effect="NONE",
    )


def bind_skap_credential(mapping: EmailAccountMapping, *, skap_credential_ref: str) -> EmailAccountMapping:
    if mapping.mapping_state not in {"MAPPED_CREDENTIAL_REQUIRED", "CREDENTIAL_BOUND"}:
        raise EmailMappingError("SKAP credential binding is not allowed in current mapping state")
    ref = skap_credential_ref.strip()
    if not ref.startswith("skap://"):
        raise EmailMappingError("credential reference must use skap://")
    return EmailAccountMapping(
        **{
            **mapping.to_dict(),
            "mapping_state": "CREDENTIAL_BOUND",
            "skap_credential_ref": ref,
            "credential_secret_present_in_kv": False,
        }
    )


def mark_session_verified(mapping: EmailAccountMapping) -> EmailAccountMapping:
    if mapping.mapping_state != "CREDENTIAL_BOUND" or not mapping.skap_credential_ref:
        raise EmailMappingError("verified provider session requires bound SKAP credential reference")
    return EmailAccountMapping(**{**mapping.to_dict(), "mapping_state": "SESSION_VERIFIED"})


def revoke_mapping(mapping: EmailAccountMapping) -> EmailAccountMapping:
    return EmailAccountMapping(**{**mapping.to_dict(), "mapping_state": "REVOKED"})


def assert_no_secret_fields(payload: dict) -> None:
    forbidden = {"password", "secret", "token", "access_token", "refresh_token", "app_password"}
    present = forbidden.intersection({str(k).lower() for k in payload})
    if present:
        raise EmailMappingError(f"raw credential material prohibited in KV mapping: {sorted(present)}")
