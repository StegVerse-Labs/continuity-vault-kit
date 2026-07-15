"""Governed delegation lifecycle transitions with immutable lineage receipts."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from delegation.decision import validate_delegation


class DelegationTransitionError(ValueError):
    pass


def _canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = target
    for part in parts[:-1]:
        next_value = cursor.get(part)
        if not isinstance(next_value, dict):
            raise DelegationTransitionError(f"invalid change path: {path}")
        cursor = next_value
    cursor[parts[-1]] = deepcopy(value)


def transition_delegation(
    policy: dict[str, Any],
    *,
    transition: str,
    actor: str,
    reason: str,
    occurred_at: str,
    requested_change: dict[str, Any] | None = None,
    user_accepted: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a successor policy and immutable transition receipt."""
    validate_delegation(policy)
    allowed = {"accept", "narrow", "expand", "reject", "revoke", "expire"}
    if transition not in allowed:
        raise DelegationTransitionError("unsupported transition")
    if not actor or not reason:
        raise DelegationTransitionError("actor and reason are required")
    datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))

    user_controlled = {"accept", "narrow", "expand", "reject", "revoke"}
    if transition in user_controlled and not user_accepted:
        raise DelegationTransitionError("transition requires explicit user acceptance")
    if transition == "expire" and actor not in {"system:clock", "user"}:
        raise DelegationTransitionError("expiry may only be recorded by the clock or user")

    successor = deepcopy(policy)
    source_hash = _canonical_hash(policy)

    if transition == "accept":
        if policy["status"] != "proposed":
            raise DelegationTransitionError("only proposed delegations may be accepted")
        successor["status"] = "active"
    elif transition in {"narrow", "expand"}:
        if policy["status"] not in {"active", "proposed"}:
            raise DelegationTransitionError("only active or proposed delegations may be revised")
        if not requested_change:
            raise DelegationTransitionError("revision requires requested_change")
        for path, value in requested_change.items():
            _set_path(successor, path, value)
        successor["status"] = "proposed"
    elif transition == "reject":
        if policy["status"] != "proposed":
            raise DelegationTransitionError("only proposed delegations may be rejected")
        successor["status"] = "rejected"
    elif transition == "revoke":
        if policy["status"] != "active":
            raise DelegationTransitionError("only active delegations may be revoked")
        successor["status"] = "revoked"
        successor["validity"]["revoked_at"] = occurred_at
        successor["validity"]["revocation_reason"] = reason
    elif transition == "expire":
        if policy["status"] != "active":
            raise DelegationTransitionError("only active delegations may expire")
        successor["status"] = "expired"
        successor["validity"]["expires_at"] = occurred_at

    validate_delegation(successor)
    result_hash = _canonical_hash(successor)
    event = {
        "accept": "delegation_created",
        "narrow": "delegation_revised",
        "expand": "delegation_revised",
        "reject": "delegation_revised",
        "revoke": "delegation_revoked",
        "expire": "delegation_expired",
    }[transition]
    receipt = {
        "schema_version": "0.1",
        "transition": transition,
        "event": event,
        "delegation_id": policy["delegation_id"],
        "source_policy_sha256": source_hash,
        "result_policy_sha256": result_hash,
        "actor": actor,
        "reason": reason,
        "occurred_at": occurred_at,
        "user_accepted": user_accepted,
        "requested_change": deepcopy(requested_change),
    }
    return successor, receipt
