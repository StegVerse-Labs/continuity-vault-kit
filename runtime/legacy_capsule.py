"""Fail-closed helpers for private KnowledgeVault legacy capsules."""

from __future__ import annotations

import copy
import re
from typing import Any, Dict, Iterable, Set

CAPSULE_SCHEMA = "stegverse.kv.legacy_capsule/v1"
DISCLOSURE_STAGES = (
    "UNKNOWN",
    "INVITED",
    "PARTICIPATING",
    "QUALIFIED",
    "CAPSULE_EXISTS",
    "ORIGINATOR_IDENTITY",
    "ASSET_CLASS",
    "TERMS",
    "FULL_PAYLOAD",
)

FORBIDDEN_FIELD_FRAGMENTS = (
    "plaintext",
    "payload_text",
    "private_key",
    "password",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "recovery_code",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class LegacyCapsuleError(ValueError):
    pass


def _reject_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN_FIELD_FRAGMENTS):
                raise LegacyCapsuleError(f"prohibited field at {path}.{key}")
            _reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def assert_capsule(capsule: Dict[str, Any]) -> None:
    if not isinstance(capsule, dict):
        raise LegacyCapsuleError("capsule must be an object")
    _reject_forbidden_fields(capsule)
    if capsule.get("schema") != CAPSULE_SCHEMA:
        raise LegacyCapsuleError("capsule schema mismatch")
    if not str(capsule.get("capsule_id", "")).strip():
        raise LegacyCapsuleError("capsule_id required")
    payload = capsule.get("payload")
    if not isinstance(payload, dict):
        raise LegacyCapsuleError("sealed payload descriptor required")
    if not str(payload.get("sealed_ref", "")).strip():
        raise LegacyCapsuleError("sealed payload reference required")
    digest = payload.get("sha256")
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        raise LegacyCapsuleError("payload sha256 required")
    if not str(capsule.get("recipient_policy_ref", "")).strip():
        raise LegacyCapsuleError("recipient policy reference required")
    if not str(capsule.get("release_policy_ref", "")).strip():
        raise LegacyCapsuleError("release policy reference required")
    disclosure = capsule.get("disclosure")
    if not isinstance(disclosure, dict):
        raise LegacyCapsuleError("disclosure policy required")
    if disclosure.get("qualified_reveal_stage") not in DISCLOSURE_STAGES[4:]:
        raise LegacyCapsuleError("invalid qualified reveal stage")
    if capsule.get("armed") not in (True, False):
        raise LegacyCapsuleError("armed must be boolean")


def build_capsule(
    *,
    capsule_id: str,
    subject_ref: str,
    payload_class: str,
    sealed_ref: str,
    payload_sha256: str,
    recipient_policy_ref: str,
    release_policy_ref: str,
    participation_gate_ref: str | None = None,
    qualified_reveal_stage: str = "CAPSULE_EXISTS",
    invite_reveals_originator: bool = False,
    alternate_disposition_ref: str | None = None,
) -> Dict[str, Any]:
    capsule = {
        "schema": CAPSULE_SCHEMA,
        "capsule_id": capsule_id,
        "subject_ref": subject_ref,
        "payload": {
            "class": payload_class,
            "sealed_ref": sealed_ref,
            "sha256": payload_sha256,
        },
        "recipient_policy_ref": recipient_policy_ref,
        "release_policy_ref": release_policy_ref,
        "participation_gate_ref": participation_gate_ref,
        "disclosure": {
            "invite_reveals_originator": bool(invite_reveals_originator),
            "qualified_reveal_stage": qualified_reveal_stage,
        },
        "alternate_disposition_ref": alternate_disposition_ref,
        "armed": False,
        "state": "NOT_ARMED",
    }
    assert_capsule(capsule)
    return capsule


def arm_capsule(capsule: Dict[str, Any], *, participant_activation_receipt_ref: str) -> Dict[str, Any]:
    assert_capsule(capsule)
    if not participant_activation_receipt_ref:
        raise LegacyCapsuleError("explicit participant activation receipt required")
    result = copy.deepcopy(capsule)
    result["armed"] = True
    result["state"] = "ARMED"
    result["participant_activation_receipt_ref"] = participant_activation_receipt_ref
    # This runtime intentionally returns an extended runtime record rather than
    # asserting it still conforms to the storage schema.
    return result


def evaluate_disclosure(
    capsule: Dict[str, Any],
    *,
    evidence: Iterable[str],
) -> Dict[str, Any]:
    assert_capsule(capsule)
    facts: Set[str] = {str(item) for item in evidence}

    if "INVITATION_DELIVERED" not in facts:
        return {"stage": "UNKNOWN", "disclose": (), "release_admissible": False}

    stage = "INVITED"
    disclose = []
    if capsule["disclosure"]["invite_reveals_originator"]:
        disclose.append("ORIGINATOR_IDENTITY")

    if "RECIPIENT_PARTICIPATING" in facts:
        stage = "PARTICIPATING"

    qualified = (
        "RECIPIENT_IDENTITY_VERIFIED" in facts
        and "RECIPIENT_PARTICIPATION_QUALIFIED" in facts
    )
    if qualified:
        stage = "QUALIFIED"
        target = capsule["disclosure"]["qualified_reveal_stage"]
        target_index = DISCLOSURE_STAGES.index(target)
        for item in DISCLOSURE_STAGES[4 : target_index + 1]:
            disclose.append(item)

    release_admissible = (
        capsule.get("armed") is True
        and qualified
        and "RELEASE_TRIGGER_VERIFIED" in facts
        and "TVC_AUTHORIZATION_VERIFIED" in facts
        and "INTR_RELEASE_ALLOW" in facts
    )

    return {
        "stage": stage,
        "disclose": tuple(dict.fromkeys(disclose)),
        "release_admissible": release_admissible,
    }
