import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kv_personal_services_validator",
    ROOT / "scripts" / "validate_kv_personal_services_registry.py",
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def load_registry():
    return json.loads(
        (ROOT / "specs" / "kv-personal-services-registry.v1.json").read_text(
            encoding="utf-8"
        )
    )


def test_personal_services_registry_is_inactive_and_authority_neutral():
    payload = load_registry()
    assert module.validate(payload) == []
    assert payload["state"] == "INSTALLED_INACTIVE"
    assert payload["authority_effect"] == "NONE"
    assert payload["interlock_activation_required_for_install"] is False
    assert payload["runtime_activation_claimed"] is False
    assert payload["network_activation_claimed"] is False
    assert payload["credential_activation_claimed"] is False
    assert payload["provider_activation_claimed"] is False


def test_service_registry_is_unique_and_uses_semantic_kv_surfaces():
    payload = load_registry()
    ids = [service["service_id"] for service in payload["services"]]
    assert len(ids) == 33
    assert len(ids) == len(set(ids))
    assert payload["service_count"] == 33
    for service in payload["services"]:
        assert service["install_state"] == "INSTALLED_INACTIVE"
        assert service["authority_effect"] == "NONE"
        assert service["kv_surfaces"]
        assert all(not surface.startswith("_System/Services/") for surface in service["kv_surfaces"])


def test_expected_service_classes_are_covered():
    payload = load_registry()
    classes = {service["service_class"] for service in payload["services"]}
    assert classes == {"KV_NATIVE", "KV_DEVICE", "KV_DEVICE_PROVIDER"}
