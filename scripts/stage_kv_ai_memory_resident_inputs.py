#!/usr/bin/env python3
"""Stage private KV AI memory inputs for the fenced resident lane.

This script is intentionally local/private. It builds the deterministic context
packet from already-readable KV entry projections and stages the packet plus the
provider-request input into a caller-selected resident state root. It never
creates or infers an InTr admission artifact, never calls a model/provider, and
never writes canonical KV state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runtime.kv_ai_memory_substrate import build_context_packet

PACKET_REL = Path("inputs/context-packet.json")
REQUEST_INPUT_REL = Path("inputs/provider-request-input.json")
ADMISSION_REL = Path("inputs/memory-packet-admission.json")
STAGING_RECEIPT_REL = Path("receipts/private-input-staging.json")
FORBIDDEN_KEYS = {
    "api_key", "apikey", "token", "access_token", "refresh_token", "password",
    "secret", "private_key", "seed", "mnemonic", "credential", "authorization",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_entries(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("entries must be JSON array of objects")
    return value


def reject_credential_like_fields(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS or normalized.endswith("_api_key") or normalized.endswith("_token") or normalized.endswith("_password"):
                raise ValueError(f"credential-like field forbidden in provider request input: {path}.{key}")
            reject_credential_like_fields(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_credential_like_fields(item, path=f"{path}[{index}]")


def validate_provider_request_input(value: dict[str, Any]) -> None:
    reject_credential_like_fields(value)
    if not isinstance(value.get("provider"), str) or not value["provider"].strip():
        raise ValueError("provider required")
    if not isinstance(value.get("model"), str) or not value["model"].strip():
        raise ValueError("model required")
    if not isinstance(value.get("created_at"), str) or not value["created_at"].strip():
        raise ValueError("created_at required for exact replay")
    messages = value.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages required")
    for message in messages:
        if not isinstance(message, dict) or not isinstance(message.get("role"), str) or not isinstance(message.get("content"), str):
            raise ValueError("each message requires string role/content")


def write_private(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stage(*, request: dict[str, Any], entries: list[dict[str, Any]], provider_request_input: dict[str, Any], stage_root: Path) -> dict[str, Any]:
    validate_provider_request_input(provider_request_input)
    packet = build_context_packet(request, entries)
    if packet.get("selected_item_count", 0) < 1:
        raise ValueError("context request selected no AI-eligible KV entries")
    root = stage_root.expanduser().resolve()
    packet_path = root / PACKET_REL
    request_input_path = root / REQUEST_INPUT_REL
    admission_path = root / ADMISSION_REL
    write_private(packet_path, packet)
    write_private(request_input_path, provider_request_input)

    receipt = {
        "schema": "stegverse.kv.ai-memory-resident-private-staging/v1",
        "state": "PRIVATE_INPUTS_STAGED_AWAITING_INTR_ADMISSION",
        "packet_id": packet["packet_id"],
        "selected_item_count": packet["selected_item_count"],
        "packet_ref": PACKET_REL.as_posix(),
        "provider_request_input_ref": REQUEST_INPUT_REL.as_posix(),
        "memory_packet_admission_ref": ADMISSION_REL.as_posix(),
        "memory_packet_admission_present": admission_path.is_file(),
        "private_content_exported_to_repository": False,
        "intr_admission_decided": False,
        "provider_request_materialized": False,
        "provider_execution_observed": False,
        "kv_writeback_observed": False,
        "credential_material_present": False,
        "authority_effect": "NONE_PRIVATE_STAGING_ONLY",
    }
    write_private(root / STAGING_RECEIPT_REL, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage private KV AI memory resident inputs")
    parser.add_argument("--context-request", type=Path, required=True)
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--provider-request-input", type=Path, required=True)
    parser.add_argument("--stage-root", type=Path, required=True)
    args = parser.parse_args()
    receipt = stage(
        request=load_object(args.context_request),
        entries=load_entries(args.entries),
        provider_request_input=load_object(args.provider_request_input),
        stage_root=args.stage_root,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
