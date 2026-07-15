"""Privacy-preserving reconstructive memory primitives.

This package is dependency-free and prototype-scoped. It models minimal
continuity, pair-bound authorization, minimized ingestion, bounded ephemeral
reconstruction, replay controls, lifecycle tombstones, plaintext-free journals,
and authoritative commit boundaries without storing plaintext chat in the chain.
"""

from .access import (
    AccessReceipt,
    CallableKeyUnwrapper,
    KeyUnwrapper,
    RelationshipRegistry,
    RelationshipState,
    make_access_receipt,
)
from .authority import AuthoritativeSessionStore, CommitSnapshot, PreparedSession
from .core import (
    AuthorizationContext,
    ChainEvent,
    EphemeralReconstructor,
    ProtectedObject,
    ReconstructionResult,
    compute_pair_id,
)
from .ingestion import ChatObservation, ContentProtector, EcosystemChatIngestor, IngestionResult
from .journal import SessionJournal, SessionJournalEntry
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
    "AuthoritativeSessionStore",
    "AuthorizationContext",
    "CallableKeyUnwrapper",
    "CallableProofVerifier",
    "CapabilityGrant",
    "ChainEvent",
    "ChatObservation",
    "CommitSnapshot",
    "ContentProtector",
    "EcosystemChatIngestor",
    "EphemeralReconstructor",
    "IngestionResult",
    "KeyUnwrapper",
    "ObjectLifecycleRegistry",
    "ObjectLifecycleState",
    "OpaqueRouteEntry",
    "OpaqueRouteIndex",
    "PreparedSession",
    "ProofVerifier",
    "ProtectedObject",
    "ReconstructionResult",
    "ReconstructionSessionCoordinator",
    "ReconstructionSessionResult",
    "RelationshipRegistry",
    "RelationshipState",
    "SessionJournal",
    "SessionJournalEntry",
    "compute_pair_id",
    "make_access_receipt",
    "make_tombstone_event",
    "require_dual_proof",
    "validate_candidate_events",
]
