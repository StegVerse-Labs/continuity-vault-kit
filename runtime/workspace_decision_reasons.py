"""Plain-language reasons for WorkSpace session and assistant-binding decisions.

Feeds the universal user-facing explanation contract (stegverse.user-facing-explanation/v1,
StegVerse-Labs/.github#3106): each decision of runtime/workspace_session_authentication.py and
runtime/workspace_assistant_binding.py carries an ``explanation_record`` whose ``why`` says, in words a
person can act on, why that predicate holds. Without it an explanation can only restate the predicate
("the prerequisite named by KV_OWNERSHIP_IS_NOT_AUTHENTICATION is not established").

Reasons are explanatory only. They never change a disposition or a predicate, and the canonical
decision fields remain the only authority. Site mirrors the same text in
assets/workspace-session-authentication.js and assets/workspace-assistant-binding.js (REASONS); the
tests compare them when a Site checkout is present.
"""
from __future__ import annotations

from typing import Any

SESSION_REQUESTED_ACTION = "Sign in to this WorkSpace"
BINDING_REQUESTED_ACTION = "Show your MyKV assistant in this WorkSpace"
OWNING_GOAL = "STEGVERSE-WORKSPACE-ANY-DEVICE-KV-SURFACE-001"
RETRY_ENTRYPOINTS = {
    SESSION_REQUESTED_ACTION: "continuity-vault-kit runtime/workspace_session_authentication.py resolve_session_authentication",
    BINDING_REQUESTED_ACTION: "continuity-vault-kit runtime/workspace_assistant_binding.py resolve_assistant_binding",
}

SESSION_REASONS: dict[str, str] = {
    "SESSION_PRINCIPAL_UNAUTHENTICATED": "this page has no signed-in identity for you, so it cannot tell who is asking",
    "KV_OWNERSHIP_IS_NOT_AUTHENTICATION": "holding or owning a KnowledgeVault projection does not prove who is signed in; only a sign-in receipt does",
    "DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION": "a registered device or node shows which machine is connected, not which person is signed in",
    "BROWSER_STATE_IS_NOT_AUTHENTICATION": "values kept in the browser, the page address or startup data can be changed by anyone, so they never prove who is signed in",
    "SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION": "the identity offered to this page did not come from a sign-in receipt, which is the only accepted source",
    "SESSION_AUTHENTICATION_RECEIPT_ABSENT": "the sign-in did not include its authentication receipt",
    "SESSION_NOT_AUTHENTICATED": "the sign-in receipt says the sign-in did not succeed",
    "SESSION_CREDENTIAL_AUTHORITY_INVALID": "the sign-in receipt was not issued by TV/TVC, the only credential authority this ecosystem accepts",
    "SESSION_AUTHENTICATION_RECEIPT_REF_ABSENT": "the sign-in receipt has no locator, so nobody can check it later",
    "SESSION_AUTHENTICATION_PRINCIPAL_MISMATCH": "the sign-in receipt belongs to a different identity than the one making this request",
    "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY": "the sign-in receipt claims the power to authorize, execute or delegate actions, and a sign-in can never grant that",
    "CALLER_AUTHENTICATION_RECEIPT_PRESENT": "a sign-in receipt from TV/TVC naming you was supplied; it is accepted as reported, and this check does not verify it itself",
}

BINDING_REASONS: dict[str, str] = {
    "SESSION_PRINCIPAL_UNAUTHENTICATED": "there is no signed-in identity, so there is nobody whose assistant could be shown",
    "ORG_KV_ASSISTANT_CONTEXT_NOT_OBSERVED": "an organization workspace needs that organization's own KnowledgeVault projection, which has not been observed, and your personal one is never reused for it",
    "PROJECTION_SCHEMA_INVALID": "the KnowledgeVault projection is missing or is not in the personal workspace format",
    "PROJECTION_AUTHORITY_INVALID": "the projection claims to be something other than a read-only personal workspace view",
    "PROJECTION_METADATA_INVALID": "the projection lacks the details that say whose it is and when it was observed",
    "WORKSPACE_GRANT_REVOKED": "access to this workspace has been revoked",
    "PROJECTION_OWNER_UNBOUND": "the projection does not say who owns it",
    "PROJECTION_OWNER_MISMATCH": "the projection belongs to someone other than the signed-in person",
    "PROJECTION_WORKSPACE_MISMATCH": "the projection is for a different workspace than the one you opened",
    "MYKV_ASSISTANT_BINDING_ABSENT": "your KnowledgeVault has no MyKV assistant recorded, and a generic assistant is never put in its place",
    "MYKV_ASSISTANT_RECORD_INVALID": "the assistant recorded in your KnowledgeVault is incomplete or is not marked as your workspace assistant",
    "MYKV_ASSISTANT_IS_SESSION_PRINCIPAL": "the assistant record names you yourself, and a person cannot be their own assistant",
    "PROJECTION_PRINCIPALS_INVALID": "the list of people and entities in the projection is malformed",
    "MYKV_ASSISTANT_AMBIGUOUS": "more than one assistant is recorded for you, and one is never chosen silently",
    "RELATIONSHIP_DECLARATION_INVALID": "the declared relationship between you and your assistant is malformed",
    "RELATIONSHIP_PARTIES_MISMATCH": "the declared relationship names a different person or assistant",
    "RELATIONSHIP_NOT_ACTIVE": "the declared relationship between you and your assistant is not active",
    "MYKV_ASSISTANT_BOUND": "this session resolved to your one MyKV assistant; that lets the page show it, not invoke it or act for you",
}


def explanation_record(disposition: str, predicate: str, reasons: dict[str, str], requested_action: str) -> dict[str, Any]:
    """Input for the explanation builder.

    Task Registry invariant (semantics.actions_by_manifest): every transition, ALLOW or not, is recorded by a
    receipt, and ALLOW without its receipt does not exist. These decisions accept caller-supplied fields and hold
    no receipt, so an ALLOW decision is explained as UNKNOWN to this surface (receipt not held), never as ALLOW and
    never as an authorized-but-unverified state. Refusals keep their own disposition. The decision itself is
    unchanged."""
    held = disposition in ("ALLOW", "UNKNOWN")
    record: dict[str, Any] = {
        "disposition": "UNKNOWN" if held else disposition,
        "predicate": predicate,
        "requested_action": requested_action,
        "authority_source": "NONE",
        "consequence_observation": "UNKNOWN" if held else "NOT_AUTHENTICALLY_OBSERVED",
    }
    if predicate in reasons:
        record["why"] = reasons[predicate]
    # Organization Role conformance standard (.github docs/ORGANIZATION_ROLE_RUNTIME_REALITY_DEPLOYMENT.md, item 5):
    # every non-ALLOW result carries these six fields; a bare UNKNOWN or FAIL_CLOSED is not a finding.
    entrypoint = RETRY_ENTRYPOINTS.get(requested_action, "the WorkSpace session sign-in")
    record.update({
        "failure_code": predicate,
        "failed_predicate": predicate,
        "required_evidence_or_repair": (
            "a receipt for this decision, located by its reference and verified through TV/TVC; this surface holds none"
            if held else
            "the condition named by " + predicate + " is established by its owner" + (": " + reasons[predicate] + " today" if predicate in reasons else "")
        ),
        "retry_entrypoint": entrypoint,
        "owning_existing_goal": OWNING_GOAL,
        "next_attempt": "the next '" + requested_action + "' request is decided again from the session it presents; nothing waits",
    })
    return record
