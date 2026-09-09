from __future__ import annotations

import copy

import pytest

from runtime.cloud_peer_adoption_provider_binding import (
    CloudPeerAdoptionProviderBindingError,
    build_provider_binding,
    evaluate_materialization_readiness,
)

REQUEST_ID = "SITE-CLOUD-KV-4347408852127319cbda574f02e03edb"
CLOUD_ID = "kvi_a31335d2cc3745fa987b635432cfed2c"
RESIDENT_ID = "kvi_0d5d4cfd531db51bbcf7fdfc0311f5dc"


def site_request():
    return {
        "schema":"stegverse.site.cloud-kv-peer-adoption-request/v1",
        "operation":"ADOPT_EXISTING_CLOUD_KV_PEER",
        "request_id":REQUEST_ID,
        "resident_instance_id":RESIDENT_ID,
        "resident_instance_number":1,
        "existing_instance_id":CLOUD_ID,
        "kv_set_id":"personal",
        "requested_instance_number":2,
        "requested_logical_name":"KV #2",
        "storage_medium":"google-drive",
        "initial_relationship_tier":"NOT_CONNECTED",
        "governance_state":"PENDING_INTERLOCK_INTR",
        "credential_material_present":False,
        "provider_operation_authorized":False,
        "instance_materialized":False,
        "relationship_mutation_authorized":False,
        "data_moved":False,
        "replication_started":False,
        "ai_corpus_exposed":False,
        "private_content_rewrite_authorized":False,
        "existing_identity_rewrite_authorized":False,
    }


def ingress():
    return {
        "request_id":REQUEST_ID,
        "governance_state":"PENDING_INTERLOCK_INTR",
        "resident_ingress_observed":True,
        "instance_materialized":False,
        "provider_operation_authorized":False,
    }


def admitted(request, operation):
    return {
        "schema":"stegverse.kv.storage-provider-operation-receipt/v1",
        "request_id":request["request_id"],
        "instance_id":request["instance_id"],
        "kv_set_id":request["kv_set_id"],
        "provider_id":"google-drive",
        "operation":operation,
        "governance_state":"ADMITTED",
        "provider_operation_executed":True,
        "data_moved":False,
        "replication_started":False,
        "interlock_receipt_ref":f"interlock:{operation.lower()}:receipt",
        "intr_receipt_ref":f"intr:{operation.lower()}:receipt",
        "skap_credential_ref":"skap:google-drive:credential-ref",
        "provider_result_ref":f"provider:google-drive:{operation.lower()}:result",
        "authority_effect":"NONE",
        "credential_material_present":False,
    }


def test_owner_ingress_binds_to_canonical_connect_verify_requests():
    value = build_provider_binding(
        site_request=site_request(), resident_ingress_evidence=ingress(),
        private_storage_locator="Google Drive:/KnowledgeVault",
    )
    assert value["source_site_request_id"] == REQUEST_ID
    assert value["existing_cloud_instance_id"] == CLOUD_ID
    assert value["requested_instance_number"] == 2
    assert value["provider_id"] == "google-drive"
    assert value["connect_request"]["operation"] == "CONNECT"
    assert value["verify_request"]["operation"] == "VERIFY"
    assert value["connect_request"]["object_ref"] == REQUEST_ID
    assert value["connect_request"]["governance_state"] == "PENDING_INTERLOCK_INTR"
    assert value["connect_request"]["provider_operation_executed"] is False
    assert value["verify_request"]["provider_operation_executed"] is False
    assert value["instance_materialization_authorized"] is False
    assert value["cloud_identity_rewrite_required"] is False
    assert value["credential_material_present"] is False


def test_missing_provider_results_remain_not_ready():
    binding = build_provider_binding(
        site_request=site_request(), resident_ingress_evidence=ingress(),
        private_storage_locator="Google Drive:/KnowledgeVault",
    )
    readiness = evaluate_materialization_readiness(binding=binding)
    assert readiness["materialization_ready"] is False
    assert readiness["missing_evidence"] == [
        "ADMITTED_GOOGLE_DRIVE_CONNECT_RESULT",
        "ADMITTED_GOOGLE_DRIVE_VERIFY_RESULT",
    ]


def test_connect_and_verify_receipts_make_readiness_true_without_rewrite():
    binding = build_provider_binding(
        site_request=site_request(), resident_ingress_evidence=ingress(),
        private_storage_locator="Google Drive:/KnowledgeVault",
    )
    readiness = evaluate_materialization_readiness(
        binding=binding,
        connect_receipt=admitted(binding["connect_request"], "CONNECT"),
        verify_receipt=admitted(binding["verify_request"], "VERIFY"),
    )
    assert readiness["materialization_ready"] is True
    assert readiness["provider_connect_verified"] is True
    assert readiness["materialization_mode"] == "SET_MEMBERSHIP_ORDINAL_BINDING_PRESERVE_CLOUD_IDENTITY"
    assert readiness["cloud_identity_rewrite_required"] is False
    assert readiness["relationship_tier_after_materialization"] == "NOT_CONNECTED"
    assert readiness["authority_effect"] == "NONE_READINESS_ONLY"


@pytest.mark.parametrize("field,value", [
    ("provider_operation_authorized", True),
    ("instance_materialized", True),
    ("credential_material_present", True),
    ("existing_identity_rewrite_authorized", True),
    ("private_content_rewrite_authorized", True),
])
def test_source_overclaims_fail_closed(field, value):
    request = site_request()
    request[field] = value
    with pytest.raises(CloudPeerAdoptionProviderBindingError):
        build_provider_binding(
            site_request=request, resident_ingress_evidence=ingress(),
            private_storage_locator="Google Drive:/KnowledgeVault",
        )


def test_receipt_missing_interlock_intr_skap_or_provider_result_fails_closed():
    binding = build_provider_binding(
        site_request=site_request(), resident_ingress_evidence=ingress(),
        private_storage_locator="Google Drive:/KnowledgeVault",
    )
    good_connect = admitted(binding["connect_request"], "CONNECT")
    good_verify = admitted(binding["verify_request"], "VERIFY")
    for field in ("interlock_receipt_ref", "intr_receipt_ref", "skap_credential_ref", "provider_result_ref"):
        bad = copy.deepcopy(good_connect)
        bad[field] = ""
        with pytest.raises(CloudPeerAdoptionProviderBindingError):
            evaluate_materialization_readiness(binding=binding, connect_receipt=bad, verify_receipt=good_verify)
