from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .core import AuthorizationContext


class ProofVerifier(Protocol):
    def verify_user(self, auth: AuthorizationContext) -> bool:
        """Verify the StegID proof for this bounded authorization context."""

    def verify_entity(self, auth: AuthorizationContext) -> bool:
        """Verify the designated AI-entity proof for this context."""


@dataclass(frozen=True)
class CallableProofVerifier:
    user_operation: Callable[[AuthorizationContext], bool]
    entity_operation: Callable[[AuthorizationContext], bool]

    def verify_user(self, auth: AuthorizationContext) -> bool:
        return bool(self.user_operation(auth))

    def verify_entity(self, auth: AuthorizationContext) -> bool:
        return bool(self.entity_operation(auth))


def require_dual_proof(auth: AuthorizationContext, verifier: ProofVerifier) -> None:
    """Fail closed unless both independently verified proofs succeed."""
    if not verifier.verify_user(auth):
        raise PermissionError("StegID proof verification failed")
    if not verifier.verify_entity(auth):
        raise PermissionError("AI-entity proof verification failed")
