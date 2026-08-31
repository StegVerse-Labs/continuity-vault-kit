from __future__ import annotations

import copy

import pytest

from runtime.kv_interlock_endpoint import KVInterlockRuntime, sha256_uri
from runtime.persistent_session_interlock import (
    PersistentSessionCandidateStore,
    PersistentSessionInterlockError,
    PersistentSessionPolicyAdapter,
    session_head_destination,
)
from runtime.persistent_session_reconstruction import session_head_sha256


def make_head(generation=0, prior=None, recall_root=None):
    return {
        "schema": "stegverse.kv.persistent-session-head/v1",
        "session_id": "sv-session-001",
        "generation": generation,
        "prior_head_sha256": prior,
        "created_at": f"2026-08-30T20:0{generation}:00Z",
        "semantic_state": {
            "active_goals": ["KV persistent session reconstruction"],
            "authoritative_repositories": ["StegVerse-Labs/continuity-vault-kit"],
            "handoff_refs": ["KV_PERSISTENT_SESSION_RECONSTRUCTION_MIRROR_HANDOFF.md"],
            "blockers": ["DEVICE_KV_INTR runtime observation pending"],
            "machine_task_refs": ["SHWP-DEVICE-KV-INTR-OBSERVATION-001"],
            "evidence_refs": ["github:StegVerse-Labs/continuity-vault-kit#144"],
            "last_verified_observations": [
                {
                    "subject": "continuity-vault-kit",
                    "state": "SOURCE",
                    "observed_at": "2026-08-30T20:00:00Z",
                    "source_ref": "github:StegVerse-Labs/continuity-vault-kit#144",
                }
            ],
            "authorization_boundaries": ["live repo/runtime verification required"],
            "next_executable_action": "Continue admitted source integration.",
        },
        "provenance": {
            "client_class": "ECOSYSTEM_CHAT",
            "source_session_ref": "chat-session:opaque",
            "conversation_event_chain_ref": "_System/Continuity/Events/events.jsonl",
            "conversation_event_verification_root": recall_root or ("a" * 64),
            "requires_live_verification": True,
        },
        "authority": {
            "authority_transfer": False,
            "execution_authority": "NONE",
            "credential_authority": "TV/TVC",
            "canonical_completion_claimed": False,
        },
    }


def make_request(operation="REQUEST"):
    request = {
        "schema_version": "kv.interlock.request.v1",
        "operation": operation,
        "request_id": "req-session-001",
        "requester": {"module": "StegOS", "component": "PersistentSessionClient"},
        "purpose": "cold session reconstruction",
        "record_class": "persistent-session-head:sv-session-001",
        "requested_scope": ["session_head"] if operation == "REQUEST" else ["session_head_candidate"],
        "minimum_necessary_justification": "resume bounded work without transcript",
        "authority_ref": "owner-session:opaque",
        "disclosure_mode": "BOUNDED_CONTEXT",
    }
    if operation == "COMMIT_CANDIDATE":
        request["candidate_writeback"] = {
            "candidate_type": "persistent-session-head:sv-session-001",
            "payload_ref": "kv-candidate://session-successor",
            "requested_destination": session_head_destination("sv-session-001"),
        }
    return request


def make_envelope(request):
    return {
        "schema": "stegverse.kv-interlock.intr-envelope/v1",
        "protocol": "InTr",
        "packet_id": "packet-session-001",
        "direction": "REQUEST",
        "source_role": "DEVICE",
        "next_role": "KV",
        "request_id": request["request_id"],
        "operation": request["operation"],
        "payload_schema_version": "kv.interlock.request.v1",
        "payload_hash": sha256_uri(request),
        "sealed_material_ref": "sealed://opaque",
        "authority": {
            "authority_transfer": False,
            "transport_grants_execution_authority": False,
            "model_output_grants_execution_authority": False,
            "credential_authority_effect": "NONE",
        },
        "boundary_proof": {
            "required": True,
            "source_identity_ref": "node://device",
            "next_boundary_identity_ref": "kv://owner",
            "verification_state": "VERIFIED",
        },
        "receipt_policy": {
            "receipt_required": True,
            "receipt_contains_payload_plaintext": False,
            "receipt_chain_required": True,
            "ambiguous_disposition": "FAIL_CLOSED",
        },
    }


def test_request_returns_bounded_reconstruction_projection_through_existing_runtime():
    current = make_head()
    receipts = []
    runtime = KVInterlockRuntime(
        authority_validator=lambda *_: True,
        policy_evaluator=PersistentSessionPolicyAdapter(
            head_reader=lambda session_id: current if session_id == "sv-session-001" else None
        ),
        receipt_store=lambda receipt: receipts.append(receipt) or "receipt://session-read",
    )
    request = make_request()
    response = runtime.handle(
        request,
        intr_envelope=make_envelope(request),
        intr_receipt_ref="sha256:" + ("1" * 64),
    )
    assert response["decision"] == "ALLOW_BOUNDED_CONTEXT"
    projection = response["context"]["session_head"]
    assert projection["head_sha256"] == session_head_sha256(current)
    assert projection["requires_live_verification"] is True
    assert projection["stored_state_is_authority"] is False
    assert projection["transcript_required"] is False
    assert projection["execution_authority"] == "NONE"
    assert receipts[-1]["writeback_candidate_ref"] is None


def test_read_missing_head_denies_without_fabricating_state():
    policy = PersistentSessionPolicyAdapter(head_reader=lambda _: None)
    decision = policy(make_request())
    assert decision["decision"] == "DENY"
    assert decision["granted_scope"] == []
    assert decision["context"] == {}


def test_commit_candidate_stages_exact_successor_without_canonical_mutation():
    current = make_head()
    successor = make_head(1, session_head_sha256(current))
    staged = []
    store = PersistentSessionCandidateStore(
        head_reader=lambda _: current,
        payload_reader=lambda ref: successor,
        candidate_writer=lambda value: staged.append(value) or "candidate://staged/001",
    )
    receipts = []
    runtime = KVInterlockRuntime(
        authority_validator=lambda *_: True,
        policy_evaluator=PersistentSessionPolicyAdapter(head_reader=lambda _: current),
        candidate_store=store,
        receipt_store=lambda receipt: receipts.append(receipt) or "receipt://candidate",
    )
    request = make_request("COMMIT_CANDIDATE")
    response = runtime.handle(
        request,
        intr_envelope=make_envelope(request),
        intr_receipt_ref="sha256:" + ("2" * 64),
    )
    assert response["decision"] == "ALLOW_BOUNDED_CONTEXT"
    assert response["context"] == {}
    assert response["receipt"]["writeback_candidate_ref"] == "candidate://staged/001"
    assert staged[-1]["current_head_sha256"] == session_head_sha256(current)
    assert staged[-1]["successor_head_sha256"] == session_head_sha256(successor)
    assert staged[-1]["canonical_state_changed"] is False
    assert staged[-1]["execution_authority"] == "NONE"
    assert staged[-1]["credential_authority"] == "TV/TVC"


def test_stale_or_wrong_successor_fails_closed():
    current = make_head()
    bad = make_head(2, session_head_sha256(current))
    store = PersistentSessionCandidateStore(
        head_reader=lambda _: current,
        payload_reader=lambda _: bad,
        candidate_writer=lambda _: "candidate://must-not-write",
    )
    with pytest.raises(PersistentSessionInterlockError, match="successor rejected"):
        store(
            {
                "schema": "kv.interlock.candidate.v1",
                "request_id": "req",
                "authority_ref": "owner",
                "candidate_type": "persistent-session-head:sv-session-001",
                "payload_ref": "candidate://bad",
                "requested_destination": session_head_destination("sv-session-001"),
                "intr_receipt_ref": "sha256:" + ("3" * 64),
                "canonical_state_changed": False,
                "candidate_only": True,
                "authority_effect": "NONE",
            }
        )


def test_recall_root_advance_requires_explicit_validator():
    current = make_head()
    successor = make_head(1, session_head_sha256(current), recall_root="b" * 64)
    base_record = {
        "schema": "kv.interlock.candidate.v1",
        "request_id": "req",
        "authority_ref": "owner",
        "candidate_type": "persistent-session-head:sv-session-001",
        "payload_ref": "candidate://next",
        "requested_destination": session_head_destination("sv-session-001"),
        "intr_receipt_ref": "sha256:" + ("4" * 64),
        "canonical_state_changed": False,
        "candidate_only": True,
        "authority_effect": "NONE",
    }
    store = PersistentSessionCandidateStore(
        head_reader=lambda _: current,
        payload_reader=lambda _: successor,
        candidate_writer=lambda _: "candidate://staged",
    )
    with pytest.raises(PersistentSessionInterlockError, match="root advance not admitted"):
        store(copy.deepcopy(base_record))

    staged = []
    admitted = PersistentSessionCandidateStore(
        head_reader=lambda _: current,
        payload_reader=lambda _: successor,
        candidate_writer=lambda value: staged.append(value) or "candidate://staged",
        recall_root_validator=lambda prior, next_, chain: (
            prior == "a" * 64
            and next_ == "b" * 64
            and chain == "_System/Continuity/Events/events.jsonl"
        ),
    )
    assert admitted(copy.deepcopy(base_record)) == "candidate://staged"
    assert staged[-1]["conversation_event_verification_root"] == "b" * 64


def test_policy_rejects_destination_or_scope_drift():
    policy = PersistentSessionPolicyAdapter(head_reader=lambda _: make_head())
    request = make_request("COMMIT_CANDIDATE")
    request["candidate_writeback"]["requested_destination"] = "kv://wrong"
    with pytest.raises(PersistentSessionInterlockError, match="destination mismatch"):
        policy(request)

    request = make_request()
    request["requested_scope"] = ["session_head", "raw_messages"]
    with pytest.raises(PersistentSessionInterlockError, match="scope invalid"):
        policy(request)
