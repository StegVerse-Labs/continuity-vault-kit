"""Materialize an already-existing cloud KnowledgeVault into a KV set without changing its identity.

This consumes only already-admitted provider-operation evidence. It never authenticates
a provider, resolves SKAP plaintext, executes Google Drive, rewrites cloud content, or
grants relationship/transport authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

READINESS_SCHEMA = "stegverse.kv.cloud-peer-adoption-materialization-readiness/v1"
MATERIALIZATION_SCHEMA = "stegverse.kv.cloud-peer-set-membership-materialization/v1"

class CloudPeerSetMembershipMaterializationError(ValueError):
    pass


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise CloudPeerSetMembershipMaterializationError(reason)


def _digest(value: Mapping[str, Any]) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return "sha256:"+sha256(raw).hexdigest()


def materialize_existing_cloud_peer(
    *,
    readiness: Mapping[str, Any],
    expected_existing_instance_id: str,
    kv_set_id: str,
    existing_instances: Sequence[Mapping[str, Any]],
    connect_receipt_ref: str,
    verify_receipt_ref: str,
) -> dict[str, Any]:
    _require(readiness.get("schema")==READINESS_SCHEMA,"readiness_schema_invalid")
    _require(readiness.get("materialization_ready") is True,"materialization_not_ready")
    _require(readiness.get("provider_connect_verified") is True,"provider_connect_verify_not_proven")
    _require(readiness.get("provider_id")=="google-drive","provider_mismatch")
    _require(readiness.get("existing_cloud_instance_id")==expected_existing_instance_id,"existing_cloud_identity_mismatch")
    _require(isinstance(expected_existing_instance_id,str) and expected_existing_instance_id.startswith("kvi_"),"existing_cloud_identity_invalid")
    _require(readiness.get("requested_instance_number")==2,"requested_instance_number_invalid")
    _require(readiness.get("materialization_mode")=="SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY","materialization_mode_invalid")
    _require(readiness.get("cloud_identity_rewrite_required") is False,"cloud_identity_rewrite_forbidden")
    _require(readiness.get("private_content_rewrite_authorized") is False,"private_content_rewrite_forbidden")
    _require(readiness.get("relationship_tier_after_materialization")=="NOT_CONNECTED","initial_relationship_must_remain_not_connected")
    _require(readiness.get("credential_material_present") is False,"credential_material_forbidden")
    _require(readiness.get("authority_effect")=="NONE_READINESS_ONLY","readiness_authority_drift")
    _require(isinstance(kv_set_id,str) and bool(kv_set_id.strip()),"kv_set_id_required")
    _require(isinstance(connect_receipt_ref,str) and bool(connect_receipt_ref.strip()),"connect_receipt_ref_required")
    _require(isinstance(verify_receipt_ref,str) and bool(verify_receipt_ref.strip()),"verify_receipt_ref_required")

    for row in existing_instances:
        _require(isinstance(row,Mapping),"existing_instance_record_invalid")
        if row.get("kv_set_id")==kv_set_id and row.get("instance_number")==2 and row.get("instance_id")!=expected_existing_instance_id:
            raise CloudPeerSetMembershipMaterializationError("kv2_ordinal_collision")
        if row.get("instance_id")==expected_existing_instance_id:
            _require(row.get("instance_number") in (None,2),"existing_cloud_identity_bound_to_other_ordinal")
            _require(row.get("kv_set_id") in (None,kv_set_id),"existing_cloud_identity_bound_to_other_set")

    body={
        "schema":MATERIALIZATION_SCHEMA,
        "state":"EXISTING_CLOUD_PEER_BOUND_TO_KV_SET",
        "provider_id":"google-drive",
        "instance_id":expected_existing_instance_id,
        "instance_number":2,
        "logical_name":"KV #2",
        "kv_set_id":kv_set_id.strip(),
        "set_membership":"PEER",
        "relationship_tier":"NOT_CONNECTED",
        "cloud_identity_preserved":True,
        "cloud_identity_rewritten":False,
        "private_content_rewritten":False,
        "provider_connect_verified":True,
        "connect_receipt_ref":connect_receipt_ref,
        "verify_receipt_ref":verify_receipt_ref,
        "credential_material_present":False,
        "relationship_mutation_authorized":False,
        "data_moved":False,
        "replication_started":False,
        "ai_corpus_exposed":False,
        "credential_authority":"TV/TVC",
        "authority_effect":"NONE_SET_MEMBERSHIP_BINDING_ONLY",
        "activation_effect":False,
    }
    return {**body,"materialization_sha256":_digest(body)}


def verify_materialization(value: Mapping[str, Any]) -> None:
    _require(value.get("schema")==MATERIALIZATION_SCHEMA,"materialization_schema_invalid")
    _require(value.get("state")=="EXISTING_CLOUD_PEER_BOUND_TO_KV_SET","materialization_state_invalid")
    _require(value.get("cloud_identity_preserved") is True and value.get("cloud_identity_rewritten") is False,"cloud_identity_preservation_invalid")
    _require(value.get("private_content_rewritten") is False,"private_content_rewrite_detected")
    _require(value.get("relationship_tier")=="NOT_CONNECTED","relationship_tier_invalid")
    _require(value.get("credential_material_present") is False,"credential_material_forbidden")
    _require(value.get("credential_authority")=="TV/TVC","credential_authority_invalid")
    _require(value.get("authority_effect")=="NONE_SET_MEMBERSHIP_BINDING_ONLY" and value.get("activation_effect") is False,"materialization_authority_drift")
    body=dict(value); claimed=body.pop("materialization_sha256",None)
    _require(claimed==_digest(body),"materialization_digest_mismatch")
