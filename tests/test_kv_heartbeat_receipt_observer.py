from __future__ import annotations

import copy

import pytest

from runtime.kv_heartbeat_receipt_observer import bind_observation


def receipt():
    return {
        "schema": "stegverse.kv.ai-memory-writeback-receipt/v1",
        "receipt_sha256": "a" * 64,
        "model_is_authority": False,
        "authority_effect": "NONE_RECEIPT_ONLY",
    }


def heartbeat():
    return {
        "observed_receipt_sha256": "a" * 64,
        "observed_at": "2026-09-14T04:00:00Z",
        "freshness_state": "FRESH",
        "carrier_ref": "HB32:fixture",
        "heartbeat_grants_execution_authority": False,
        "heartbeat_grants_transition_authority": False,
        "heartbeat_grants_state_authority": False,
    }


def test_verified_receipt_can_be_observed_without_authority():
    value = bind_observation(receipt=receipt(), heartbeat=heartbeat())
    assert value["timing_correlation_only"] is True
    assert value["kv_transition_verified_before_observation"] is True
    assert value["kv_state_mutation_performed"] is False
    assert value["admission_decision_performed"] is False
    assert value["receipt_minted_by_heartbeat"] is False
    assert value["authority_effect"] == "NONE_OBSERVATION_ONLY"


def test_receipt_hash_mismatch_fails():
    hb = heartbeat()
    hb["observed_receipt_sha256"] = "b" * 64
    with pytest.raises(Exception, match="hash mismatch"):
        bind_observation(receipt=receipt(), heartbeat=hb)


def test_heartbeat_execution_authority_fails():
    hb = heartbeat()
    hb["heartbeat_grants_execution_authority"] = True
    with pytest.raises(Exception, match="execution authority"):
        bind_observation(receipt=receipt(), heartbeat=hb)


def test_heartbeat_transition_authority_fails():
    hb = heartbeat()
    hb["heartbeat_grants_transition_authority"] = True
    with pytest.raises(Exception, match="transition authority"):
        bind_observation(receipt=receipt(), heartbeat=hb)


def test_heartbeat_state_authority_fails():
    hb = heartbeat()
    hb["heartbeat_grants_state_authority"] = True
    with pytest.raises(Exception, match="state authority"):
        bind_observation(receipt=receipt(), heartbeat=hb)


def test_authority_escalating_receipt_fails():
    bad = receipt()
    bad["authority_effect"] = "GRANT"
    with pytest.raises(Exception, match="receipt authority effect invalid"):
        bind_observation(receipt=bad, heartbeat=heartbeat())


def test_stale_receipt_may_be_observed_but_not_promoted():
    hb = heartbeat()
    hb["freshness_state"] = "STALE"
    value = bind_observation(receipt=receipt(), heartbeat=hb)
    assert value["freshness_state"] == "STALE"
    assert value["heartbeat_grants_state_authority"] is False
