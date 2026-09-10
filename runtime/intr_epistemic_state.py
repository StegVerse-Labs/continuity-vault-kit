"""Universal epistemic-state discipline for StegVerse InTr communications.

Every inter-Entity communication may carry assertions, questions, ambiguity,
unknowns, discoveries, probes, corrections, and acknowledgements. Transport of
an envelope grants no governance or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Literal

EpistemicState = Literal["KNOWN", "UNKNOWN", "AMBIGUOUS", "DISCOVERED_UNKNOWN", "DISPUTED"]
Applicability = Literal["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]
ReadinessEffect = Literal["NONE", "PROBE_REQUIRED", "BLOCKING", "RECOMPUTE_REQUIRED"]
IncorporationState = Literal["INCORPORATED", "NOT_APPLICABLE", "PROBE_REQUIRED", "REJECTED_AS_INVALID"]


@dataclass(frozen=True)
class EpistemicItem:
    item_id: str
    subject: str
    state: EpistemicState
    applicability: Applicability
    source_evidence_refs: tuple[str, ...] = ()
    readiness_effect: ReadinessEffect = "NONE"
    discovery_id: str | None = None
    supersedes_item_id: str | None = None
    probe_ref: str | None = None


@dataclass(frozen=True)
class EntityAcknowledgement:
    receiver_entity: str
    source_message_id: str
    item_id: str
    incorporation_state: IncorporationState
    incorporated_predicate_id: str | None = None
    evidence_refs: tuple[str, ...] = ()


def classify_received_item(item: EpistemicItem) -> IncorporationState:
    """Determine the mandatory receiver-side disposition of one communicated item."""
    if item.applicability == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if item.applicability == "UNKNOWN":
        return "PROBE_REQUIRED"
    if item.state in {"UNKNOWN", "AMBIGUOUS", "DISCOVERED_UNKNOWN", "DISPUTED"}:
        return "PROBE_REQUIRED"
    return "INCORPORATED"


def acknowledgement_for(
    *, receiver_entity: str,
    source_message_id: str,
    item: EpistemicItem,
    incorporated_predicate_id: str | None = None,
    evidence_refs: Iterable[str] = (),
) -> EntityAcknowledgement:
    """Create a durable receiver acknowledgement without inventing resolution."""
    disposition = classify_received_item(item)
    if disposition == "INCORPORATED" and not incorporated_predicate_id:
        incorporated_predicate_id = item.item_id
    if disposition == "PROBE_REQUIRED" and incorporated_predicate_id is None:
        incorporated_predicate_id = item.item_id
    return EntityAcknowledgement(
        receiver_entity=receiver_entity,
        source_message_id=source_message_id,
        item_id=item.item_id,
        incorporation_state=disposition,
        incorporated_predicate_id=incorporated_predicate_id,
        evidence_refs=tuple(evidence_refs),
    )


def discovered_unknown(
    item: EpistemicItem,
    *, discovery_id: str,
    evidence_refs: Iterable[str],
) -> EpistemicItem:
    """Promote a formerly unrepresented condition into explicit known state.

    Discovery does not prove applicability or truth. It makes the condition
    representable and therefore impossible for affected entities to silently omit.
    """
    if not discovery_id.strip():
        raise ValueError("discovery_id must be non-empty")
    refs = tuple(evidence_refs)
    if not refs:
        raise ValueError("discovered unknown requires evidence provenance")
    return replace(
        item,
        state="DISCOVERED_UNKNOWN",
        applicability="UNKNOWN",
        source_evidence_refs=refs,
        readiness_effect="RECOMPUTE_REQUIRED",
        discovery_id=discovery_id,
    )


def unresolved_acknowledgements_block_ready(
    acknowledgements: Iterable[EntityAcknowledgement],
) -> bool:
    """READY is forbidden while any affected receiver still requires a probe."""
    return any(a.incorporation_state == "PROBE_REQUIRED" for a in acknowledgements)
