#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / "fixtures" / "multimodal"

ALLOWED_COMPLETENESS = {
    "complete_for_declared_scope",
    "bounded_but_coherent",
    "materially_incomplete",
    "protected_evidence_unavailable",
    "source_deleted_under_policy",
    "timing_uncertain",
    "interpretation_disputed",
    "generated_only",
}


class CapsuleValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CapsuleValidationError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CapsuleValidationError(f"cannot read JSON: {exc}") from exc
    require(isinstance(data, dict), "capsule root must be an object")
    return data


def validate_capsule(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "experience_id",
        "start_time",
        "participants",
        "authorized_devices",
        "streams",
        "consent_transitions",
        "retention_policy",
        "provenance_root",
        "reconstruction_rights",
        "completeness_status",
    }
    missing = sorted(required - data.keys())
    require(not missing, f"missing required fields: {', '.join(missing)}")
    require(data["schema_version"] == "0.1", "unsupported schema_version")
    require(isinstance(data["streams"], list) and data["streams"], "streams must be a non-empty list")
    require(data["completeness_status"] in ALLOWED_COMPLETENESS, "invalid completeness_status")

    stream_ids: set[str] = set()
    has_material_missing = False
    for item in data.get("missing_evidence", []):
        require(isinstance(item, dict), "missing_evidence entries must be objects")
        if item.get("materiality") in {"material", "unknown"}:
            has_material_missing = True

    for stream in data["streams"]:
        require(isinstance(stream, dict), "stream entries must be objects")
        stream_id = stream.get("stream_id")
        require(isinstance(stream_id, str) and stream_id, "stream_id is required")
        require(stream_id not in stream_ids, f"duplicate stream_id: {stream_id}")
        stream_ids.add(stream_id)

        artifact_class = stream.get("artifact_class")
        retention_class = stream.get("retention_class")
        generated = stream.get("generated", False)
        payload_ref = stream.get("payload_ref")

        if artifact_class == "generated_reconstruction":
            require(generated is True, f"{stream_id}: generated reconstruction must set generated=true")
            require(bool(stream.get("source_stream_refs")), f"{stream_id}: generated reconstruction requires source_stream_refs")
            require(bool(stream.get("transform_method")), f"{stream_id}: generated reconstruction requires transform_method")
            require(bool(stream.get("transform_version")), f"{stream_id}: generated reconstruction requires transform_version")
        else:
            require(generated is not True, f"{stream_id}: only generated_reconstruction may set generated=true")

        if retention_class == "ephemeral":
            require(payload_ref is None, f"{stream_id}: ephemeral stream may not expose a durable payload_ref")

        if retention_class in {"deleted_with_receipt", "continuity_receipt_only"}:
            require(payload_ref is None, f"{stream_id}: deleted or receipt-only stream may not retain payload_ref")

    policy = data["retention_policy"]
    require(isinstance(policy, dict), "retention_policy must be an object")
    voice_mode = policy.get("default_voice_mode")
    rights = data["reconstruction_rights"]
    require(isinstance(rights, list), "reconstruction_rights must be a list")

    if voice_mode == "transcription_only":
        for stream in data["streams"]:
            if stream.get("modality") == "audio":
                require(stream.get("user_recall_available") is False, "transcription_only audio may not be user recallable")
        for right in rights:
            require(right.get("may_access_raw") is False, "transcription_only policy may not grant raw-audio access")

    transitions = data.get("fidelity_transitions", [])
    require(isinstance(transitions, list), "fidelity_transitions must be a list")
    for transition in transitions:
        require(isinstance(transition, dict), "fidelity transition must be an object")
        require(bool(transition.get("information_loss")), "fidelity transition must declare information_loss")
        require(isinstance(transition.get("reversible"), bool), "fidelity transition must declare reversible")
        if transition.get("to_class") == "continuity_receipt_only":
            require(transition.get("reversible") is False, "receipt-only transition cannot be reversible")

    completeness = data["completeness_status"]
    if has_material_missing:
        require(completeness != "complete_for_declared_scope", "material missing evidence cannot be complete_for_declared_scope")
    if completeness == "complete_for_declared_scope":
        require(not data.get("missing_evidence"), "complete_for_declared_scope cannot declare missing evidence")
    if completeness == "generated_only":
        require(all(s.get("artifact_class") == "generated_reconstruction" for s in data["streams"]), "generated_only requires all streams to be generated reconstructions")


def validate_path(path: Path) -> None:
    validate_capsule(load_json(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate governed ExperienceCapsule fixtures.")
    parser.add_argument("paths", nargs="*", type=Path, help="Capsule JSON files. Defaults to fixtures/multimodal/*.json")
    args = parser.parse_args()

    paths = args.paths or sorted(DEFAULT_FIXTURES.glob("*.json"))
    if not paths:
        raise SystemExit("EXPERIENCE CAPSULE VALIDATION FAILED: no capsule files found")

    failures: list[str] = []
    for path in paths:
        try:
            validate_path(path)
            print(f"PASS {path}")
        except CapsuleValidationError as exc:
            failures.append(f"{path}: {exc}")
            print(f"FAIL {path}: {exc}")

    if failures:
        raise SystemExit("EXPERIENCE CAPSULE VALIDATION FAILED\n" + "\n".join(failures))

    print("EXPERIENCE CAPSULE VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
