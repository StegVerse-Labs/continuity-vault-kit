from pathlib import Path

import pytest

from execution.adapter import canonical_sha256
from execution.communication_runtime import (
    CommunicationRuntimeJournal,
    CommunicationRuntimeJournalError,
)
from execution.vault_store import KnowledgeVaultExecutionStore


def selection():
    value = {
        "attempt_id": "attempt:runtime:1",
        "policy_version": "stegtalk.cross-edge.v0.1",
        "posture": "AUTO",
        "recipient_state": "KNOWN",
        "candidate_set_sha256": "sha256:" + "1" * 64,
        "selected_edge_id": "edge:gateway",
        "selected_bearer": "stegtalk-ip",
        "primary_score": 10.0,
        "primary_score_components": {},
        "fallback_order": [{"edge_id": "edge:phone", "bearer": "sms", "score": 5.0}],
        "excluded_paths": [],
        "selected_advertisement_sha256": "sha256:" + "2" * 64,
        "decision_time": "2026-08-22T22:35:00Z",
        "multipath_authorized": False,
        "remote_edge_execution_authorized": True,
    }
    value["selection_sha256"] = canonical_sha256(value)
    return value


def lease():
    return {
        "attempt_id": "attempt:runtime:1",
        "edge_id": "edge:gateway",
        "lease_epoch": 1,
        "expires_at": "2026-08-22T22:45:00Z",
    }


def execution_receipt(*, key="idem:runtime:1", outcome="DELIVERED", side_effect_absence_confirmed=False):
    value = {
        "receipt_type": "EDGE_EXECUTION",
        "attempt_id": "attempt:runtime:1",
        "selection_sha256": selection()["selection_sha256"],
        "edge_id": "edge:gateway",
        "bearer": "stegtalk-ip",
        "idempotency_key": key,
        "lease_epoch": 1,
        "dispatch_state": "OBSERVED" if outcome == "DELIVERED" else "DISPATCHED",
        "outcome": outcome,
        "side_effect_absence_confirmed": side_effect_absence_confirmed,
        "observed_at": "2026-08-22T22:36:00Z",
    }
    value["receipt_sha256"] = canonical_sha256(value)
    return value


def journal(tmp_path: Path):
    return CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(tmp_path / "KnowledgeVault"))


def test_begin_persists_selection_and_lease_and_reconstructs(tmp_path):
    j = journal(tmp_path)
    stream_id = j.begin(selection=selection(), lease=lease())
    recovered = j.recover("attempt:runtime:1")
    assert stream_id == j.stream_id("attempt:runtime:1")
    assert recovered.selection == selection()
    assert recovered.lease == lease()
    assert recovered.execution_receipt is None


def test_execution_receipt_persists_and_reconstructs_after_new_store_instance(tmp_path):
    root = tmp_path / "KnowledgeVault"
    first = CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(root))
    first.record_execution(selection=selection(), lease=lease(), receipt=execution_receipt())

    restarted = CommunicationRuntimeJournal(KnowledgeVaultExecutionStore(root))
    recovered = restarted.recover("attempt:runtime:1")
    assert recovered.execution_receipt == execution_receipt()
    assert recovered.execution_receipt["outcome"] == "DELIVERED"


def test_same_execution_receipt_is_idempotent_in_durable_store(tmp_path):
    j = journal(tmp_path)
    receipt = execution_receipt()
    stream_id = j.record_execution(selection=selection(), lease=lease(), receipt=receipt)
    j.record_execution(selection=selection(), lease=lease(), receipt=receipt)
    attempts = j.store.read_stream("Attempts", stream_id)
    receipts = j.store.read_stream("Receipts", stream_id)
    assert len([row for row in attempts if row.get("record_type") == "EDGE_EXECUTION_OBSERVED"]) == 1
    assert len(receipts) == 2  # selection + one execution receipt


def test_idempotency_key_cannot_rebind_to_different_receipt(tmp_path):
    j = journal(tmp_path)
    j.record_execution(selection=selection(), lease=lease(), receipt=execution_receipt())
    different = execution_receipt(key="idem:runtime:1", outcome="FAILED", side_effect_absence_confirmed=True)
    with pytest.raises(CommunicationRuntimeJournalError, match="idempotency key already bound"):
        j.record_execution(selection=selection(), lease=lease(), receipt=different)


def test_wrong_selection_hash_is_rejected(tmp_path):
    bad = selection()
    bad["selection_sha256"] = "sha256:" + "f" * 64
    with pytest.raises(CommunicationRuntimeJournalError, match="selection receipt hash mismatch"):
        journal(tmp_path).begin(selection=bad, lease=lease())


def test_wrong_execution_edge_is_rejected(tmp_path):
    receipt = execution_receipt()
    receipt["edge_id"] = "edge:other"
    body = dict(receipt)
    body.pop("receipt_sha256")
    receipt["receipt_sha256"] = canonical_sha256(body)
    with pytest.raises(CommunicationRuntimeJournalError, match="execution edge does not match"):
        journal(tmp_path).record_execution(selection=selection(), lease=lease(), receipt=receipt)


def test_ambiguous_execution_cannot_claim_no_side_effect(tmp_path):
    receipt = execution_receipt(outcome="TIMEOUT_AFTER_DISPATCH", side_effect_absence_confirmed=True)
    with pytest.raises(CommunicationRuntimeJournalError, match="ambiguous dispatch"):
        journal(tmp_path).record_execution(selection=selection(), lease=lease(), receipt=receipt)


def test_recovery_record_cannot_grant_authority(tmp_path):
    j = journal(tmp_path)
    j.begin(selection=selection(), lease=lease())
    with pytest.raises(CommunicationRuntimeJournalError, match="recovery cannot grant new authority"):
        j.record_recovery(
            attempt_id="attempt:runtime:1",
            decision={"action": "TRY_FALLBACK", "reason": "TEST", "new_authority_granted": True},
        )


def test_recovery_record_round_trips_without_new_authority(tmp_path):
    j = journal(tmp_path)
    j.begin(selection=selection(), lease=lease())
    j.record_recovery(
        attempt_id="attempt:runtime:1",
        decision={
            "action": "VERIFY_EXTERNALLY",
            "reason": "AMBIGUOUS_AFTER_DISPATCH",
            "new_authority_granted": False,
        },
    )
    recovered = j.recover("attempt:runtime:1")
    assert recovered.recovery_records[0]["action"] == "VERIFY_EXTERNALLY"
    assert recovered.recovery_records[0]["new_authority_granted"] is False
