import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kv_activation_readiness",
    ROOT / "scripts" / "evaluate_kv_activation_readiness.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_current_snapshot_is_fail_closed_and_non_authorizing():
    snapshot = module.evaluate()
    assert snapshot["entry_count"] == 46
    assert snapshot["module_count"] == 13
    assert snapshot["service_count"] == 33
    assert snapshot["baseline_intr_complete"] is True
    assert snapshot["production_interlock_runtime_activated"] is False
    assert snapshot["activation_performed"] is False
    assert snapshot["authority_effect"] == "NONE"
    assert snapshot["summary"] == {
        "local_ready": 45,
        "local_blocked": 1,
        "governed_ready": 0,
        "governed_blocked": 46,
    }
    assert all(e["install_state"] == "INSTALLED_INACTIVE" for e in snapshot["entries"])
    assert all(e["activation_performed"] is False for e in snapshot["entries"])
    assert all(e["authority_effect"] == "NONE" for e in snapshot["entries"])
    assert all(e["governed_action_readiness"] == "BLOCKED" for e in snapshot["entries"])


def test_stegid_remains_locally_blocked_until_current_receipt_exists():
    snapshot = module.evaluate()
    stegid = next(e for e in snapshot["entries"] if e["entry_id"] == "stegid-continuity")
    assert stegid["local_materialization"] == "BLOCKED_CURRENT_IDENTITY"
    assert "current_identity_continuity_receipt_observed" in stegid["governed_blockers"]


def test_local_services_can_be_materializable_without_governed_authority():
    snapshot = module.evaluate()
    journal = next(e for e in snapshot["entries"] if e["entry_id"] == "personal-journal")
    assert journal["local_materialization"] == "READY_FOR_LOCAL_MATERIALIZATION"
    assert journal["governed_action_readiness"] == "BLOCKED"
    assert "production_interlock_runtime_activated" in journal["governed_blockers"]


def test_stegfin_preserves_full_production_tvc_blockers():
    snapshot = module.evaluate()
    stegfin = next(e for e in snapshot["entries"] if e["entry_id"] == "stegfin-wallet-pay")
    required = {
        "production_interlock_runtime_activated",
        "tvc_resident_key_liveness_observed",
        "ready_for_owner_ingress_observed",
        "production_gateway_route_observed",
        "production_double_interlock_receipts_observed",
        "provider_session_evidence_observed",
    }
    assert required.issubset(set(stegfin["governed_blockers"]))
