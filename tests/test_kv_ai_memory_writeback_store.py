from __future__ import annotations

import json

import pytest

from runtime.kv_ai_memory_substrate import build_write_proposal
from runtime.kv_ai_memory_writeback_store import apply_admitted_writeback


def source_packet():
    return {
        "schema": "stegverse.kv.ai-memory-context-packet/v1",
        "packet_id": "KVMEM-source-001",
        "kv_class": "PERSONAL_KV",
        "authority_domain": "PERSON",
        "model_is_authority": False,
        "authority_effect": "NONE_CONTEXT_ONLY",
    }


def prepare_kv(tmp_path):
    root = tmp_path / "KnowledgeVault"
    record = root / "_System/Instances/instance.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({
        "schema": "stegverse.kv.instance/v1",
        "instance_id": "kvi_test001",
        "instance_number": 1,
        "kv_set_id": "personal",
    }) + "\n", encoding="utf-8")
    return root


def proposal():
    return build_write_proposal(
        source_packet=source_packet(),
        target_kv_instance_id="kvi_test001",
        relative_path="01_Notes/remembered-next.md",
        content="Remember this only after governed target-KV admission.",
        retention_class="DURABLE",
    )


def admission(value):
    return {
        "governance_state": "ADMITTED",
        "disposition": "ALLOW",
        "proposal_id": value["proposal_id"],
        "target_kv_instance_id": value["target_kv_instance_id"],
        "content_sha256": value["content_sha256"],
        "persistence_authorized": True,
        "interlock_receipt_ref": "receipt://interlock/write-001",
        "intr_receipt_ref": "receipt://intr/write-001",
        "credential_material_present": False,
        "authority_effect": "NONE",
    }


def test_admitted_writeback_materializes_and_reads_back_exact_bytes(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    receipt = apply_admitted_writeback(root, proposal=p, admission=admission(p))
    assert (root / p["relative_path"]).read_text(encoding="utf-8") == p["content"]
    assert receipt["persistence_performed"] is True
    assert receipt["exact_byte_readback_verified"] is True
    assert receipt["content_sha256"] == receipt["readback_sha256"]
    assert receipt["model_is_authority"] is False
    assert receipt["authority_effect"] == "NONE_RECEIPT_ONLY"


def test_writeback_is_idempotent_for_exact_same_bytes(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    first = apply_admitted_writeback(root, proposal=p, admission=admission(p))
    second = apply_admitted_writeback(root, proposal=p, admission=admission(p))
    assert first["materialization_disposition"] == "MATERIALIZED_NEW_EXACT_BYTES"
    assert second["materialization_disposition"] == "IDEMPOTENT_EXISTING_EXACT_BYTES"


def test_writeback_rejects_missing_admission(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    bad = admission(p)
    bad["disposition"] = "DENY"
    with pytest.raises(Exception, match="must be ALLOW"):
        apply_admitted_writeback(root, proposal=p, admission=bad)
    assert not (root / p["relative_path"]).exists()


def test_writeback_rejects_content_hash_mismatch(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    bad = admission(p)
    bad["content_sha256"] = "0" * 64
    with pytest.raises(Exception, match="content hash mismatch"):
        apply_admitted_writeback(root, proposal=p, admission=bad)


def test_writeback_rejects_wrong_target_instance(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    p["target_kv_instance_id"] = "kvi_wrong"
    bad = admission(p)
    with pytest.raises(Exception, match="target KV instance binding mismatch"):
        apply_admitted_writeback(root, proposal=p, admission=bad)


def test_writeback_rejects_collision_with_different_bytes(tmp_path):
    root = prepare_kv(tmp_path)
    p = proposal()
    target = root / p["relative_path"]
    target.parent.mkdir(parents=True)
    target.write_text("different bytes", encoding="utf-8")
    with pytest.raises(Exception, match="collision"):
        apply_admitted_writeback(root, proposal=p, admission=admission(p))
