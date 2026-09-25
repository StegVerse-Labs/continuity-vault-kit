"""Source-only capability composition for existing MyKV/Auri owners.

This module cannot perform user verification, admit transport/Interlock transitions,
grant capture rights, mint receipts or reconstruct Master Records. Caller facts
are test inputs, never authenticated evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "specs/kv-auri-peripheral-capability-profiles.v1.json"
MODULES = ROOT / "specs/kv-device-backed-capability-registry.v1.json"
TRANSPORT = ROOT / "specs/kv-transport-capability-registry.v1.json"

EXPECTED_SCOPES = {
    "live_audio": ("audio_capture",),
    "live_video": ("video_capture",),
    "live_audio_video": ("audio_capture", "video_capture"),
}
EXPECTED_PROFILES = {
    "live_audio": ("audio_input", "audio_output"),
    "live_video": ("video_input", "video_output"),
    "live_audio_video": ("audio_input", "audio_output", "video_input", "video_output"),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry_not_an_object")
    return value


def validate_source_contract(
    profiles: Mapping[str, Any] | None = None,
    modules: Mapping[str, Any] | None = None,
    transport: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check immutable source invariants; never claim activation."""
    profiles = profiles if profiles is not None else load_json(PROFILES)
    modules = modules if modules is not None else load_json(MODULES)
    transport = transport if transport is not None else load_json(TRANSPORT)
    required = {
        "schema": "stegverse.kv.auri-peripheral-capability-profiles/v1",
        "state": "DEFINED_INACTIVE",
        "authority_effect": "NONE",
        "runtime_activation_claimed": False,
        "user_verifier": "KV/SKAP Vault",
        "node_role": "INTERCHANGEABLE_TRANSPORT_OR_EXECUTION",
        "device_identity_gate": "NONE_PROHIBITED",
        "credential_authority": "TV/TVC",
        "transition_authority": "Interlock/InTr",
        "custody_reconstruction": "Master Records",
        "source_validation_is_not_runtime_proof": True,
    }
    for key, expected in required.items():
        if profiles.get(key) != expected:
            raise ValueError(f"invalid_invariant:{key}")
    if modules.get("schema") != "stegverse.kv.device-backed-capability-registry/v1":
        raise ValueError("existing_module_registry_missing")
    if transport.get("schema") != "stegverse.kv.transport-capability-registry/v1":
        raise ValueError("existing_transport_registry_missing")
    actual_modules = {x.get("module_id") for x in modules.get("modules", [])}
    if not {"stegwhisper", "auri-ecosystem-chat"} <= actual_modules:
        raise ValueError("existing_module_bindings_missing")
    if set(profiles.get("registry_bindings", [])) != {"stegwhisper", "auri-ecosystem-chat"}:
        raise ValueError("duplicate_or_missing_existing_module_binding")
    ids = [p.get("id") for p in profiles.get("profiles", [])]
    if len(ids) != len(set(ids)) or set(ids) != {
        "visual_display", "touch_gesture", "audio_input", "audio_output",
        "video_input", "video_output", "flexible_glass",
    }:
        raise ValueError("profile_identity_mismatch")
    indexed = {p["id"]: p for p in profiles["profiles"]}
    for profile in indexed.values():
        if profile.get("actual_hardware_observation_required") is not True:
            raise ValueError("actual_hardware_observation_required")
    for mode in profiles.get("modes", []):
        name = mode.get("id")
        if name not in EXPECTED_PROFILES:
            raise ValueError("unexpected_live_mode")
        if tuple(mode.get("required_profiles", [])) != EXPECTED_PROFILES[name]:
            raise ValueError("mode_profile_scope_mismatch")
        if tuple(mode.get("capture_scopes", [])) != EXPECTED_SCOPES[name]:
            raise ValueError("mode_capture_scope_mismatch")
    if {m.get("id") for m in profiles.get("modes", [])} != set(EXPECTED_PROFILES):
        raise ValueError("missing_live_mode")
    glass = indexed["flexible_glass"]
    if glass.get("photovoltaic_is_not_display") is not True:
        raise ValueError("photovoltaic_misrepresented_as_display")
    if glass.get("requires_actual_observed_components") is not True:
        raise ValueError("unverified_glass_components")
    if glass.get("standalone_compute_or_network_not_assumed") is not True:
        raise ValueError("implicit_standalone_glass_node")
    expected_semantics = (
        "preserve_my_kv_session_identity",
        "fresh_scoped_manifest_for_changed_capture_or_transport",
        "separate_input_output_consent",
        "registration_does_not_grant_capture",
        "each_actual_intr_hop_requires_authentic_disposition",
        "transport_type_distinct_from_carrier",
        "revocation_stops_affected_capture_and_egress",
        "raw_audio_video_transcripts_ephemeral_by_default",
        "stop_and_mute_independent_of_inference",
        "no_second_user_operated_device",
    )
    if not all(profiles.get("mode_semantics", {}).get(k) is True for k in expected_semantics):
        raise ValueError("mode_invariant_missing")
    return {"state": "SOURCE_CONTRACT_VALID", "profiles": len(ids), "modes": 3,
            "authority_effect": "NONE", "authentic_runtime_evidence": False}


def propose_live_mode(request: Mapping[str, Any]) -> dict[str, Any]:
    """Generate a *non-authorizing* candidate with one precise first missing predicate.

    This deterministic source fixture requires real callers to obtain actual
    KV/SKAP, typed transport and independent Interlock/InTr evidence separately.
    No caller may upgrade its return value to an authentic ALLOW or DENY receipt.
    """
    mode = request.get("mode")
    sid = request.get("session_id")
    if not isinstance(sid, str) or not sid:
        raise ValueError("session_id_required")
    if mode not in EXPECTED_PROFILES:
        raise ValueError("unknown_live_mode")

    def result(candidate: str, reason: str, scopes: list[str]) -> dict[str, Any]:
        return {
            "evidence_class": "SOURCE_ONLY",
            "authentic_transition_receipt": False,
            "master_records_reconstruction": False,
            "session_id": sid,
            "mode": mode,
            "candidate_disposition": candidate,
            "first_missing_predicate": reason,
            "requested_capture_scopes": list(EXPECTED_SCOPES[mode]),
            "admissible_capture_scopes": scopes,
            "fresh_manifest_required": True,
        }

    if not request.get("kv_skap_verification_observed"):
        return result("CANDIDATE_NON_ALLOW", "KV_SKAP_VERIFICATION_NOT_OBSERVED", [])
    if not request.get("peripheral_relationship_active"):
        return result("CANDIDATE_NON_ALLOW", "SKAP_PERIPHERAL_RELATIONSHIP_INACTIVE_OR_REVOKED", [])
    if not request.get("eligible_node_observed"):
        return result("CANDIDATE_NON_ALLOW", "ELIGIBLE_NODE_NOT_OBSERVED", [])
    available = set(request.get("observed_profiles", []))
    for profile in EXPECTED_PROFILES[mode]:
        if profile not in available:
            return result("CANDIDATE_NON_ALLOW", f"PERIPHERAL_CAPABILITY_NOT_OBSERVED:{profile}", [])
    accepted = set(request.get("current_capture_consents", []))
    for scope in EXPECTED_SCOPES[mode]:
        if scope not in accepted:
            return result("CANDIDATE_NON_ALLOW", f"CAPTURE_CONSENT_NOT_OBSERVED:{scope}", [])
    if not request.get("typed_transport_observed"):
        return result("CANDIDATE_NON_ALLOW", "TYPED_TRANSPORT_NOT_OBSERVED", [])
    if not request.get("all_hop_intr_admissions_observed"):
        return result("CANDIDATE_NON_ALLOW", "ADJACENT_INTR_ADMISSION_NOT_OBSERVED", [])
    if not request.get("scope_bound_manifest"):
        return result("CANDIDATE_NON_ALLOW", "SCOPE_BOUND_MANIFEST_NOT_OBSERVED", [])
    return result("CANDIDATE_ALLOW_REQUIRES_REAL_RUNTIME_DISPOSITION",
                  "AUTHENTIC_RUNTIME_AND_MASTER_RECORDS_PROOF_REQUIRED",
                  list(EXPECTED_SCOPES[mode]))


if __name__ == "__main__":
    print(json.dumps(validate_source_contract(), sort_keys=True))
