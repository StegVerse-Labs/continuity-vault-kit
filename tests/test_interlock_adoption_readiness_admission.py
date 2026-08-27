import copy
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

ADMIT_SPEC = importlib.util.spec_from_file_location(
    "interlock_adoption_admission",
    ROOT / "scripts" / "admit_interlock_adoption_readiness.py",
)
admit_module = importlib.util.module_from_spec(ADMIT_SPEC)
assert ADMIT_SPEC.loader is not None
ADMIT_SPEC.loader.exec_module(admit_module)

EVAL_SPEC = importlib.util.spec_from_file_location(
    "kv_activation_readiness",
    ROOT / "scripts" / "evaluate_kv_activation_readiness.py",
)
eval_module = importlib.util.module_from_spec(EVAL_SPEC)
assert EVAL_SPEC.loader is not None
EVAL_SPEC.loader.exec_module(eval_module)


def blocked_assessment():
    return {
        "schema": "stegos.universal_interlock_adoption_readiness.v1",
        "protocol_id": "SV-INTERLOCK-v0.4-candidate",
        "state": "BLOCKED",
        "blockers": [
            "AUTHENTIC_RUNTIME_BINDING_MISSING",
            "MASTER_RECORDS_CUSTODY_RECEIPT_MISSING",
            "MASTER_RECORDS_RECONSTRUCTION_NOT_VERIFIED",
        ],
        "runtime_binding_id": None,
        "master_records_custody_receipt_id": None,
        "runtime_conformance_evidenced": False,
        "master_records_custody_evidenced": False,
        "master_records_reconstruction_verified": False,
        "canonical_protocol_adopted": False,
        "runtime_activation": False,
        "production_interlock_runtime_activated": False,
        "adoption_decision_created": False,
        "execute_consequence": False,
        "canonical_result_committed": False,
        "credential_authority": "TV/TVC",
        "master_records_authority_effect": "NONE",
        "authority_effect": "NONE",
    }


def test_blocked_interlock_assessment_admits_only_explanatory_facts():
    result = admit_module.admit_interlock_adoption_readiness(blocked_assessment())
    assert result["decision"] == "ADMIT_EXPLANATORY_FACTS"
    assert result["facts_delta"]["universal_interlock_adoption_review_ready"] is False
    assert result["facts_delta"]["universal_interlock_adoption_review_state"] == "BLOCKED"
    assert result["facts_delta"]["universal_interlock_adoption_review_blockers"]
    assert result["production_interlock_runtime_activated_set_by_adapter"] is False
    assert result["canonical_protocol_adopted_set_by_adapter"] is False
    assert result["activation_performed"] is False
    assert result["authority_effect"] == "NONE"


def test_ready_for_review_still_cannot_activate_interlock():
    assessment = blocked_assessment()
    assessment["state"] = "READY_FOR_ADOPTION_REVIEW"
    assessment["blockers"] = []
    assessment["runtime_binding_id"] = "runtime-binding-1"
    assessment["master_records_custody_receipt_id"] = "custody-receipt-1"
    assessment["runtime_conformance_evidenced"] = True
    assessment["master_records_custody_evidenced"] = True
    assessment["master_records_reconstruction_verified"] = True
    result = admit_module.admit_interlock_adoption_readiness(assessment)
    assert result["facts_delta"]["universal_interlock_adoption_review_ready"] is True
    assert result["production_interlock_runtime_activated_set_by_adapter"] is False
    assert result["canonical_protocol_adopted_set_by_adapter"] is False


def test_adopted_or_active_source_claim_is_rejected():
    assessment = blocked_assessment()
    assessment["canonical_protocol_adopted"] = True
    with pytest.raises(admit_module.AdmissionError):
        admit_module.admit_interlock_adoption_readiness(assessment)

    assessment = blocked_assessment()
    assessment["runtime_activation"] = True
    with pytest.raises(admit_module.AdmissionError):
        admit_module.admit_interlock_adoption_readiness(assessment)

    assessment = blocked_assessment()
    assessment["production_interlock_runtime_activated"] = True
    with pytest.raises(admit_module.AdmissionError):
        admit_module.admit_interlock_adoption_readiness(assessment)


def test_current_kv_snapshot_exposes_upstream_interlock_blockers_without_activation():
    snapshot = eval_module.evaluate()
    review = snapshot["interlock_adoption_review"]
    assert review["ready"] is False
    assert review["state"] == "BLOCKED"
    assert set(review["blockers"]) == {
        "AUTHENTIC_RUNTIME_BINDING_MISSING",
        "MASTER_RECORDS_CUSTODY_RECEIPT_MISSING",
        "MASTER_RECORDS_RECONSTRUCTION_NOT_VERIFIED",
    }
    assert review["canonical_protocol_adopted"] is False
    assert review["runtime_activation"] is False
    assert review["authority_effect"] == "NONE"
    assert snapshot["production_interlock_runtime_activated"] is False
    assert snapshot["summary"]["governed_ready"] == 0
    assert snapshot["summary"]["governed_blocked"] == 46
