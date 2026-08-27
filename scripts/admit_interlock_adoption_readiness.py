#!/usr/bin/env python3
"""Admit StegOS Universal Interlock adoption-readiness as explanatory KV facts."""
from __future__ import annotations

from typing import Any, Mapping

SOURCE_SCHEMA = "stegos.universal_interlock_adoption_readiness.v1"
ADMISSION_SCHEMA = "stegverse.kv.interlock-adoption-readiness-admission/v1"
PROTOCOL_ID = "SV-INTERLOCK-v0.4-candidate"


class AdmissionError(ValueError):
    pass


def admit_interlock_adoption_readiness(
    assessment: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(assessment, Mapping):
        raise AdmissionError("Interlock adoption-readiness assessment object required")
    if assessment.get("schema") != SOURCE_SCHEMA:
        raise AdmissionError("unexpected Interlock adoption-readiness schema")
    if assessment.get("protocol_id") != PROTOCOL_ID:
        raise AdmissionError("Interlock protocol id mismatch")
    state = assessment.get("state")
    blockers = assessment.get("blockers")
    if state not in {"BLOCKED", "READY_FOR_ADOPTION_REVIEW"}:
        raise AdmissionError("invalid Interlock adoption-readiness state")
    if not isinstance(blockers, list) or any(
        not isinstance(item, str) or not item for item in blockers
    ):
        raise AdmissionError("Interlock adoption-readiness blockers invalid")
    if state == "BLOCKED" and not blockers:
        raise AdmissionError("blocked Interlock assessment must expose blockers")
    if state == "READY_FOR_ADOPTION_REVIEW" and blockers:
        raise AdmissionError("ready Interlock assessment cannot retain blockers")

    forbidden_true = (
        "canonical_protocol_adopted",
        "runtime_activation",
        "production_interlock_runtime_activated",
        "adoption_decision_created",
        "execute_consequence",
        "canonical_result_committed",
    )
    for field in forbidden_true:
        if assessment.get(field) is not False:
            raise AdmissionError(f"{field} must remain false")

    if assessment.get("credential_authority") != "TV/TVC":
        raise AdmissionError("credential authority must remain TV/TVC")
    if assessment.get("master_records_authority_effect") != "NONE":
        raise AdmissionError("Master Records authority effect must remain NONE")
    if assessment.get("authority_effect") != "NONE":
        raise AdmissionError("Interlock adoption-readiness authority effect must remain NONE")

    ready = state == "READY_FOR_ADOPTION_REVIEW"
    return {
        "schema": ADMISSION_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "decision": "ADMIT_EXPLANATORY_FACTS",
        "facts_delta": {
            "universal_interlock_adoption_review_ready": ready,
            "universal_interlock_adoption_review_state": state,
            "universal_interlock_adoption_review_blockers": list(blockers),
        },
        "production_interlock_runtime_activated_set_by_adapter": False,
        "canonical_protocol_adopted_set_by_adapter": False,
        "activation_performed": False,
        "authority_effect": "NONE",
    }
