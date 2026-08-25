"""Transient owner-authorized credential ingress into SKAP.

This API intentionally accepts only an already-in-memory mutable bytearray supplied by
a trusted interactive edge. It has no argv/env/file/network credential-loading path.
The caller must establish owner authorization before invoking ingress. The plaintext
buffer is sealed immediately through the TVC key-provider boundary, then overwritten
on a best-effort basis. The returned receipt is deliberately secret-free.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .crypto_boundary import KeyProvider, SealedMaterial, seal_with_provider

INGRESS_RECEIPT_SCHEMA = "stegverse.skap.owner_credential_ingress_receipt/v1"


class SKAPIngressError(ValueError):
    pass


def ingest_owner_credential(
    plaintext: bytearray,
    *,
    owner_authorized: bool,
    authorization_ref: str,
    key_provider: KeyProvider,
    object_id: str,
    credential_version: int,
    wrapping_policy_ref: str,
    purpose: str,
    endpoint_ref: str,
    source_class: str = "TRUSTED_INTERACTIVE_EDGE",
    observed_at: str | None = None,
) -> tuple[SealedMaterial, dict[str, Any]]:
    """Seal owner-supplied plaintext and return only sealed material + receipt.

    The input must be a mutable ``bytearray`` so this boundary can wipe the caller's
    provided buffer in-place. Immutable ``bytes``/``str`` inputs are rejected because
    they cannot be reliably overwritten by this function.
    """
    if owner_authorized is not True:
        raise SKAPIngressError("owner authorization is required before credential ingress")
    if not authorization_ref:
        raise SKAPIngressError("owner authorization reference is required")
    if source_class != "TRUSTED_INTERACTIVE_EDGE":
        raise SKAPIngressError("credential ingress source must be TRUSTED_INTERACTIVE_EDGE")
    if not isinstance(plaintext, bytearray):
        raise SKAPIngressError("credential ingress requires a mutable bytearray")
    if not plaintext:
        raise SKAPIngressError("credential ingress plaintext must not be empty")

    original_length = len(plaintext)
    try:
        sealed = seal_with_provider(
            plaintext,
            key_provider=key_provider,
            object_id=object_id,
            credential_version=credential_version,
            wrapping_policy_ref=wrapping_policy_ref,
            purpose=purpose,
            endpoint_ref=endpoint_ref,
        )
    finally:
        for index in range(len(plaintext)):
            plaintext[index] = 0

    timestamp = observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = {
        "schema": INGRESS_RECEIPT_SCHEMA,
        "object_id": object_id,
        "credential_version": credential_version,
        "purpose": purpose,
        "endpoint_ref": endpoint_ref,
        "wrapping_policy_ref": wrapping_policy_ref,
        "authorization_ref": authorization_ref,
        "source_class": source_class,
        "key_authority_ref": key_provider.authority_ref,
        "sealed_material_hash": sealed.sealed_material_hash,
        "plaintext_length": original_length,
        "owner_authorized": True,
        "plaintext_persisted": False,
        "device_durable_secret_custody": False,
        "kv_decryption_authority": False,
        "model_secret_access": False,
        "authority_transfer": False,
        "ingressed_at": timestamp,
    }
    return sealed, receipt
