import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tvc_readiness_admission",
    ROOT / "scripts" / "admit_tvc_readiness_evidence.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def resident_base(**overrides):
    value = {
        "schema": "stegverse.tvc.coinbase_intr_resident_readiness/v3",
        "state": "BLOCKED_RECIPIENT_KEY_NOT_PROVISIONED",
        "ready_for_owner_ingress": False,
        "provider_operation_authorized": False,
        "provider_operation_started": False,
        "credential_plaintext_observed": False,
        "credential_authority": "TV/TVC",
        "credential_custody_target": "SKAP_VAULT",
        "transport_protocol": "InTr",
        "authority_transfer": False,
    }
    value.update(overrides)
    return value


def boundary_ready(**overrides):
    value = {
        "schema": "stegverse.tvc.skap_vault_runtime_boundary_observation/v1",
        "state": "READY_FOR_SKAP_VAULT_INGRESS",
        "ready_for_skap_vault_ingress": True,
        "credential_authority": "TV/TVC",
        "credential_custody_target": "KV_HOSTED_SKAP_VAULT",
        "storage_connector": "KV_SKAP_INTR_ONLY",
        "device_durable_secret_custody": False,
        "kv_decryption_authority": False,
        "provider_operation_authorized": False,
        "execution_authority": "NONE",
        "authority_transfer": False,
    }
    value.update(overrides)
    return value


def test_blocked_observation_is_admitted_as_false_facts_only():
    result = module.admit(resident_base())
    assert result["decision"] == "ADMIT_FACTS_DELTA"
    assert all(value is False for value in result["facts_delta"].values())
    assert result["activation_performed"] is False
    assert result["authority_effect"] == "NONE"


def test_ready_owner_ingress_advances_only_proven_liveness_facts():
    resident = resident_base(
        state="READY_FOR_OWNER_INGRESS",
        ready_for_owner_ingress=True,
        private_key_liveness_verified=True,
        public_projection_verified=True,
        successor_service_installed=True,
        browser_ingress_service_installed=True,
        browser_ingress_health_verified=True,
        public_intr_route_verified=False,
        double_interlock_receipt_chain_observed=False,
        device_kv_receipt_observed=False,
        kv_skap_receipt_observed=False,
    )
    result = module.admit(resident)
    facts = result["facts_delta"]
    assert facts["tvc_resident_key_liveness_observed"] is True
    assert facts["ready_for_owner_ingress_observed"] is True
    assert facts["production_gateway_route_observed"] is False
    assert facts["production_double_interlock_receipts_observed"] is False
    assert facts["skap_vault_runtime_boundary_observed"] is False
    assert result["production_interlock_runtime_activated_set_by_adapter"] is False


def test_ready_double_interlock_plus_boundary_advances_exact_runtime_facts():
    resident = resident_base(
        state="READY_WITH_DOUBLE_INTERLOCK_RECEIPTS",
        ready_for_owner_ingress=True,
        private_key_liveness_verified=True,
        public_projection_verified=True,
        successor_service_installed=True,
        browser_ingress_service_installed=True,
        browser_ingress_health_verified=True,
        public_intr_route_verified=True,
        double_interlock_receipt_chain_observed=True,
        device_kv_receipt_observed=True,
        kv_skap_receipt_observed=True,
        device_kv_receipt_hash="sha256:first",
        kv_skap_receipt_hash="sha256:second",
        double_interlock_chain_digest="sha256:chain",
    )
    result = module.admit(resident, boundary_ready())
    assert result["facts_delta"] == {
        "tvc_resident_key_liveness_observed": True,
        "ready_for_owner_ingress_observed": True,
        "production_gateway_route_observed": True,
        "production_double_interlock_receipts_observed": True,
        "skap_vault_runtime_boundary_observed": True,
    }
    assert result["provider_session_evidence_set_by_adapter"] is False
    assert result["activation_performed"] is False


def test_authority_escalation_is_rejected():
    with pytest.raises(module.AdmissionError):
        module.admit(resident_base(provider_operation_authorized=True))
    with pytest.raises(module.AdmissionError):
        module.admit(resident_base(), boundary_ready(execution_authority="ALLOW"))


def test_secret_bearing_evidence_is_rejected():
    with pytest.raises(module.AdmissionError):
        module.admit(resident_base(recipient_private_key="-----BEGIN PRIVATE KEY-----abc"))
    with pytest.raises(module.AdmissionError):
        module.admit(resident_base(credential_plaintext_observed=True))
