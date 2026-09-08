"""KnowledgeVault inter-instance relationship semantics.

This module defines capability tiers only. It does not create provider sessions,
copy data, synchronize storage, or grant Interlock/InTr authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


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


def capabilities_for(tier: KVRelationshipTier | str) -> KVRelationshipCapabilities:
    if isinstance(tier, str):
        tier = KVRelationshipTier[tier]
    return CAPABILITIES[tier]


def validate_transition(current: KVRelationshipTier | str, target: KVRelationshipTier | str) -> bool:
    """Return whether the target tier is structurally representable.

    Relationship tiers are ordered by capability, but downgrade and upgrade authority
    are intentionally not granted here. Interlock/InTr policy must separately admit
    the actual transition when runtime governance is active.
    """
    if isinstance(current, str):
        current = KVRelationshipTier[current]
    if isinstance(target, str):
        target = KVRelationshipTier[target]
    return current in KVRelationshipTier and target in KVRelationshipTier


def relationship_record(tier: KVRelationshipTier | str) -> dict[str, object]:
    if isinstance(tier, str):
        tier = KVRelationshipTier[tier]
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
