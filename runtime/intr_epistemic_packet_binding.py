"""Binding rules between InTr transport packets and epistemic-state envelopes.

The binding is hash/reference based so transport can prove which epistemic artifact it
carried without transport becoming semantic, governance, or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from runtime.intr_epistemic_state import REQUIRED_ACK_BY_CONSEQUENCE, ConsequenceClass


@dataclass(frozen=True)
class EpistemicBinding:
    epistemic_message_id: str
    epistemic_envelope_sha256: str
    consequence_class: ConsequenceClass
    required_acknowledgement_level: str
    acknowledgement_required: bool
    authority_effect: str = "NONE"


def canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def bind_epistemic_envelope(envelope: Mapping[str, Any]) -> EpistemicBinding:
    """Produce a non-authorizing InTr binding for one epistemic envelope."""
    if envelope.get("schema") != "stegverse.intr.epistemic-state/v1":
        raise ValueError("unsupported epistemic envelope schema")
    message_id = envelope.get("message_id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("epistemic message_id required")
    consequence = envelope.get("consequence_class")
    if consequence not in REQUIRED_ACK_BY_CONSEQUENCE:
        raise ValueError("valid consequence_class required")
    required_level = REQUIRED_ACK_BY_CONSEQUENCE[consequence]
    declared_level = envelope.get("required_acknowledgement_level", required_level)
    if declared_level != required_level:
        raise ValueError("required acknowledgement level must match consequence class")
    required = bool(envelope.get("requires_acknowledgement"))
    if consequence != "INFORMATIONAL" and not required:
        raise ValueError("state-relevant or consequential communication requires acknowledgement")
    return EpistemicBinding(
        epistemic_message_id=message_id,
        epistemic_envelope_sha256=canonical_sha256(envelope),
        consequence_class=consequence,
        required_acknowledgement_level=required_level,
        acknowledgement_required=required,
    )


def require_epistemic_binding(*, consequence_class: ConsequenceClass, binding: EpistemicBinding | None) -> None:
    """Fail closed when state-relevant InTr communication lacks epistemic binding."""
    if consequence_class != "INFORMATIONAL" and binding is None:
        raise ValueError("state-relevant InTr communication requires epistemic-state binding")
    if binding is not None and binding.consequence_class != consequence_class:
        raise ValueError("transport consequence class does not match epistemic binding")
