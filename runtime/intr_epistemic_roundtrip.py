"""Executable source proof for inter-Entity epistemic discovery propagation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from runtime.intr_epistemic_state import (
    EpistemicItem,
    EntityAcknowledgement,
    acknowledgement_for,
    aggregate_receiver_completion,
    discovered_unknown,
)


@dataclass(frozen=True)
class RoundTripResult:
    discovery: EpistemicItem
    acknowledgements: tuple[EntityAcknowledgement, ...]
    unresolved_entities: tuple[str, ...]
    dependent_state: str


def execute_discovery_roundtrip(*, source_entity: str, affected_entities: Iterable[str],
                                item: EpistemicItem, discovery_id: str,
                                evidence_refs: Iterable[str]) -> RoundTripResult:
    """Exercise discovery -> receiver probe disposition -> acknowledgement -> recompute.

    This is a source-level protocol proof only. It does not claim network transport,
    runtime activation, governance, or receiver truth agreement.
    """
    affected = tuple(affected_entities)
    if not source_entity.strip() or not affected:
        raise ValueError("source_entity and affected_entities are required")
    discovery = discovered_unknown(
        item,
        discovery_id=discovery_id,
        evidence_refs=evidence_refs,
        scope_hypothesis=affected,
    )
    acknowledgements = tuple(
        acknowledgement_for(
            acknowledgement_id=f"ack:{discovery_id}:{entity}",
            receiver_entity=entity,
            source_message_id=f"discovery:{discovery_id}",
            item=discovery,
            level="RECEIVED",
        )
        for entity in affected
    )
    unresolved = aggregate_receiver_completion(
        affected_entities=affected,
        acknowledgements=acknowledgements,
        consequence="HIGH_CONSEQUENCE",
    )
    dependent_state = "PROBE_REQUIRED" if unresolved else "READY"
    return RoundTripResult(discovery, acknowledgements, unresolved, dependent_state)
