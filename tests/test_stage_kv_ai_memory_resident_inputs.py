from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.stage_kv_ai_memory_resident_inputs import stage


def request():
    return {
        "schema": "stegverse.kv.ai-memory-context-request/v1",
        "request_id": "REQ-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "consumer_ai_role": "PERSONAL_ASSISTANT_AI",
        "source_kv_instance_ids": ["KV-1"],
        "query_terms": ["continuity"],
        "purpose": "recover continuity context",
        "max_items": 5,
        "max_bytes": 4096,
        "intr_admission_required": True,
        "authority_effect": "NONE_CONTEXT_REQUEST_ONLY",
    }


def entries():
    return [{
        "entry_id": "E-1",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "source_kv_instance_id": "KV-1",
        "relative_path": "01_Notes/continuity.md",
        "title": "Continuity",
        "content": "Persistent continuity context.",
        "tags": ["continuity"],
        "retention_class": "DURABLE",
        "provenance_ref": "P-1",
        "ai_context_allowed": True,
        "secret_material": False,
        "priority": 1,
    }]


def provider_input():
    return {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "created_at": "2026-09-14T03:45:00+00:00",
        "messages": [{"role": "user", "content": "Continue from my durable context."}],
        "purpose": "answer",
        "allowed_sources": ["model_knowledge"],
        "temperature": 0.0,
    }


def test_stage_writes_packet_and_request_but_never_fabricates_admission(tmp_path):
    result = stage(request=request(), entries=entries(), provider_request_input=provider_input(), stage_root=tmp_path)
    assert result["state"] == "PRIVATE_INPUTS_STAGED_AWAITING_INTR_ADMISSION"
    assert (tmp_path / "inputs/context-packet.json").is_file()
    assert (tmp_path / "inputs/provider-request-input.json").is_file()
    assert not (tmp_path / "inputs/memory-packet-admission.json").exists()
    assert result["memory_packet_admission_present"] is False
    assert result["intr_admission_decided"] is False
    assert result["provider_request_materialized"] is False
    assert result["provider_execution_observed"] is False
    assert result["kv_writeback_observed"] is False
    assert result["credential_material_present"] is False
    assert result["authority_effect"] == "NONE_PRIVATE_STAGING_ONLY"


def test_stage_rejects_credential_like_provider_input(tmp_path):
    bad = provider_input()
    bad["metadata"] = {"api_key": "forbidden"}
    with pytest.raises(ValueError, match="credential-like field forbidden"):
        stage(request=request(), entries=entries(), provider_request_input=bad, stage_root=tmp_path)


def test_stage_rejects_empty_selection(tmp_path):
    req = request()
    req["query_terms"] = ["no-match"]
    with pytest.raises(ValueError, match="selected no AI-eligible"):
        stage(request=req, entries=entries(), provider_request_input=provider_input(), stage_root=tmp_path)


def test_stage_fails_closed_on_secret_eligible_entry(tmp_path):
    secret = entries()
    secret[0]["secret_material"] = True
    with pytest.raises(Exception, match="secret material"):
        stage(request=request(), entries=secret, provider_request_input=provider_input(), stage_root=tmp_path)
