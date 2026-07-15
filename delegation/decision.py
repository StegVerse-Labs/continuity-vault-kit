"""Dependency-light governed delegation validation and ACT/ASK/DENY decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


class DelegationError(ValueError):
    """Raised when a delegation policy violates mandatory invariants."""


@dataclass(frozen=True)
class Decision:
    outcome: str
    reason: str
    delegation_id: str | None
    authority_source: str | None
    receipt_required: bool = True


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DelegationError(message)


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def validate_delegation(policy: dict[str, Any]) -> None:
    required = {
        "schema_version", "delegation_id", "principal", "delegate",
        "authority_source", "scope", "validity", "confirmation_policy",
        "receipt_policy", "status",
    }
    missing = sorted(required - policy.keys())
    _require(not missing, f"missing fields: {missing}")
    _require(policy["schema_version"] == "0.1", "schema_version must be 0.1")
    _require(policy["authority_source"] in {"direct_instruction", "standing_delegation"}, "invalid authority_source")

    scope = policy["scope"]
    for field in ("actions", "resources", "destinations"):
        values = scope.get(field)
        _require(isinstance(values, list) and values, f"scope.{field} must be non-empty")
        _require(len(values) == len(set(values)), f"scope.{field} must be unique")

    validity = policy["validity"]
    _require(validity.get("revocable") is True, "delegation must be revocable")
    status = policy["status"]
    _require(status in {"proposed", "active", "revoked", "expired", "rejected"}, "invalid status")
    if status == "revoked":
        _require(bool(validity.get("revoked_at")), "revoked delegation needs revoked_at")
        _require(bool(validity.get("revocation_reason")), "revoked delegation needs reason")

    receipt = policy["receipt_policy"]
    _require(receipt.get("required") is True, "material delegated actions require receipts")
    events = set(receipt.get("events", []))
    _require("action_authorized" in events, "action_authorized receipt required")
    _require("action_completed" in events, "action_completed receipt required")

    for rule in policy.get("escalation_rules", []):
        _require(rule.get("decision") == "ASK", "escalation rules may only produce ASK")


def decide(
    policy: dict[str, Any] | None,
    request: dict[str, Any],
    *,
    now: datetime | None = None,
) -> Decision:
    """Evaluate current authority without inferring authority from technical access."""
    if policy is None:
        return Decision("DENY", "no current authority", None, None)

    validate_delegation(policy)
    now = now or datetime.now(timezone.utc)
    validity = policy["validity"]
    starts = _parse_time(validity.get("starts_at"))
    expires = _parse_time(validity.get("expires_at"))

    if policy["status"] != "active":
        return Decision("DENY", f"delegation status is {policy['status']}", policy["delegation_id"], policy["authority_source"])
    if validity.get("revoked_at"):
        return Decision("DENY", "delegation revoked", policy["delegation_id"], policy["authority_source"])
    if starts and now < starts:
        return Decision("DENY", "delegation not yet valid", policy["delegation_id"], policy["authority_source"])
    if expires and now >= expires:
        return Decision("DENY", "delegation expired", policy["delegation_id"], policy["authority_source"])

    scope = policy["scope"]
    action = request.get("action")
    resource = request.get("resource")
    destination = request.get("destination")

    if action not in scope["actions"]:
        return Decision("ASK", "action exceeds delegated scope", policy["delegation_id"], policy["authority_source"])
    if resource not in scope["resources"]:
        return Decision("ASK", "resource exceeds delegated scope", policy["delegation_id"], policy["authority_source"])
    if destination not in scope["destinations"]:
        return Decision("ASK", "destination exceeds delegated scope", policy["delegation_id"], policy["authority_source"])

    exclusions = set(scope.get("exclusions", []))
    requested_features = set(request.get("features", []))
    if exclusions & requested_features:
        return Decision("ASK", "request intersects an explicit exclusion", policy["delegation_id"], policy["authority_source"])

    if request.get("material_context_change") is True:
        return Decision("ASK", "material context changed", policy["delegation_id"], policy["authority_source"])

    if policy["confirmation_policy"] == "always_confirm":
        return Decision("ASK", "user selected per-action confirmation", policy["delegation_id"], policy["authority_source"])

    return Decision("ACT", "request is covered by current delegated authority", policy["delegation_id"], policy["authority_source"])
