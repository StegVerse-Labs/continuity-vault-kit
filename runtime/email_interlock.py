"""Email-continuity specialization for the canonical KV-INTERLOCK-v1 request contract."""

from __future__ import annotations

from runtime.email_continuity import EmailAccountMapping, EmailMappingError


def _base_request(
    *,
    operation: str,
    request_id: str,
    purpose: str,
    authority_ref: str,
    requested_scope: list[str],
    mapping: EmailAccountMapping,
) -> dict:
    if mapping.mapping_state == "REVOKED":
        raise EmailMappingError("revoked email mapping cannot request Interlock admission")
    if not request_id or not authority_ref:
        raise EmailMappingError("request_id and authority_ref are required")
    return {
        "schema_version": "kv.interlock.request.v1",
        "operation": operation,
        "request_id": request_id,
        "requester": {
            "module": "email-continuity",
            "component": "governed-ingress",
        },
        "purpose": purpose,
        "record_class": "email-continuity",
        "requested_scope": requested_scope,
        "minimum_necessary_justification": (
            f"Govern mailbox mapping {mapping.mapping_id} without disclosing mailbox secrets."
        ),
        "authority_ref": authority_ref,
        "disclosure_mode": "SOURCE_REFERENCE_ONLY",
    }


def build_ingress_discovery_request(
    *,
    request_id: str,
    authority_ref: str,
    mapping: EmailAccountMapping,
) -> dict:
    return _base_request(
        operation="DISCOVER",
        request_id=request_id,
        purpose="email.ingress.discover",
        authority_ref=authority_ref,
        requested_scope=["email_mapping_state", "email_provider_state"],
        mapping=mapping,
    )


def build_ingress_evaluation_request(
    *,
    request_id: str,
    authority_ref: str,
    mapping: EmailAccountMapping,
) -> dict:
    if mapping.mapping_state != "SESSION_VERIFIED":
        raise EmailMappingError("ingress evaluation requires verified provider session")
    return _base_request(
        operation="REQUEST",
        request_id=request_id,
        purpose="email.ingress.evaluate",
        authority_ref=authority_ref,
        requested_scope=["email_message_metadata", "email_ingress_policy"],
        mapping=mapping,
    )


def build_projection_candidate_request(
    *,
    request_id: str,
    authority_ref: str,
    mapping: EmailAccountMapping,
    payload_ref: str,
    requested_destination: str = "03_Records/Email",
) -> dict:
    if mapping.mapping_state != "SESSION_VERIFIED":
        raise EmailMappingError("email projection candidate requires verified provider session")
    if not payload_ref.startswith("sha256:"):
        raise EmailMappingError("candidate payload_ref must be a sha256 reference")
    request = _base_request(
        operation="COMMIT_CANDIDATE",
        request_id=request_id,
        purpose="email.ingress.project-admitted",
        authority_ref=authority_ref,
        requested_scope=["email_projection_candidate"],
        mapping=mapping,
    )
    request["candidate_writeback"] = {
        "candidate_type": "email_admitted_projection",
        "payload_ref": payload_ref,
        "requested_destination": requested_destination,
    }
    return request
