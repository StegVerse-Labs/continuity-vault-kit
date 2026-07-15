from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .access import AccessReceipt, RelationshipRegistry, make_access_receipt
from .core import AuthorizationContext, ChainEvent, EphemeralReconstructor, ProtectedObject, ReconstructionResult
from .lifecycle import CapabilityGrant, ObjectLifecycleRegistry
from .proofs import ProofVerifier, require_dual_proof
from .routing import OpaqueRouteIndex, validate_candidate_events


@dataclass(frozen=True)
class ReconstructionSessionResult:
    reconstruction: ReconstructionResult
    receipt: AccessReceipt
    consumed_capability: CapabilityGrant


class ReconstructionSessionCoordinator:
    """Run one bounded reconstruction as a fail-closed logical transaction.

    The coordinator does not persist mutable state. A production service must
    atomically store the returned consumed capability alongside the receipt.
    """

    def __init__(
        self,
        *,
        events: Iterable[ChainEvent],
        objects: Mapping[str, ProtectedObject],
        relationships: RelationshipRegistry,
        lifecycles: ObjectLifecycleRegistry,
        route_index: OpaqueRouteIndex,
        proof_verifier: ProofVerifier,
        decrypt: Callable[[ProtectedObject, AuthorizationContext], str],
        resolve_token: Callable[[str, AuthorizationContext], str],
    ) -> None:
        self._events = tuple(events)
        self._objects = dict(objects)
        self._relationships = relationships
        self._lifecycles = lifecycles
        self._route_index = route_index
        self._proof_verifier = proof_verifier
        self._decrypt = decrypt
        self._resolve_token = resolve_token

    def execute(
        self,
        *,
        query: str,
        auth: AuthorizationContext,
        capability: CapabilityGrant,
        now: int,
        receipt_id: str,
        max_candidates: int = 64,
        max_events: int = 32,
    ) -> ReconstructionSessionResult:
        if not query:
            raise ValueError("query is required")
        if not receipt_id:
            raise ValueError("receipt id is required")

        relationship = self._relationships.resolve(auth)
        require_dual_proof(auth, self._proof_verifier)
        capability.validate(auth, now=now)

        candidates = self._route_index.candidates(
            query=query,
            auth=auth,
            relationship=relationship,
            resolve_token=self._resolve_token,
            max_candidates=max_candidates,
        )
        if not candidates:
            raise LookupError("authorized route returned no candidate events")
        validated = validate_candidate_events(candidates, self._events, auth)

        def guarded_decrypt(protected: ProtectedObject, context: AuthorizationContext) -> str:
            self._lifecycles.resolve(protected)
            return self._decrypt(protected, context)

        reconstructor = EphemeralReconstructor(self._events, self._objects, guarded_decrypt)
        reconstruction = reconstructor.reconstruct(validated, auth, max_events=max_events)
        receipt = make_access_receipt(
            receipt_id=receipt_id,
            auth=auth,
            request_descriptor={
                "route_candidate_count": len(validated),
                "max_candidates": max_candidates,
                "max_events": max_events,
            },
            result=reconstruction,
        )
        consumed = capability.consume(auth, now=now)
        return ReconstructionSessionResult(
            reconstruction=reconstruction,
            receipt=receipt,
            consumed_capability=consumed,
        )
