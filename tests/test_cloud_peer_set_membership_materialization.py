from copy import deepcopy
import pytest

from runtime.cloud_peer_set_membership_materialization import (
    CloudPeerSetMembershipMaterializationError,
    materialize_existing_cloud_peer,
    verify_materialization,
)

CLOUD="kvi_a31335d2cc3745fa987b635432cfed2c"


def readiness():
    return {
        "schema":"stegverse.kv.cloud-peer-adoption-materialization-readiness/v1",
        "source_site_request_id":"SITE-CLOUD-KV-4347408852127319cbda574f02e03edb",
        "existing_cloud_instance_id":CLOUD,
        "requested_instance_number":2,
        "requested_logical_name":"KV #2",
        "provider_id":"google-drive",
        "provider_connect_verified":True,
        "materialization_ready":True,
        "materialization_mode":"SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY",
        "cloud_identity_rewrite_required":False,
        "private_content_rewrite_authorized":False,
        "relationship_tier_after_materialization":"NOT_CONNECTED",
        "missing_evidence":[],
        "credential_material_present":False,
        "authority_effect":"NONE_READINESS_ONLY",
        "activation_effect":False,
    }


def test_preserves_existing_cloud_identity_and_ordinal():
    value=materialize_existing_cloud_peer(readiness=readiness(),expected_existing_instance_id=CLOUD,kv_set_id="personal",existing_instances=[{"instance_id":"kvi_device","instance_number":1,"kv_set_id":"personal"}],connect_receipt_ref="receipt://connect",verify_receipt_ref="receipt://verify")
    assert value["instance_id"]==CLOUD
    assert value["instance_number"]==2
    assert value["cloud_identity_preserved"] is True
    assert value["relationship_tier"]=="NOT_CONNECTED"
    assert value["credential_material_present"] is False
    verify_materialization(value)


def test_refuses_before_connect_and_verify_are_admitted():
    r=readiness(); r["materialization_ready"]=False
    with pytest.raises(CloudPeerSetMembershipMaterializationError,match="materialization_not_ready"):
        materialize_existing_cloud_peer(readiness=r,expected_existing_instance_id=CLOUD,kv_set_id="personal",existing_instances=[],connect_receipt_ref="receipt://connect",verify_receipt_ref="receipt://verify")


def test_refuses_kv2_ordinal_collision():
    with pytest.raises(CloudPeerSetMembershipMaterializationError,match="kv2_ordinal_collision"):
        materialize_existing_cloud_peer(readiness=readiness(),expected_existing_instance_id=CLOUD,kv_set_id="personal",existing_instances=[{"instance_id":"kvi_other","instance_number":2,"kv_set_id":"personal"}],connect_receipt_ref="receipt://connect",verify_receipt_ref="receipt://verify")


def test_refuses_cloud_identity_rewrite_semantics():
    r=readiness(); r["cloud_identity_rewrite_required"]=True
    with pytest.raises(CloudPeerSetMembershipMaterializationError,match="cloud_identity_rewrite_forbidden"):
        materialize_existing_cloud_peer(readiness=r,expected_existing_instance_id=CLOUD,kv_set_id="personal",existing_instances=[],connect_receipt_ref="receipt://connect",verify_receipt_ref="receipt://verify")


def test_verifier_rejects_mutated_materialization():
    value=materialize_existing_cloud_peer(readiness=readiness(),expected_existing_instance_id=CLOUD,kv_set_id="personal",existing_instances=[],connect_receipt_ref="receipt://connect",verify_receipt_ref="receipt://verify")
    mutated=deepcopy(value); mutated["instance_number"]=3
    with pytest.raises(CloudPeerSetMembershipMaterializationError,match="materialization_digest_mismatch"):
        verify_materialization(mutated)
