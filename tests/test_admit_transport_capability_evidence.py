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

FACTS = json.loads(
    (ROOT / "specs" / "kv-activation-readiness-facts.v1.json").read_text(encoding="utf-8")
)


def hf_evidence():
    return {
        "schema": module.HF_SCHEMA,
        "observation_class": "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE",
        "state": "OBSERVED",
        "node_registration": {
            "node_id": "stegnode-test",
            "device_continuity_id": "stegdevice-test",
            "state": "ESTABLISHED",
            "credential_authority": "TV/TVC",
        },
        "resident_receipt": {
            "state": "COMPLETE",
            "credential_used": False,
            "github_token_used": False,
            "authority_effect": "NONE",
        },
        "intr_receipt": {
            "state": "COMPLETE",
            "transport_profile": "stegverse.universal-intr.adjacent-hop/v1",
            "destination_validation": "PASS",
            "lineage_verified": True,
            "claims": {
                "credential_used": False,
                "runtime_activation_claimed": False,
                "production_interlock_runtime_activated": False,
            },
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
        "reconstruction_entry": {
            "receipt": {
                "state": "PASS",
                "same_execution": True,
            }
        },
        "authority_effect": "NONE",
    }


def hil_evidence():
    return {
        "schema": module.HIL_SCHEMA,
        "state": "OBSERVED",
        "observation_class": "AUTHENTIC_ESTABLISHED_STEGVERSE_WEB_NODE",
        "existing_node_reused": True,
        "new_node_identity_minted": False,
        "credential_used": False,
        "github_token_used": False,
        "exact_byte_reconstruction": "PASS",
        "custody_state": "EXACT_BYTES_PERSISTED",
        "registry_state": "RECORDED",
        "journal_replay_state": "PASS",
        "next_required_transition": "HIL_CUSTODY_TVC_INTERLOCK_ADMISSION",
        "tvc_receiving_receipt_observed": False,
        "receiver_restart_reconstruction_observed": False,
        "authority_effect": "NONE",
    }


def test_hf_admission_advances_only_adjacent_external_api_egress():
    updated, admission = module.admit(hf_evidence(), FACTS)
    assert admission["capability_type"] == "ADJACENT_EXTERNAL_API_EGRESS"
    assert admission["facts_advanced"] == [
        "transport_capabilities_observed.ADJACENT_EXTERNAL_API_EGRESS"
    ]
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


def test_hil_ingress_capability_does_not_require_downstream_tvc_receipt():
    evidence = hil_evidence()
    assert evidence["tvc_receiving_receipt_observed"] is False
    updated, admission = module.admit(evidence, FACTS)
    assert updated["transport_capabilities_observed"]["PUBLIC_HTTPS_INGRESS"] is True
    assert admission["activation_performed"] is False


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
