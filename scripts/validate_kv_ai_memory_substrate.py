#!/usr/bin/env python3
"""Validate the KV AI memory substrate contract and deterministic source behavior."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.kv_ai_memory_substrate import build_context_packet, build_write_proposal  # noqa: E402

SPEC = ROOT / "specs" / "kv-ai-memory-substrate.v1.json"
REQUIRED_SCHEMAS = [
    ROOT / "schemas" / "kv-ai-memory-context-request.schema.json",
    ROOT / "schemas" / "kv-ai-memory-context-packet.schema.json",
    ROOT / "schemas" / "kv-ai-memory-write-proposal.schema.json",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    require(spec.get("schema") == "stegverse.kv.ai-memory-substrate/v1", "invalid substrate schema")
    require(spec.get("goal_id") == "SV-KV-AI-PERSISTENCE-001", "goal_id mismatch")

    profile = spec.get("personal_assistant_profile", {})
    require(profile.get("kv_class") == "PERSONAL_KV", "personal assistant must use PERSONAL_KV")
    require(profile.get("authority_domain") == "PERSON", "personal assistant authority must remain PERSON")
    require(profile.get("consumer_ai_role") == "PERSONAL_ASSISTANT_AI", "personal assistant role mismatch")
    require(profile.get("model_is_authority") is False, "model may not be authority")
    require(profile.get("provider_is_authority") is False, "provider may not be authority")
    require(profile.get("context_transfers_authority") is False, "context may not transfer authority")
    require(profile.get("implicit_writeback_allowed") is False, "implicit writeback must be forbidden")
    require(profile.get("cross_authority_context_allowed") is False, "cross-authority context must be forbidden")
    require(profile.get("secret_material_allowed") is False, "secret material must be forbidden")
    require(profile.get("intr_admission_required") is True, "InTr admission must be required")

    selection = spec.get("selection_contract", {})
    require(selection.get("deterministic") is True, "selection must be deterministic")
    require(selection.get("semantic_claim") == "LEXICAL_BOUNDED_SELECTION_ONLY", "semantic overclaim detected")
    require(selection.get("oversized_entry_behavior") == "SKIP_NO_TRUNCATION", "oversized entries must not be silently truncated")
    require(selection.get("provenance_required") is True, "provenance required")
    require(selection.get("content_hash_required") is True, "content hash required")

    writeback = spec.get("writeback_contract", {})
    require(writeback.get("artifact_type") == "PROPOSAL_ONLY", "writeback must remain proposal only")
    require(writeback.get("execution_authorized") is False, "write proposal may not authorize execution")
    require(writeback.get("direct_kv_mutation") is False, "direct KV mutation forbidden")
    require(writeback.get("cross_class_mutation") is False, "cross-class mutation forbidden")

    runtime = spec.get("runtime_boundary", {})
    require(runtime.get("source_implementation_proves_runtime") is False, "source may not prove runtime")
    require(runtime.get("hosted_ci_proves_runtime") is False, "CI may not prove runtime")
    require(runtime.get("live_context_delivery_requires_authentic_intr_receipt") is True, "live context delivery must require InTr receipt")
    require(runtime.get("live_write_requires_target_kv_admission") is True, "live write must require target KV admission")
    require(runtime.get("credential_material_belongs_in_skap") is True, "credential custody must remain SKAP")

    for schema_path in REQUIRED_SCHEMAS:
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        require(payload.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"invalid JSON schema declaration: {schema_path.name}")
        require(payload.get("additionalProperties") is False, f"schema must fail closed on unknown fields: {schema_path.name}")

    request = {
        "schema": "stegverse.kv.ai-memory-context-request/v1",
        "request_id": "VALIDATION-REQUEST-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "consumer_ai_role": "PERSONAL_ASSISTANT_AI",
        "source_kv_instance_ids": ["KV-VALIDATION-1"],
        "purpose": "validate bounded memory context",
        "query_terms": ["continuity"],
        "max_items": 2,
        "max_bytes": 2048,
        "intr_admission_required": True,
        "authority_effect": "NONE_CONTEXT_REQUEST_ONLY",
    }
    entries = [{
        "entry_id": "VALIDATION-ENTRY-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "source_kv_instance_id": "KV-VALIDATION-1",
        "relative_path": "01_Notes/continuity.md",
        "title": "Continuity",
        "content": "Governed continuity state for deterministic validation.",
        "tags": ["continuity"],
        "retention_class": "PROJECT",
        "provenance_ref": "VALIDATION-SOURCE-001",
        "ai_context_allowed": True,
        "secret_material": False,
        "priority": 1,
    }]
    packet = build_context_packet(request, entries)
    require(packet["selected_item_count"] == 1, "validation packet did not select expected entry")
    require(packet["authority_effect"] == "NONE_CONTEXT_ONLY", "context packet authority effect invalid")
    proposal = build_write_proposal(
        source_packet=packet,
        target_kv_instance_id="KV-VALIDATION-1",
        relative_path="01_Notes/continuity-result.md",
        content="Validated memory proposal.",
        retention_class="PROJECT",
    )
    require(proposal["execution_authorized"] is False, "write proposal unexpectedly authorized")
    require(proposal["authority_effect"] == "NONE_PROPOSAL_ONLY", "write proposal authority effect invalid")

    print("KV_AI_MEMORY_SUBSTRATE_VALIDATION=PASS")


if __name__ == "__main__":
    main()
