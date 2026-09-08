from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.kv_instance_relationships import transition_request
from runtime.kv_relationship_state_store import (
    KVRelationshipStateError,
    apply_admitted_transition,
    initialize_store,
    load_state,
    persist_transition_request,
)


def test_store_initializes_fail_closed(tmp_path: Path) -> None:
    state = initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    assert state["relationship"]["tier"] == "NOT_CONNECTED"
    assert state["governance_state"] == "NOT_CONNECTED"
    assert state["authority_effect"] == "NONE"
    assert state["activation_effect"] is False


def test_pending_request_can_be_persisted_without_runtime_effect(tmp_path: Path) -> None:
    initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="NOT_CONNECTED",
        target_tier="CONNECTED",
    )
    path = persist_transition_request(tmp_path, request)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["governance_state"] == "PENDING_INTERLOCK_INTR"
    assert saved["data_moved"] is False
    assert saved["replication_started"] is False
    assert saved["ai_corpus_exposed"] is False
    assert load_state(tmp_path)["relationship"]["tier"] == "NOT_CONNECTED"


def test_apply_rejects_unadmitted_transition(tmp_path: Path) -> None:
    initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="NOT_CONNECTED",
        target_tier="CONNECTED",
    )
    with pytest.raises(KVRelationshipStateError, match="ADMITTED"):
        apply_admitted_transition(
            tmp_path,
            request=request,
            admission={"governance_state": "PENDING_INTERLOCK_INTR", "request_id": request["request_id"]},
        )


def test_apply_requires_both_interlock_and_intr_receipts(tmp_path: Path) -> None:
    initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="NOT_CONNECTED",
        target_tier="CONNECTED",
    )
    with pytest.raises(KVRelationshipStateError, match="Interlock and InTr"):
        apply_admitted_transition(
            tmp_path,
            request=request,
            admission={
                "governance_state": "ADMITTED",
                "request_id": request["request_id"],
                "interlock_receipt_ref": "receipt://interlock/1",
            },
        )


def test_admitted_transition_materializes_state_and_receipt(tmp_path: Path) -> None:
    initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="NOT_CONNECTED",
        target_tier="CONNECTED",
    )
    next_state = apply_admitted_transition(
        tmp_path,
        request=request,
        admission={
            "governance_state": "ADMITTED",
            "request_id": request["request_id"],
            "interlock_receipt_ref": "receipt://interlock/1",
            "intr_receipt_ref": "receipt://intr/1",
            "authority_effect": "NONE",
        },
    )
    assert next_state["relationship"]["tier"] == "CONNECTED"
    assert next_state["governance_state"] == "ADMITTED"
    assert next_state["activation_effect"] is False
    receipt = tmp_path / "_System/Instances/Relationships/Receipts" / f"{request['request_id']}.json"
    assert receipt.is_file()


def test_state_cannot_skip_current_tier_binding(tmp_path: Path) -> None:
    initialize_store(tmp_path, kv_set_id="personal", instance_id="kvi_one")
    request = transition_request(
        kv_set_id="personal",
        participant_instance_ids=["kvi_one", "kvi_two"],
        current_tier="CONNECTED",
        target_tier="SYNCED",
    )
    with pytest.raises(KVRelationshipStateError, match="current tier"):
        apply_admitted_transition(
            tmp_path,
            request=request,
            admission={
                "governance_state": "ADMITTED",
                "request_id": request["request_id"],
                "interlock_receipt_ref": "receipt://interlock/2",
                "intr_receipt_ref": "receipt://intr/2",
            },
        )
