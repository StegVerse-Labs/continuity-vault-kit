"""Universal epistemic-state discipline for StegVerse InTr communications.

Transport proves carriage. This module represents how a receiving Entity treats
meaning: receipt, interpretation, applicability, evidence acceptance, agreement,
incorporation, dispute, freshness, correction, supersession, and unknown discovery.
It grants no governance or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable, Literal

EpistemicState = Literal["KNOWN", "UNKNOWN", "AMBIGUOUS", "DISCOVERED_UNKNOWN", "DISPUTED"]
Applicability = Literal["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]
ReadinessEffect = Literal["NONE", "PROBE_REQUIRED", "BLOCKING", "RECOMPUTE_REQUIRED"]
IncorporationState = Literal["INCORPORATED", "NOT_APPLICABLE", "PROBE_REQUIRED", "REJECTED_AS_INVALID", "DISPUTED"]
AckLevel = Literal["RECEIVED", "INTERPRETED", "APPLICABILITY_RESOLVED", "EVIDENCE_ACCEPTED", "AGREED", "INCORPORATED"]
ConsequenceClass = Literal["INFORMATIONAL", "STATE_RELEVANT", "STATE_CHANGING", "HIGH_CONSEQUENCE"]

ACK_ORDER: tuple[AckLevel, ...] = (
    "RECEIVED", "INTERPRETED", "APPLICABILITY_RESOLVED", "EVIDENCE_ACCEPTED", "AGREED", "INCORPORATED"
)
REQUIRED_ACK_BY_CONSEQUENCE: dict[ConsequenceClass, AckLevel] = {
    "INFORMATIONAL": "RECEIVED",
    "STATE_RELEVANT": "INTERPRETED",
    "STATE_CHANGING": "APPLICABILITY_RESOLVED",
    "HIGH_CONSEQUENCE": "INCORPORATED",
}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include timezone")
    return parsed.astimezone(timezone.utc)


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
    scope_hypothesis: tuple[str, ...] = ()
    valid_until: str | None = None


@dataclass(frozen=True)
class EntityAcknowledgement:
    acknowledgement_id: str
    receiver_entity: str
    source_message_id: str
    item_id: str
    level: AckLevel
    incorporation_state: IncorporationState
    incorporated_predicate_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    observed_at: str | None = None
    interpretation_ref: str | None = None
    dispute_ref: str | None = None


def classify_received_item(item: EpistemicItem) -> IncorporationState:
    if item.state == "DISPUTED":
        return "DISPUTED"
    if item.applicability == "NOT_APPLICABLE":
        return "NOT_APPLICABLE"
    if item.applicability == "UNKNOWN":
        return "PROBE_REQUIRED"
    if item.state in {"UNKNOWN", "AMBIGUOUS", "DISCOVERED_UNKNOWN"}:
        return "PROBE_REQUIRED"
    return "INCORPORATED"


def acknowledgement_for(*, acknowledgement_id: str, receiver_entity: str, source_message_id: str,
                        item: EpistemicItem, level: AckLevel = "RECEIVED",
                        incorporated_predicate_id: str | None = None,
                        evidence_refs: Iterable[str] = (), observed_at: str | None = None,
                        interpretation_ref: str | None = None,
                        dispute_ref: str | None = None) -> EntityAcknowledgement:
    """Create one durable acknowledgement dimension; receipt never implies agreement."""
    if not acknowledgement_id.strip():
        raise ValueError("acknowledgement_id must be non-empty")
    disposition = classify_received_item(item)
    if level == "INCORPORATED" and disposition == "INCORPORATED" and not incorporated_predicate_id:
        incorporated_predicate_id = item.item_id
    if disposition == "PROBE_REQUIRED" and level in {"APPLICABILITY_RESOLVED", "EVIDENCE_ACCEPTED", "AGREED", "INCORPORATED"}:
        raise ValueError("cannot advance acknowledgement beyond unresolved applicability/ambiguity")
    if disposition == "DISPUTED" and not dispute_ref:
        raise ValueError("DISPUTED acknowledgement requires dispute_ref")
    return EntityAcknowledgement(
        acknowledgement_id=acknowledgement_id,
        receiver_entity=receiver_entity,
        source_message_id=source_message_id,
        item_id=item.item_id,
        level=level,
        incorporation_state=disposition,
        incorporated_predicate_id=incorporated_predicate_id,
        evidence_refs=tuple(evidence_refs),
        observed_at=observed_at,
        interpretation_ref=interpretation_ref,
        dispute_ref=dispute_ref,
    )


def discovered_unknown(item: EpistemicItem, *, discovery_id: str, evidence_refs: Iterable[str],
                       scope_hypothesis: Iterable[str] = ()) -> EpistemicItem:
    """Make a latent condition representable without asserting truth or applicability."""
    if not discovery_id.strip():
        raise ValueError("discovery_id must be non-empty")
    refs = tuple(evidence_refs)
    if not refs:
        raise ValueError("discovered unknown requires evidence provenance")
    return replace(item, state="DISCOVERED_UNKNOWN", applicability="UNKNOWN",
                   source_evidence_refs=refs, readiness_effect="RECOMPUTE_REQUIRED",
                   discovery_id=discovery_id, scope_hypothesis=tuple(scope_hypothesis))


def supersede(item: EpistemicItem, *, new_item_id: str, state: EpistemicState,
              evidence_refs: Iterable[str]) -> EpistemicItem:
    """Create append-only correction/supersession lineage instead of rewriting history."""
    refs = tuple(evidence_refs)
    if not refs:
        raise ValueError("correction/supersession requires evidence provenance")
    return replace(item, item_id=new_item_id, state=state, source_evidence_refs=refs,
                   supersedes_item_id=item.item_id)


def acknowledgement_is_fresh(ack: EntityAcknowledgement, item: EpistemicItem, *, now: str) -> bool:
    """A time-bounded epistemic item cannot support dependent state after expiry."""
    if item.valid_until is None:
        return True
    if ack.observed_at is None:
        return False
    return _parse_time(ack.observed_at) <= _parse_time(item.valid_until) and _parse_time(now) <= _parse_time(item.valid_until)


def acknowledgement_satisfies_consequence(ack: EntityAcknowledgement, consequence: ConsequenceClass) -> bool:
    required = REQUIRED_ACK_BY_CONSEQUENCE[consequence]
    return ACK_ORDER.index(ack.level) >= ACK_ORDER.index(required) and ack.incorporation_state not in {"PROBE_REQUIRED", "DISPUTED", "REJECTED_AS_INVALID"}


def aggregate_receiver_completion(*, affected_entities: Iterable[str], acknowledgements: Iterable[EntityAcknowledgement],
                                  consequence: ConsequenceClass) -> tuple[str, ...]:
    """Return affected Entities that have not reached the required acknowledgement depth."""
    required = set(affected_entities)
    satisfied = {ack.receiver_entity for ack in acknowledgements if acknowledgement_satisfies_consequence(ack, consequence)}
    return tuple(sorted(required - satisfied))


def unresolved_acknowledgements_block_ready(acknowledgements: Iterable[EntityAcknowledgement]) -> bool:
    return any(a.incorporation_state in {"PROBE_REQUIRED", "DISPUTED", "REJECTED_AS_INVALID"} for a in acknowledgements)
