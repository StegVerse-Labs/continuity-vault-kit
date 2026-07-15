"""Validation helpers for mutually declared governed AI relationships."""

from __future__ import annotations

from typing import Any


class RelationshipDeclarationError(ValueError):
    """Raised when a relationship declaration violates mandatory invariants."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RelationshipDeclarationError(message)


def validate_relationship_declaration(declaration: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "relationship_id",
        "principal",
        "ai_entity",
        "user_responsibilities",
        "ai_responsibilities",
        "ai_declared_limitations",
        "renegotiation_triggers",
        "revision",
        "status",
        "receipt_policy",
    }
    missing = sorted(required - declaration.keys())
    _require(not missing, f"missing fields: {missing}")
    _require(declaration["schema_version"] == "0.1", "schema_version must be 0.1")

    for field in ("user_responsibilities", "ai_responsibilities", "ai_declared_limitations"):
        values = declaration[field]
        _require(isinstance(values, list) and values, f"{field} must be non-empty")
        _require(len(values) == len(set(values)), f"{field} must be unique")

    triggers = declaration["renegotiation_triggers"]
    _require(isinstance(triggers, list) and triggers, "renegotiation_triggers must be non-empty")
    allowed_responses = {"DISCLOSE", "ASK", "PAUSE", "RENEGOTIATE"}
    for trigger in triggers:
        _require(trigger.get("required_response") in allowed_responses, "invalid renegotiation response")

    revision = declaration["revision"]
    accepted_by = set(revision.get("accepted_by", []))
    if declaration["status"] == "active":
        _require(accepted_by == {"user", "ai_entity"}, "active relationship requires mutual acceptance")

    receipt = declaration["receipt_policy"]
    _require(receipt.get("required") is True, "relationship transitions require receipts")
    events = set(receipt.get("events", []))
    _require("relationship_accepted" in events, "relationship_accepted receipt required")
    _require("relationship_revised" in events, "relationship_revised receipt required")
    _require("renegotiation_requested" in events, "renegotiation_requested receipt required")
