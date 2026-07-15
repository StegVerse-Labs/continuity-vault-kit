"""Privacy-preserving reconstructive memory primitives.

This package is intentionally dependency-free and prototype-scoped. It models a
minimal continuity chain, pair-bound authorization, bounded ephemeral
reconstruction, relationship epochs, key-unwrapping boundaries, access
receipts, and opaque candidate routing without storing plaintext chat content
in the chain.
"""

from .core import (
    AuthorizationContext,
    ChainEvent,
    EphemeralReconstructor,
    ProtectedObject,
    ReconstructionResult,
    compute_pair_id,
)
from .access import (
    AccessReceipt,
    CallableKeyUnwrapper,
    KeyUnwrapper,
    RelationshipRegistry,
    RelationshipState,
    make_access_receipt,
)
from .routing import OpaqueRouteEntry, OpaqueRouteIndex, validate_candidate_events

__all__ = [
    "AccessReceipt",
    "AuthorizationContext",
    "CallableKeyUnwrapper",
    "ChainEvent",
    "EphemeralReconstructor",
    "KeyUnwrapper",
    "OpaqueRouteEntry",
    "OpaqueRouteIndex",
    "ProtectedObject",
    "ReconstructionResult",
    "RelationshipRegistry",
    "RelationshipState",
    "compute_pair_id",
    "make_access_receipt",
    "validate_candidate_events",
]
