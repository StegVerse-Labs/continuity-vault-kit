"""Privacy-preserving reconstructive memory primitives.

This package is intentionally dependency-free and prototype-scoped. It models a
minimal continuity chain, pair-bound authorization, bounded ephemeral
reconstruction, relationship epochs, proof verification, minimized chat
ingestion, key-unwrapping boundaries, opaque routing, expiring capabilities,
protected-object tombstones, coordinated reconstruction sessions, and access
receipts without storing plaintext chat content in the chain.
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
from .ingestion import ChatObservation, ContentProtector, EcosystemChatIngestor, IngestionResult
from .lifecycle import (
    CapabilityGrant,
    ObjectLifecycleRegistry,
    ObjectLifecycleState,
    make_tombstone_event,
)
from .proofs import CallableProofVerifier, ProofVerifier, require_dual_proof
from .routing import OpaqueRouteEntry, OpaqueRouteIndex, validate_candidate_events
from .session import ReconstructionSessionCoordinator, ReconstructionSessionResult

__all__ = [
    "AccessReceipt",
    "AuthorizationContext",
    "CallableKeyUnwrapper",
    "CallableProofVerifier",
    "CapabilityGrant",
    "ChainEvent",
    "ChatObservation",
    "ContentProtector",
    "EcosystemChatIngestor",
    "EphemeralReconstructor",
    "IngestionResult",
    "KeyUnwrapper",
    "ObjectLifecycleRegistry",
    "ObjectLifecycleState",
    "OpaqueRouteEntry",
    "OpaqueRouteIndex",
    "ProofVerifier",
    "ProtectedObject",
    "ReconstructionResult",
    "ReconstructionSessionCoordinator",
    "ReconstructionSessionResult",
    "RelationshipRegistry",
    "RelationshipState",
    "compute_pair_id",
    "make_access_receipt",
    "make_tombstone_event",
    "require_dual_proof",
    "validate_candidate_events",
]
