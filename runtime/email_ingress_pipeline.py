"""Deterministic pre-admission email staging and governed projection.

No provider access occurs here. Callers supply already-retrieved message material and
classification signals. Staged content remains untrusted until an ADMIT decision.
Receipts contain hashes/metadata only and never persist the message payload.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Iterable

DECISIONS = {"ADMIT", "QUARANTINE", "REVIEW", "REJECT", "FAIL_CLOSED"}


class EmailIngressError(ValueError):
    pass


def _sha256_uri(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class StagedEmail:
    mapping_id: str
    canonical_message_id: str
    provider_message_id: str
    from_address: str
    subject: str
    payload: str
    staged_content_hash: str
    trust_state: str

    def metadata(self) -> dict:
        data = asdict(self)
        data.pop("payload")
        return data


@dataclass(frozen=True)
class EmailIngressReceipt:
    schema: str
    receipt_id: str
    mapping_id: str
    canonical_message_id: str
    staged_content_hash: str
    decision: str
    reason: str
    trusted_projection_created: bool
    payload_retained_in_receipt: bool
    authority_effect: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TrustedEmailProjection:
    mapping_id: str
    canonical_message_id: str
    from_address: str
    subject: str
    payload: str
    source_content_hash: str
    trust_state: str


def canonical_message_id(*, mapping_id: str, provider_message_id: str) -> str:
    if not mapping_id.startswith("kv-email:"):
        raise EmailIngressError("valid KV email mapping_id required")
    provider_message_id = provider_message_id.strip()
    if not provider_message_id:
        raise EmailIngressError("provider_message_id required")
    material = {
        "mapping_id": mapping_id,
        "provider_message_id": provider_message_id,
    }
    return "kv-email-message:" + hashlib.sha256(_canonical_bytes(material)).hexdigest()


def stage_message(
    *,
    mapping_id: str,
    provider_message_id: str,
    from_address: str,
    subject: str,
    payload: str,
) -> StagedEmail:
    if not from_address.strip():
        raise EmailIngressError("from_address required")
    if not isinstance(payload, str):
        raise EmailIngressError("payload must be text for canonical staging")
    message_id = canonical_message_id(
        mapping_id=mapping_id,
        provider_message_id=provider_message_id,
    )
    hash_material = {
        "mapping_id": mapping_id,
        "canonical_message_id": message_id,
        "from_address": from_address.strip().lower(),
        "subject": subject.strip(),
        "payload": payload,
    }
    return StagedEmail(
        mapping_id=mapping_id,
        canonical_message_id=message_id,
        provider_message_id=provider_message_id.strip(),
        from_address=from_address.strip().lower(),
        subject=subject.strip(),
        payload=payload,
        staged_content_hash=_sha256_uri(_canonical_bytes(hash_material)),
        trust_state="STAGED_UNTRUSTED",
    )


def decide(
    staged: StagedEmail,
    *,
    signals: Iterable[str],
    governance_available: bool = True,
) -> tuple[EmailIngressReceipt, TrustedEmailProjection | None]:
    normalized = {str(signal).strip().lower() for signal in signals if str(signal).strip()}

    if not governance_available:
        decision, reason = "FAIL_CLOSED", "governance_unavailable_or_ambiguous"
    elif "spam_or_bulk_abuse" in normalized or "user_denylist" in normalized:
        decision, reason = "REJECT", "active_rejection_rule"
    elif "phishing" in normalized or "malware" in normalized or "dangerous_attachment" in normalized:
        decision, reason = "QUARANTINE", "security_quarantine_rule"
    elif "user_review_required" in normalized or "restricted_content" in normalized:
        decision, reason = "REVIEW", "user_or_policy_review_rule"
    else:
        decision, reason = "ADMIT", "passes_active_ingress_governance"

    projection = None
    if decision == "ADMIT":
        projection = TrustedEmailProjection(
            mapping_id=staged.mapping_id,
            canonical_message_id=staged.canonical_message_id,
            from_address=staged.from_address,
            subject=staged.subject,
            payload=staged.payload,
            source_content_hash=staged.staged_content_hash,
            trust_state="TRUSTED_ADMITTED",
        )

    receipt_material = {
        "mapping_id": staged.mapping_id,
        "canonical_message_id": staged.canonical_message_id,
        "staged_content_hash": staged.staged_content_hash,
        "decision": decision,
        "reason": reason,
    }
    receipt = EmailIngressReceipt(
        schema="stegverse.kv.email-ingress-receipt/v1",
        receipt_id="kv-email-receipt:" + hashlib.sha256(_canonical_bytes(receipt_material)).hexdigest(),
        mapping_id=staged.mapping_id,
        canonical_message_id=staged.canonical_message_id,
        staged_content_hash=staged.staged_content_hash,
        decision=decision,
        reason=reason,
        trusted_projection_created=projection is not None,
        payload_retained_in_receipt=False,
        authority_effect="NONE",
    )
    return receipt, projection


def reconcile_duplicate(
    *,
    staged: StagedEmail,
    prior_receipt: EmailIngressReceipt,
) -> str:
    if prior_receipt.canonical_message_id != staged.canonical_message_id:
        return "NEW_MESSAGE"
    if prior_receipt.staged_content_hash != staged.staged_content_hash:
        raise EmailIngressError("canonical message id collision with content drift")
    return "ALREADY_EVALUATED"
