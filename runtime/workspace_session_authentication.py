"""WorkSpace session-authentication contract: stegverse.workspace.session-authentication/v1.

Producer-side mirror of Site assets/workspace-session-authentication.js (Site#1509 W4), with the same
predicates in the same order, so the reference implementation and the Site consumer admit a session
principal identically before it reaches resolve_assistant_binding.

The contract takes the caller's session only. The KV projection is never an input, so KV ownership
data (projection_metadata.owner_principal_id, workspace.owner_principal_id, principals[]) can never
become the caller. Device registration proves a node, browser or process state proves nothing, and a
bare principal_id without a caller-authentication receipt is refused.

ALLOW is an informational acceptance of caller-supplied receipt fields: this module performs no TV/TVC
verification (verification CALLER_SUPPLIED_NOT_PAGE_VERIFIED), so no decision here is runtime
authentication evidence (runtime_authentication_evidence False) and none raises action eligibility.
"""
from __future__ import annotations

from typing import Any

from runtime.workspace_decision_reasons import SESSION_REASONS, SESSION_REQUESTED_ACTION, explanation_record

SESSION_AUTHENTICATION_SCHEMA = "stegverse.workspace.session-authentication/v1"
RECEIPT_SOURCE_CLASS = "CALLER_AUTHENTICATION_RECEIPT"
CREDENTIAL_AUTHORITY = "TV/TVC"

# Source classes that are never authentication, each with the predicate that names why.
NON_AUTHENTICATION_SOURCES: dict[str, str] = {
    "NO_AUTHENTICATED_SESSION_PRINCIPAL": "SESSION_PRINCIPAL_UNAUTHENTICATED",
    "KV_PROJECTION_OWNER": "KV_OWNERSHIP_IS_NOT_AUTHENTICATION",
    "KV_PROJECTION_METADATA": "KV_OWNERSHIP_IS_NOT_AUTHENTICATION",
    "KV_PROJECTION_PRINCIPAL": "KV_OWNERSHIP_IS_NOT_AUTHENTICATION",
    "KV_WORKSPACE_CONTEXT": "KV_OWNERSHIP_IS_NOT_AUTHENTICATION",
    "DEVICE_REGISTRATION": "DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION",
    "STEGOS_NODE_REGISTRATION": "DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION",
    "BROWSER_STORAGE": "BROWSER_STATE_IS_NOT_AUTHENTICATION",
    "PAGE_STATE": "BROWSER_STATE_IS_NOT_AUTHENTICATION",
    "URL_PARAMETER": "BROWSER_STATE_IS_NOT_AUTHENTICATION",
    "BOOTSTRAP_DATA": "BROWSER_STATE_IS_NOT_AUTHENTICATION",
}


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def _decision(disposition: str, predicate: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": SESSION_AUTHENTICATION_SCHEMA,
        "disposition": disposition,
        "predicate": predicate,
        "session": session,
        "admission_class": "CALLER_SUPPLIED_FIELDS_ACCEPTED",
        "verification": "CALLER_SUPPLIED_NOT_PAGE_VERIFIED",
        "runtime_authentication_evidence": False,
        "identity_from_projection": False,
        "action_eligible": False,
        "authority_effect": "NONE",
        "explanation_record": explanation_record(disposition, predicate, SESSION_REASONS, SESSION_REQUESTED_ACTION),
    }


def resolve_session_authentication(session: Any) -> dict[str, Any]:
    """Decide whether a caller session may be handed to the MyKV assistant binding resolver.

    Same predicate order as the Site module. Only the session is read; projection, device and process
    state are never inputs.
    """
    s = session if isinstance(session, dict) else {}
    source_class = s.get("source_class") if isinstance(s.get("source_class"), str) else None
    principal_id = s.get("principal_id")
    if not _non_empty(principal_id) and (source_class is None or source_class == "NO_AUTHENTICATED_SESSION_PRINCIPAL"):
        return _decision("FAIL_CLOSED", "SESSION_PRINCIPAL_UNAUTHENTICATED")
    if source_class is not None and source_class in NON_AUTHENTICATION_SOURCES:
        return _decision("FAIL_CLOSED", NON_AUTHENTICATION_SOURCES[source_class])
    if source_class != RECEIPT_SOURCE_CLASS:
        return _decision("FAIL_CLOSED", "SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION")
    if not _non_empty(principal_id):
        return _decision("FAIL_CLOSED", "SESSION_PRINCIPAL_UNAUTHENTICATED")
    auth = s.get("authentication")
    if not isinstance(auth, dict):
        return _decision("FAIL_CLOSED", "SESSION_AUTHENTICATION_RECEIPT_ABSENT")
    if auth.get("authenticated") is not True:
        return _decision("FAIL_CLOSED", "SESSION_NOT_AUTHENTICATED")
    if auth.get("credential_authority") != CREDENTIAL_AUTHORITY:
        return _decision("FAIL_CLOSED", "SESSION_CREDENTIAL_AUTHORITY_INVALID")
    if not _non_empty(auth.get("receipt_ref")):
        return _decision("FAIL_CLOSED", "SESSION_AUTHENTICATION_RECEIPT_REF_ABSENT")
    if auth.get("principal_id") != principal_id:
        return _decision("FAIL_CLOSED", "SESSION_AUTHENTICATION_PRINCIPAL_MISMATCH")
    if (
        auth.get("transaction_authority") is True
        or auth.get("execution_authority") is True
        or auth.get("delegation_authority") is True
        or ("authority_effect" in auth and auth.get("authority_effect") != "NONE")
    ):
        return _decision("FAIL_CLOSED", "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY")
    workspace_id = s.get("workspace_id") if "workspace_id" in s else None
    return _decision(
        "ALLOW",
        "CALLER_AUTHENTICATION_RECEIPT_PRESENT",
        {
            "principal_id": principal_id,
            "workspace_id": workspace_id,
            "source_class": RECEIPT_SOURCE_CLASS,
            "receipt_ref": auth["receipt_ref"],
            "credential_authority": CREDENTIAL_AUTHORITY,
        },
    )
