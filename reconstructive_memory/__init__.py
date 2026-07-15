"""Privacy-preserving reconstructive memory primitives.

This package is dependency-free and prototype-scoped. It models minimal
continuity, pair-bound authorization, authenticated minimized ingestion, bounded
ephemeral reconstruction, durable replay controls, lifecycle tombstones,
plaintext-free journals, authoritative commit boundaries, receipt propagation,
and deployment adapter contracts without storing plaintext chat in the chain.
"""

from .access import AccessReceipt, CallableKeyUnwrapper, KeyUnwrapper, RelationshipRegistry, RelationshipState, make_access_receipt
from .authority import AuthoritativeSessionStore, CommitSnapshot, PreparedSession
from .core import AuthorizationContext, ChainEvent, EphemeralReconstructor, ProtectedObject, ReconstructionResult, compute_pair_id
from .deployment import BlobMasterRecordsStateStore, MasterRecordsDeliveryClient, MasterRecordsStateCodec, ReplicatedBlobStore, deliver_due_exports
from .ingestion import ChatObservation, ContentProtector, EcosystemChatIngestor, IngestionResult
from .journal import SessionJournal, SessionJournalEntry
from .lifecycle import CapabilityGrant, ObjectLifecycleRegistry, ObjectLifecycleState, make_tombstone_event
from .master_records import MasterRecordAcknowledgement, MasterRecordEnvelope, MasterRecordsOutbox, MasterRecordsVerifier
from .master_records_state import DurableMasterRecordsOutbox, InMemoryMasterRecordsStateStore, MasterRecordsEntry, MasterRecordsState, MasterRecordsStateStore
from .proofs import CallableProofVerifier, ProofVerifier, require_dual_proof
from .replay import DurableTransportReplayRegistry, InMemoryReplayStateStore, ReplayState, ReplayStateStore
from .routing import OpaqueRouteEntry, OpaqueRouteIndex, validate_candidate_events
from .session import ReconstructionSessionCoordinator, ReconstructionSessionResult
from .transport import AuthenticatedChatTransportAdapter, ChatTransportEnvelope, TransportReplayRegistry, TransportVerifier

__all__ = [name for name in globals() if not name.startswith("_")]
