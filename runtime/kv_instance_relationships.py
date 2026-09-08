"""KnowledgeVault inter-instance relationship semantics.

This module defines the four capability tiers and non-authorizing transition proposals.
It does not create provider sessions, copy data, synchronize storage, expose data to an
AI system, or grant Interlock/InTr authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class KVRelationshipTier(IntEnum):
    NOT_CONNECTED = 0
    CONNECTED = 1
    SYNCED = 2
    AI_INTERACTION = 3


@dataclass(frozen=True)
class KVRelationshipCapabilities:
    inter_comms: bool
    data_movement: bool
    replication: bool
    unified_ai_corpus: bool


CAPABILITIES = {
    KVRelationshipTier.NOT_CONNECTED: KVRelationshipCapabilities(False, False, False, False),
    KVRelationshipTier.CONNECTED: KVRelationshipCapabilities(True, True, False, False),
    KVRelationshipTier.SYNCED: KVRelationshipCapabilities(True, True, True, False),
    KVRelationshipTier.AI_INTERACTION: KVRelationshipCapabilities(True, True, True, True),
}

TRANSITION_SCHEMA = "stegverse.kv.relationship-transition-request/v1"


def _tier(value: KVRelationshipTier | str) -> KVRelationshipTier:
    return KVRelationshipTier[value] if isinstance(value, str) else value


def capabilities_for(tier: KVRelationshipTier | str) -> KVRelationshipCapabilities:
    return CAPABILITIES[_tier(tier)]


def validate_transition(current: KVRelationshipTier | str, target: KVRelationshipTier | str) -> bool:
    """Return whether both tiers are structurally representable.

    Upgrade and downgrade authority are intentionally not granted here. Interlock/InTr
    must separately admit the actual transition when runtime governance is active.
    """
    return _tier(current) in KVRelationshipTier and _tier(target) in KVRelationshipTier


def relationship_record(tier: KVRelationshipTier | str) -> dict[str, object]:
    tier = _tier(tier)
    caps = capabilities_for(tier)
    return {
        "tier": tier.name,
        "tier_order": int(tier),
        "inter_comms": caps.inter_comms,
        "data_movement": caps.data_movement,
        "replication": caps.replication,
        "unified_ai_corpus": caps.unified_ai_corpus,
        "authority_effect": "NONE",
        "activation_effect": False,
    }


def transition_request(
    *,
    kv_set_id: str,
    participant_instance_ids: Iterable[str],
    current_tier: KVRelationshipTier | str,
    target_tier: KVRelationshipTier | str,
    requested_by: str = "owner",
) -> dict[str, object]:
    """Create a deterministic, non-authorizing relationship transition request.

    The request is suitable for later Interlock/InTr admission. Creating it does not
    perform the transition. A relationship requires at least two unique participants.
    """
    current = _tier(current_tier)
    target = _tier(target_tier)
    participants = sorted({str(value).strip() for value in participant_instance_ids if str(value).strip()})
    if not kv_set_id.strip():
        raise ValueError("kv_set_id is required")
    if len(participants) < 2:
        raise ValueError("at least two unique KV participant instance IDs are required")
    if not all(value.startswith("kvi_") for value in participants):
        raise ValueError("participant instance IDs must use kvi_ identifiers")
    if not requested_by.strip():
        raise ValueError("requested_by is required")

    canonical = {
        "kv_set_id": kv_set_id.strip(),
        "participants": participants,
        "current_tier": current.name,
        "target_tier": target.name,
        "requested_by": requested_by.strip(),
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    direction = "UNCHANGED" if current == target else ("UPGRADE" if target > current else "DOWNGRADE")
    return {
        "schema": TRANSITION_SCHEMA,
        "request_id": f"kvrel_{digest[:24]}",
        **canonical,
        "direction": direction,
        "requested_capabilities": relationship_record(target),
        "governance_state": "PENDING_INTERLOCK_INTR",
        "authority_effect": "NONE",
        "activation_effect": False,
        "data_moved": False,
        "replication_started": False,
        "ai_corpus_exposed": False,
    }
