from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from typing import Callable, Iterable, Sequence

from .core import AuthorizationContext, ChainEvent
from .access import RelationshipState


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OpaqueRouteEntry:
    route_token: str
    pair_id: str
    policy_ref: str
    relationship_epoch: int
    event_ids: tuple[str, ...]
    event_set_commitment: str

    @classmethod
    def build(
        cls,
        *,
        route_token: str,
        pair_id: str,
        policy_ref: str,
        relationship_epoch: int,
        event_ids: Sequence[str],
    ) -> "OpaqueRouteEntry":
        if not route_token or not event_ids:
            raise ValueError("route token and event ids are required")
        return cls(
            route_token=route_token,
            pair_id=pair_id,
            policy_ref=policy_ref,
            relationship_epoch=relationship_epoch,
            event_ids=tuple(event_ids),
            event_set_commitment=_digest(tuple(event_ids)),
        )


class OpaqueRouteIndex:
    """Low-information candidate routing.

    Route tokens are opaque outputs of an authorized resolver. Plaintext search
    terms and semantic labels are never stored in this index.
    """

    def __init__(self, entries: Iterable[OpaqueRouteEntry]) -> None:
        self._entries = tuple(entries)

    def candidates(
        self,
        *,
        query: str,
        auth: AuthorizationContext,
        relationship: RelationshipState,
        resolve_token: Callable[[str, AuthorizationContext], str],
        max_candidates: int = 64,
    ) -> tuple[str, ...]:
        relationship.validate(auth)
        token = resolve_token(query, auth)
        if not token:
            raise PermissionError("authorized route resolver returned no token")

        selected: list[str] = []
        for entry in self._entries:
            if not hmac.compare_digest(entry.route_token, token):
                continue
            if entry.pair_id != auth.pair_id or entry.policy_ref != auth.policy_ref:
                raise PermissionError("opaque route binding mismatch")
            if entry.relationship_epoch != auth.relationship_epoch:
                raise PermissionError("opaque route epoch mismatch")
            if not hmac.compare_digest(entry.event_set_commitment, _digest(entry.event_ids)):
                raise ValueError("opaque route event commitment mismatch")
            selected.extend(entry.event_ids)

        unique = tuple(dict.fromkeys(selected))
        if len(unique) > max_candidates:
            raise ValueError("candidate route exceeds bounded window")
        return unique


def validate_candidate_events(
    candidate_ids: Sequence[str],
    events: Iterable[ChainEvent],
    auth: AuthorizationContext,
) -> tuple[str, ...]:
    by_id = {event.event_id: event for event in events}
    validated: list[str] = []
    for event_id in candidate_ids:
        event = by_id.get(event_id)
        if event is None:
            raise KeyError(f"unknown routed event: {event_id}")
        if event.pair_id != auth.pair_id or event.policy_ref != auth.policy_ref:
            raise PermissionError("routed event crosses pair or policy boundary")
        event.verify()
        validated.append(event_id)
    return tuple(validated)
