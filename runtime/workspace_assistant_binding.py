"""WorkSpace -> MyKV AI Assistant identity and continuity binding (Site#1509 W4).

Pure and storage-free. The WorkSpace assistant IS the user's existing MyKV AI Assistant: the single
AI_ENTITY principal with role WORKSPACE_ASSISTANT that the authenticated Personal KV Workspace
projection (runtime/workspace_projection.py) carries in ``assistant``. This module decides whether an
authenticated WorkSpace session may resolve to that assistant and returns
``stegverse.kv.workspace-assistant-binding/v1``. It never creates, renames or substitutes an assistant,
never falls back to a generic LLM, and grants no invocation, inference, credential or action authority:
consequential actions still need the admitted manifest route and an actual ALLOW. No assistant
invocation route or StegBrowser ephemeral-inference consent contract exists yet, so both are reported
NOT_AVAILABLE rather than assumed.
"""
from __future__ import annotations

from typing import Any

from delegation.relationship import RelationshipDeclarationError, validate_relationship_declaration
from runtime.workspace_continuity_checkpoint import CHECKPOINT_SCHEMA

BINDING_SCHEMA = "stegverse.kv.workspace-assistant-binding/v1"
PROJECTION_SCHEMA = "stegverse.kv.personal-workspace-projection/v1"
METADATA_SCHEMA = "stegverse.kv.workspace-projection-metadata/v1"
ASSISTANT_ROLE = "WORKSPACE_ASSISTANT"


def _decision(disposition: str, predicate: str, binding: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "disposition": disposition,
        "predicate": predicate,
        "binding": binding,
        "generic_llm_fallback": "FORBIDDEN",
        "action_eligible": False,
        "authority_effect": "NONE",
    }


def _is_assistant(row: Any) -> bool:
    return isinstance(row, dict) and row.get("principal_type") == "AI_ENTITY" and isinstance(row.get("roles"), list) and ASSISTANT_ROLE in row["roles"]


def resolve_assistant_binding(
    projection: Any,
    *,
    principal_id: str,
    workspace_type: str,
    workspace_id: str | None,
    relationship_declaration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the authenticated session (principal_id, workspace_type, workspace_id) to its MyKV assistant.

    The caller supplies the session context from its own authentication; projection fields never
    establish who the user is. ALLOW here means only "this WorkSpace session shows that assistant";
    it is not permission to invoke it or to act.
    """
    if not isinstance(principal_id, str) or not principal_id:
        return _decision("FAIL_CLOSED", "SESSION_PRINCIPAL_UNAUTHENTICATED")
    if workspace_type != "PERSONAL":
        # Org context changes data and action scope, never assistant identity; it needs a distinct
        # authenticated Org-KV projection, and Personal KV is never reused for it.
        return _decision("FAIL_CLOSED", "ORG_KV_ASSISTANT_CONTEXT_NOT_OBSERVED")
    if not isinstance(projection, dict) or projection.get("schema") != PROJECTION_SCHEMA:
        return _decision("FAIL_CLOSED", "PROJECTION_SCHEMA_INVALID")
    if projection.get("workspace_type") != "PERSONAL" or projection.get("authority_effect") != "NONE" or projection.get("workspace_grants_authority") is not False:
        return _decision("FAIL_CLOSED", "PROJECTION_AUTHORITY_INVALID")
    meta = projection.get("projection_metadata")
    if not isinstance(meta, dict) or meta.get("schema") != METADATA_SCHEMA:
        return _decision("FAIL_CLOSED", "PROJECTION_METADATA_INVALID")
    if meta.get("grant_state") == "REVOKED":
        return _decision("DENY", "WORKSPACE_GRANT_REVOKED")
    owner = meta.get("owner_principal_id")
    if not isinstance(owner, str) or not owner:
        return _decision("FAIL_CLOSED", "PROJECTION_OWNER_UNBOUND")
    if owner != principal_id:
        return _decision("DENY", "PROJECTION_OWNER_MISMATCH")
    if meta.get("workspace_id") != workspace_id:
        return _decision("DENY", "PROJECTION_WORKSPACE_MISMATCH")
    assistant = projection.get("assistant")
    if assistant is None:
        return _decision("FAIL_CLOSED", "MYKV_ASSISTANT_BINDING_ABSENT")
    if not _is_assistant(assistant) or not isinstance(assistant.get("principal_id"), str) or not assistant["principal_id"]:
        return _decision("FAIL_CLOSED", "MYKV_ASSISTANT_RECORD_INVALID")
    assistant_id = assistant["principal_id"]
    if assistant_id == principal_id:
        return _decision("FAIL_CLOSED", "MYKV_ASSISTANT_IS_SESSION_PRINCIPAL")
    principals = projection.get("principals") or []
    if not isinstance(principals, list):
        return _decision("FAIL_CLOSED", "PROJECTION_PRINCIPALS_INVALID")
    others = {row.get("principal_id") for row in principals if _is_assistant(row)} - {assistant_id}
    if others:
        # One user, one assistant identity: a second candidate is never silently chosen.
        return _decision("FAIL_CLOSED", "MYKV_ASSISTANT_AMBIGUOUS")
    relationship_state = "NOT_SUPPLIED"
    relationship_id = None
    if relationship_declaration is not None:
        try:
            validate_relationship_declaration(relationship_declaration)
        except (RelationshipDeclarationError, AttributeError, KeyError, TypeError):
            return _decision("FAIL_CLOSED", "RELATIONSHIP_DECLARATION_INVALID")
        parties = (relationship_declaration["principal"].get("entity_id"), relationship_declaration["ai_entity"].get("entity_id"))
        if parties != (principal_id, assistant_id):
            return _decision("DENY", "RELATIONSHIP_PARTIES_MISMATCH")
        if relationship_declaration["status"] != "active":
            return _decision("DENY", "RELATIONSHIP_NOT_ACTIVE")
        relationship_state, relationship_id = "ACTIVE_DECLARED", relationship_declaration["relationship_id"]
    return _decision("ALLOW", "MYKV_ASSISTANT_BOUND", {
        "assistant_principal_id": assistant_id,
        "assistant_display_name": assistant.get("display_name"),
        "ai_label_required": True,
        "owner_principal_id": owner,
        "workspace_type": "PERSONAL",
        "workspace_id": workspace_id,
        "continuity": {
            # Continuity is keyed by (owner, assistant, workspace), never by device or page session.
            "key": {"owner_principal_id": owner, "assistant_principal_id": assistant_id, "workspace_id": workspace_id},
            "source_revision": meta.get("source_revision"),
            "provenance_ref": meta.get("provenance_ref"),
            "observed_at": meta.get("observed_at"),
            "checkpoint_schema": CHECKPOINT_SCHEMA,
            "replay_status": "UNKNOWN",
        },
        "grant_state": meta.get("grant_state") if isinstance(meta.get("grant_state"), str) else "UNKNOWN",
        "relationship_state": relationship_state,
        "relationship_id": relationship_id,
        "invocation_route": "NOT_AVAILABLE",
        "ephemeral_inference": "NOT_AVAILABLE",
    })
