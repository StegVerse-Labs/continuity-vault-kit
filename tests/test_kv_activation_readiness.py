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


def test_all_governed_entries_require_device_kv_transport_capability():
    snapshot = module.evaluate()
    assert snapshot["transport_capabilities_observed"]["DEVICE_KV_INTR"] is False
    assert snapshot["transport_capabilities_observed"]["ADJACENT_EXTERNAL_API_EGRESS"] is True
    assert all(
        "DEVICE_KV_INTR" in entry["transport_capability_requirements"]
        for entry in snapshot["entries"]
    )
    assert all(
        "transport_capability:DEVICE_KV_INTR" in entry["governed_blockers"]
        for entry in snapshot["entries"]
    )


def test_external_provider_services_require_adjacent_external_api_egress():
    snapshot = module.evaluate()
    services = json.loads(
        (ROOT / "specs" / "kv-personal-services-registry.v1.json").read_text(encoding="utf-8")
    )["services"]
    provider_backed = {
        service["service_id"]
        for service in services
        if service["service_class"] == "KV_DEVICE_PROVIDER" or service["provider_dependency"] != "NONE"
    }
    entries = {entry["entry_id"]: entry for entry in snapshot["entries"] if entry["entry_type"] == "SERVICE"}
    assert provider_backed
    for service_id in provider_backed:
        entry = entries[service_id]
        assert "ADJACENT_EXTERNAL_API_EGRESS" in entry["transport_capability_requirements"]
        assert "transport_capability:ADJACENT_EXTERNAL_API_EGRESS" not in entry["governed_blockers"]


def test_local_only_personal_journal_does_not_require_external_api_egress():
    snapshot = module.evaluate()
    journal = next(e for e in snapshot["entries"] if e["entry_id"] == "personal-journal")
    assert journal["transport_capability_requirements"] == ["DEVICE_KV_INTR"]
    assert "transport_capability:ADJACENT_EXTERNAL_API_EGRESS" not in journal["governed_blockers"]


def test_observed_external_api_egress_does_not_clear_other_governance_blockers():
    snapshot = module.evaluate()
    provider_entries = [
        entry for entry in snapshot["entries"]
        if entry["entry_type"] == "SERVICE"
        and "ADJACENT_EXTERNAL_API_EGRESS" in entry["transport_capability_requirements"]
    ]
    assert provider_entries
    for entry in provider_entries:
        assert entry["governed_action_readiness"] == "BLOCKED"
        assert "transport_capability:DEVICE_KV_INTR" in entry["governed_blockers"]
        assert "production_interlock_runtime_activated" in entry["governed_blockers"]
