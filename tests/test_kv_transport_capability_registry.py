import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_kv_transport_capability_registry",
    ROOT / "scripts" / "validate_kv_transport_capability_registry.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)

REGISTRY = json.loads(
    (ROOT / "specs" / "kv-transport-capability-registry.v1.json").read_text(encoding="utf-8")
)


def test_current_registry_is_fail_closed_and_non_authorizing():
    assert module.validate(REGISTRY) == []
    assert REGISTRY["state"] == "DEFINED_INACTIVE"
    assert REGISTRY["credential_authority"] == "TV/TVC"
    assert REGISTRY["authority_effect"] == "NONE"
    assert REGISTRY["runtime_activation_claimed"] is False
    assert all(cap["capability_state"] == "DEFINED_UNOBSERVED" for cap in REGISTRY["capabilities"])
    assert all(cap["runtime_observed"] is False for cap in REGISTRY["capabilities"])
    assert all(cap["authority_effect"] == "NONE" for cap in REGISTRY["capabilities"])


def test_every_transport_type_requires_node_and_kv_continuity():
    for cap in REGISTRY["capabilities"]:
        binding = cap["binding_requirements"]
        assert binding["device_node_continuity_required"] is True
        assert binding["kv_continuity_binding_required"] is True


def test_carrier_protocol_does_not_collapse_distinct_transport_types():
    by_type = {cap["capability_type"]: cap for cap in REGISTRY["capabilities"]}
    hil = by_type["PUBLIC_HTTPS_INGRESS"]
    hf = by_type["ADJACENT_EXTERNAL_API_EGRESS"]
    assert "HTTPS" in hil["carrier_profiles"]
    assert "HTTPS" in hf["carrier_profiles"]
    assert hil["capability_type"] != hf["capability_type"]
    assert hil["direction"] == "INGRESS"
    assert hf["direction"] == "EGRESS"


def test_transport_capability_requires_receipts_and_reconstruction():
    for cap in REGISTRY["capabilities"]:
        receipts = cap["receipt_requirements"]
        assert receipts["capability_establishment_receipt_required"] is True
        assert receipts["adjacent_boundary_receipts_required"] is True
        assert receipts["reconstruction_evidence_required"] is True


def test_revoked_expired_or_superseded_capability_fails_closed():
    for cap in REGISTRY["capabilities"]:
        policy = cap["reuse_policy"]
        assert policy["reuse_allowed_when_valid"] is True
        assert policy["revoked_fails_closed"] is True
        assert policy["expired_fails_closed"] is True
        assert policy["superseded_fails_closed"] is True


def test_validator_rejects_runtime_observation_in_source_registry():
    payload = copy.deepcopy(REGISTRY)
    payload["capabilities"][0]["runtime_observed"] = True
    failures = module.validate(payload)
    assert any("may not claim runtime observation" in failure for failure in failures)


def test_validator_rejects_missing_kv_binding_requirement():
    payload = copy.deepcopy(REGISTRY)
    payload["capabilities"][0]["binding_requirements"]["kv_continuity_binding_required"] = False
    failures = module.validate(payload)
    assert any("KV continuity binding must be required" in failure for failure in failures)


def test_validator_rejects_duplicate_transport_type():
    payload = copy.deepcopy(REGISTRY)
    payload["capabilities"].append(copy.deepcopy(payload["capabilities"][0]))
    failures = module.validate(payload)
    assert any("duplicate capability_type" in failure for failure in failures)
