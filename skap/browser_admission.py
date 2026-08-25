"""Canonical browser-sealed -> SKAP-sealed admission bridge.

This module composes the existing browser ECDH recipient boundary with the existing
canonical SKAP root-key provider boundary. It deliberately does not provision either
key. The browser recipient private key and canonical SKAP root key remain provider-
owned and callback-scoped.

The only plaintext transition is inside nested callbacks:

    browser ciphertext
    -> resolve_at_skap(...)
    -> mutable callback-local copy
    -> seal_with_provider(...)
    -> canonical SKAP ciphertext

The temporary mutable copy is overwritten before this function returns. Neither key
nor plaintext is returned, serialized, persisted, or granted authority by this bridge.
"""
from __future__ import annotations

from typing import Any, Callable, Protocol, TypeVar

from cryptography.hazmat.primitives.asymmetric import ec

from skap.browser_ingress import resolve_at_skap
from skap.crypto_boundary import KeyProvider, seal_with_provider

T = TypeVar("T")


class BrowserRecipientKeyProvider(Protocol):
    @property
    def key_id(self) -> str: ...

    def with_private_key(self, consumer: Callable[[ec.EllipticCurvePrivateKey], T]) -> T: ...


class BrowserAdmissionError(ValueError):
    pass


def admit_browser_envelope(
    browser_envelope: dict[str, Any],
    *,
    recipient_key_provider: BrowserRecipientKeyProvider,
    canonical_key_provider: KeyProvider,
    object_id: str,
    credential_version: int,
    browser_wrapping_policy_ref: str,
    canonical_wrapping_policy_ref: str,
    purpose: str,
    endpoint_ref: str,
) -> dict[str, Any]:
    """Convert one authenticated browser envelope into canonical SKAP ciphertext."""
    if endpoint_ref != "https://api.coinbase.com":
        raise BrowserAdmissionError("canonical browser admission endpoint must be exact Coinbase origin")
    if not recipient_key_provider.key_id.startswith("tvc://skap/browser-ingress/coinbase/"):
        raise BrowserAdmissionError("browser recipient key authority invalid")

    canonical: dict[str, Any] = {}

    def consume_recipient_private_key(recipient_private_key: ec.EllipticCurvePrivateKey) -> None:
        if not isinstance(recipient_private_key, ec.EllipticCurvePrivateKey):
            raise BrowserAdmissionError("browser recipient private key provider returned invalid key")
        if not isinstance(recipient_private_key.curve, ec.SECP256R1):
            raise BrowserAdmissionError("browser recipient private key must use P-256")

        def consume_plaintext(view: memoryview) -> None:
            temporary = bytearray(view)
            try:
                sealed = seal_with_provider(
                    temporary,
                    key_provider=canonical_key_provider,
                    object_id=object_id,
                    credential_version=credential_version,
                    wrapping_policy_ref=canonical_wrapping_policy_ref,
                    purpose=purpose,
                    endpoint_ref=endpoint_ref,
                )
                canonical.update(sealed.envelope)
            finally:
                for index in range(len(temporary)):
                    temporary[index] = 0

        resolve_at_skap(
            browser_envelope,
            recipient_private_key=recipient_private_key,
            expected_recipient_key_id=recipient_key_provider.key_id,
            expected_object_id=object_id,
            expected_credential_version=credential_version,
            expected_wrapping_policy_ref=browser_wrapping_policy_ref,
            expected_purpose=purpose,
            expected_endpoint_ref=endpoint_ref,
            consumer=consume_plaintext,
        )

    recipient_key_provider.with_private_key(consume_recipient_private_key)

    if not canonical:
        raise BrowserAdmissionError("canonical SKAP admission did not produce sealed material")
    if canonical.get("object_id") != object_id:
        raise BrowserAdmissionError("canonical SKAP object binding mismatch")
    if canonical.get("credential_version") != credential_version:
        raise BrowserAdmissionError("canonical SKAP version binding mismatch")
    if canonical.get("purpose") != purpose or canonical.get("endpoint_ref") != endpoint_ref:
        raise BrowserAdmissionError("canonical SKAP endpoint/purpose binding mismatch")
    if canonical.get("plaintext_persisted") is not False:
        raise BrowserAdmissionError("canonical SKAP plaintext persistence forbidden")
    if canonical.get("key_material_persisted") is not False:
        raise BrowserAdmissionError("canonical SKAP key persistence forbidden")
    if canonical.get("authority_transfer") is not False:
        raise BrowserAdmissionError("canonical SKAP authority transfer forbidden")
    return canonical
