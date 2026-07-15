"""Progressive delegation onboarding helpers.

These helpers produce proposals and readable profiles. They never activate authority.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def propose_standing_delegation(
    repeated_instruction: dict[str, Any],
    *,
    delegation_id: str,
    principal: dict[str, str],
    delegate: dict[str, str],
) -> dict[str, Any]:
    """Convert a repeated instruction pattern into a reviewable proposal.

    The returned status is always ``proposed``. User acceptance is a separate,
    explicit transition.
    """
    required = {"purpose", "actions", "resources", "destinations"}
    missing = sorted(required - repeated_instruction.keys())
    if missing:
        raise ValueError(f"missing repeated-instruction fields: {missing}")

    return {
        "schema_version": "0.1",
        "delegation_id": delegation_id,
        "principal": deepcopy(principal),
        "delegate": deepcopy(delegate),
        "authority_source": "standing_delegation",
        "purpose": repeated_instruction["purpose"],
        "scope": {
            "actions": list(repeated_instruction["actions"]),
            "resources": list(repeated_instruction["resources"]),
            "destinations": list(repeated_instruction["destinations"]),
            "constraints": deepcopy(repeated_instruction.get("constraints", {})),
            "exclusions": list(repeated_instruction.get("exclusions", [])),
        },
        "validity": {
            "starts_at": repeated_instruction["starts_at"],
            "expires_at": repeated_instruction.get("expires_at"),
            "revocable": True,
            "revoked_at": None,
            "revocation_reason": None,
        },
        "confirmation_policy": repeated_instruction.get(
            "confirmation_policy", "confirm_on_material_change"
        ),
        "escalation_rules": deepcopy(repeated_instruction.get("escalation_rules", [])),
        "receipt_policy": {
            "required": True,
            "events": [
                "delegation_created",
                "action_authorized",
                "action_completed",
                "action_failed",
                "escalation_requested",
                "delegation_revised",
                "delegation_revoked",
                "delegation_expired",
            ],
            "integrity_algorithm": "sha256",
        },
        "status": "proposed",
        "relationship_declaration_ref": repeated_instruction.get(
            "relationship_declaration_ref"
        ),
    }


def render_governance_profile(policies: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a user-readable, non-authoritative summary of current policies."""
    active = [p for p in policies if p.get("status") == "active"]
    proposed = [p for p in policies if p.get("status") == "proposed"]
    inactive = [p for p in policies if p.get("status") not in {"active", "proposed"}]

    def summarize(policy: dict[str, Any]) -> dict[str, Any]:
        return {
            "delegation_id": policy.get("delegation_id"),
            "purpose": policy.get("purpose"),
            "authority_source": policy.get("authority_source"),
            "actions": policy.get("scope", {}).get("actions", []),
            "destinations": policy.get("scope", {}).get("destinations", []),
            "confirmation_policy": policy.get("confirmation_policy"),
            "expires_at": policy.get("validity", {}).get("expires_at"),
            "status": policy.get("status"),
            "revocable": policy.get("validity", {}).get("revocable") is True,
        }

    return {
        "active_delegations": [summarize(p) for p in active],
        "proposed_changes": [summarize(p) for p in proposed],
        "inactive_delegations": [summarize(p) for p in inactive],
        "user_controls": ["accept", "narrow", "expand", "reject", "expire", "revoke"],
        "authority_note": "This profile describes authority; it does not grant authority.",
    }
