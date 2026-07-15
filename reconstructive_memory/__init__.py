"""Privacy-preserving reconstructive memory primitives.

This package is intentionally dependency-free and prototype-scoped. It models a
minimal continuity chain, pair-bound authorization, and bounded ephemeral
reconstruction without storing plaintext chat content in the chain.
"""

from .core import (
    AuthorizationContext,
    ChainEvent,
    EphemeralReconstructor,
    ProtectedObject,
    ReconstructionResult,
    compute_pair_id,
)

__all__ = [
    "AuthorizationContext",
    "ChainEvent",
    "EphemeralReconstructor",
    "ProtectedObject",
    "ReconstructionResult",
    "compute_pair_id",
]
