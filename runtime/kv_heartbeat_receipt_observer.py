"""Bind HeartBeat observations to already-verified KV transition receipts.

HeartBeat supplies timing/freshness/correlation only. This module cannot admit a
transition, mutate KV state, mint a transition receipt, or promote liveness into
execution/state authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "stegverse.kv.heartbeat-receipt-observation/v1"


class KVHeartbeatObservationError(ValueError):
    pass


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise KVHeartbeatObservationError(message)


def bind_observation(*, receipt: dict[str, Any], heartbeat: dict[str, Any]) -> dict[str, Any]:
    receipt_hash = receipt.get("receipt_sha256") or receipt.get("readback_sha256") or receipt.get("reconstruction_sha256")
    _require(isinstance(receipt_hash, str) and len(receipt_hash.replace("sha256:", "")) == 64, "verified KV receipt hash required")
    normalized_hash = receipt_hash.replace("sha256:", "")
    _require(receipt.get("authority_effect") in {"NONE", "NONE_RECEIPT_ONLY", "NONE_RECONSTRUCTION_PROOF_ONLY", "NONE_STATUS_ONLY"}, "KV receipt authority effect invalid")
    _require(receipt.get("model_is_authority") is not True, "KV receipt may not establish model authority")

    _require(heartbeat.get("heartbeat_grants_execution_authority") is False, "HeartBeat may not grant execution authority")
    _require(heartbeat.get("heartbeat_grants_transition_authority") is False, "HeartBeat may not grant transition authority")
    _require(heartbeat.get("heartbeat_grants_state_authority") is False, "HeartBeat may not grant KV state authority")
    _require(heartbeat.get("observed_receipt_sha256") == normalized_hash, "HeartBeat observed receipt hash mismatch")
    _require(isinstance(heartbeat.get("observed_at"), str) and heartbeat["observed_at"], "HeartBeat observed_at required")
    _require(heartbeat.get("freshness_state") in {"FRESH", "STALE", "UNKNOWN"}, "HeartBeat freshness_state invalid")

    result = {
        "schema": SCHEMA,
        "receipt_sha256": normalized_hash,
        "observed_at": heartbeat["observed_at"],
        "freshness_state": heartbeat["freshness_state"],
        "carrier_ref": heartbeat.get("carrier_ref"),
        "timing_correlation_only": True,
        "kv_transition_verified_before_observation": True,
        "heartbeat_grants_execution_authority": False,
        "heartbeat_grants_transition_authority": False,
        "heartbeat_grants_state_authority": False,
        "kv_state_mutation_performed": False,
        "admission_decision_performed": False,
        "receipt_minted_by_heartbeat": False,
        "authority_effect": "NONE_OBSERVATION_ONLY",
    }
    result["observation_sha256"] = canonical_hash(result)
    return result
