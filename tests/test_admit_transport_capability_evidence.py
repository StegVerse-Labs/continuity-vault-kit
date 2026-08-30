import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "admit_transport_capability_evidence",
    ROOT / "scripts" / "admit_transport_capability_evidence.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)

FACTS = json.loads((ROOT / "specs" / "kv-activation-readiness-facts.v1.json").read_text(encoding="utf-8"))


def hf_evidence():
    return {
        "schema": module.HF_SCHEMA,
        "observation_class": "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE",
        "state": "OBSERVED",
        "node_registration": {"node_id": "stegnode-test", "device_continuity_id": "stegdevice-test", "state": "ESTABLISHED", "credential_authority": "TV/TVC"},
        "resident_receipt": {"state": "COMPLETE", "credential_used": False, "github_token_used": False, "authority_effect": "NONE"},
        "intr_receipt": {
            "state": "COMPLETE",
            "transport_profile": "stegverse.universal-intr.adjacent-hop/v1",
            "destination_validation": "PASS",
            "lineage_verified": True,
            "claims": {"credential_used": False, "runtime_activation_claimed": False, "production_interlock_runtime_activated": False},
            "authority_effect": "NONE",
        },
        "assertions": {
            "existing_node_reused": True,
            "new_node_identity_minted": False,
            "public_source_live_fetch": True,
            "exact_raw_bytes_hashed": True,
            "universal_intr_adjacent_hop_executed": True,
            "destination_validation": "PASS",
            "lineage_verified": True,
            "global_runtime_activation_claimed": False,
        },
        "journal_replay": {"state": "PASS"},
        "reconstruction_entry": {"receipt": {"state": "PASS", "same_execution": True}},
        "authority_effect": "NONE",
    }


def hf_canonical_evidence():
    return {
        "schema": module.HF_CANONICAL_SCHEMA,
        "state": "OBSERVED",
        "observation_class": "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE",
        "observed_at": "2026-08-29T23:39:43.780Z",
        "continuity_source": "LIVE_EXISTING_WEB_BOOTSTRAP",
        "source_bundle_sha256": "bce1baa1ee8db9e185f0e40673187ba0d7ef3ed47e8c1981ec9eae5d6c3cc2f0",
        "node_id": "stegnode-test",
        "device_continuity_id": "stegdevice-test",
        "resident_task_id": "SV-DN1-RESIDENT-OBSERVER-001",
        "claim_id": "SV-DN1-stegnode-test-G5",
        "fencing_token": 5,
        "resident_state": "COMPLETE",
        "source_url": "https://huggingface.co/api/models/Qwen/Qwen3-8B",
        "source_http_status": 200,
        "raw_response_sha256": "sha256:" + "b" * 64,
        "semantic_exchange_id": "sha256:" + "4" * 64,
        "source_transform_hash": "sha256:" + "a" * 64,
        "intr_receipt_hash": "sha256:" + "e" * 64,
        "transport_profile": "stegverse.universal-intr.adjacent-hop/v1",
        "universal_intr_policy_id": "STEGVERSE-UNIVERSAL-INTR-TRANSPORT-001",
        "boundary_from": "EXTERNAL_SYSTEM",
        "boundary_to": "STEGOS_ECOSYSTEM",
        "destination_validation": "PASS",
        "lineage_verified": True,
        "journal_replay_state": "PASS",
        "journal_entries": 26,
        "journal_tail_sha256": "8" * 64,
        "existing_node_reused": True,
        "new_node_identity_minted": False,
        "credential_used": False,
        "github_token_used": False,
        "sdk_admitted": False,
        "runtime_activation_claimed": False,
        "production_interlock_runtime_activated": False,
        "authority_effect": "NONE",
        "validation": {
            "journal_receipt_hashes": "PASS",
            "journal_entry_hashes": "PASS",
            "journal_previous_hash_chain": "PASS",
            "claim_terminal_link": "PASS",
            "terminal_reconstruction_link": "PASS",
            "reconstruction_same_execution": "PASS",
            "interlock_intr_previous_receipt_hash": "PASS",
            "intr_exchange_identity": "PASS",
            "resident_exchange_identity": "PASS",
            "resident_raw_digest_identity": "PASS",
        },
    }


def hil_evidence():
    digest = "sha256:" + "a" * 64
    return {
        "schema": module.HIL_SCHEMA,
        "state": "OBSERVED",
        "observation_class": "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE",
        "node_id": "stegnode-test",
        "device_continuity_id": "stegdevice-test",
        "existing_node_reused": True,
        "new_node_identity_minted": False,
        "credential_used": False,
        "github_token_used": False,
        "participant_research_submission": False,
        "runtime_activation_claimed": False,
        "exact_byte_reconstruction": "PASS",
        "custody_state": "EXACT_BYTES_PERSISTED",
        "registry_state": "RECORDED",
        "journal_replay_state": "PASS",
        "next_required_transition": "HIL_CUSTODY_TVC_INTERLOCK_ADMISSION",
        "tvc_lifecycle_intent_observed": True,
        "tvc_receiving_receipt_observed": False,
        "receiver_restart_reconstruction_observed": False,
        "controlled_pdf_sha256": digest,
        "retrieved_pdf_sha256": digest,
        "receiver_receipt_id": "HIL-RECEIPT-test",
        "submission_id": "HIL-SUBMISSION-test",
        "intr_chain_hash": "sha256:" + "b" * 64,
        "device_stegos_ingress_receipt_hash": "sha256:" + "c" * 64,
        "hil_custody_receipt_hash": "sha256:" + "d" * 64,
        "journal_tail_sha256": "e" * 64,
        "validation": {
            "journal_receipt_hashes": "PASS",
            "journal_entry_hashes": "PASS",
            "journal_previous_hash_chain": "PASS",
            "claim_terminal_link": "PASS",
            "terminal_reconstruction_link": "PASS",
            "intr_receipt_chain": "PASS",
            "exact_byte_retrieval": "PASS",
        },
        "authority_effect": "NONE",
    }


def test_hf_admission_advances_only_adjacent_external_api_egress():
    updated, admission = module.admit(hf_evidence(), FACTS)
    assert admission["capability_type"] == "ADJACENT_EXTERNAL_API_EGRESS"
    assert admission["facts_advanced"] == ["transport_capabilities_observed.ADJACENT_EXTERNAL_API_EGRESS"]
    assert admission["unrelated_facts_advanced"] == []
    assert admission["activation_performed"] is False
    assert admission["authority_effect"] == "NONE"
    before = FACTS["transport_capabilities_observed"]
    after = updated["transport_capabilities_observed"]
    for key, value in before.items():
        assert after[key] is (True if key == "ADJACENT_EXTERNAL_API_EGRESS" else value)


def test_hil_admission_advances_only_public_https_ingress():
    updated, admission = module.admit(hil_evidence(), FACTS)
    assert admission["capability_type"] == "PUBLIC_HTTPS_INGRESS"
    before = FACTS["transport_capabilities_observed"]
    after = updated["transport_capabilities_observed"]
    for key, value in before.items():
        assert after[key] is (True if key == "PUBLIC_HTTPS_INGRESS" else value)


def test_hil_ingress_capability_requires_downstream_tvc_receipt_to_remain_unobserved():
    evidence = hil_evidence()
    assert evidence["tvc_receiving_receipt_observed"] is False
    updated, admission = module.admit(evidence, FACTS)
    assert updated["transport_capabilities_observed"]["PUBLIC_HTTPS_INGRESS"] is True
    assert admission["activation_performed"] is False
    evidence["tvc_receiving_receipt_observed"] = True
    with pytest.raises(ValueError, match="must remain unobserved"):
        module.admit(evidence, FACTS)


def test_hil_fails_closed_on_runtime_activation_claim():
    evidence = hil_evidence()
    evidence["runtime_activation_claimed"] = True
    with pytest.raises(ValueError, match="runtime activation"):
        module.admit(evidence, FACTS)


def test_hil_fails_closed_on_participant_research_submission():
    evidence = hil_evidence()
    evidence["participant_research_submission"] = True
    with pytest.raises(ValueError, match="participant research submission"):
        module.admit(evidence, FACTS)


def test_hil_fails_closed_on_digest_identity_drift():
    evidence = hil_evidence()
    evidence["retrieved_pdf_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError, match="digest identity mismatch"):
        module.admit(evidence, FACTS)


def test_hil_fails_closed_on_validation_drift():
    evidence = hil_evidence()
    evidence["validation"]["intr_receipt_chain"] = "FAIL"
    with pytest.raises(ValueError, match="intr_receipt_chain must PASS"):
        module.admit(evidence, FACTS)


def test_hf_fails_closed_if_observation_is_not_observed():
    evidence = hf_evidence()
    evidence["state"] = "NOT_OBSERVED"
    with pytest.raises(ValueError, match="must be OBSERVED"):
        module.admit(evidence, FACTS)


def test_hf_fails_closed_on_new_node_identity():
    evidence = hf_evidence()
    evidence["assertions"]["new_node_identity_minted"] = True
    with pytest.raises(ValueError, match="may not mint"):
        module.admit(evidence, FACTS)


def test_hil_fails_closed_without_exact_byte_custody():
    evidence = hil_evidence()
    evidence["custody_state"] = "UNKNOWN"
    with pytest.raises(ValueError, match="exact bytes"):
        module.admit(evidence, FACTS)


def test_unsupported_schema_fails_closed():
    with pytest.raises(ValueError, match="unsupported"):
        module.admit({"schema": "unknown/v1"}, FACTS)


def test_source_facts_are_not_mutated_in_place():
    before = copy.deepcopy(FACTS)
    module.admit(hf_evidence(), FACTS)
    assert FACTS == before


def test_canonical_hf_admission_advances_only_adjacent_external_api_egress():
    updated, admission = module.admit(hf_canonical_evidence(), FACTS)
    assert admission["source_schema"] == module.HF_CANONICAL_SCHEMA
    assert admission["capability_type"] == "ADJACENT_EXTERNAL_API_EGRESS"
    assert updated["transport_capabilities_observed"]["ADJACENT_EXTERNAL_API_EGRESS"] is True
    for key, value in FACTS["transport_capabilities_observed"].items():
        if key != "ADJACENT_EXTERNAL_API_EGRESS":
            assert updated["transport_capabilities_observed"][key] is value


def test_canonical_hf_fails_closed_on_validation_drift():
    evidence = hf_canonical_evidence()
    evidence["validation"]["terminal_reconstruction_link"] = "FAIL"
    with pytest.raises(ValueError, match="terminal_reconstruction_link must PASS"):
        module.admit(evidence, FACTS)


def test_canonical_hf_fails_closed_on_transport_profile_drift():
    evidence = hf_canonical_evidence()
    evidence["transport_profile"] = "other/v1"
    with pytest.raises(ValueError, match="transport profile mismatch"):
        module.admit(evidence, FACTS)
