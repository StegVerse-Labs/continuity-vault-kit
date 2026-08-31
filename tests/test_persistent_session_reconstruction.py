from __future__ import annotations

import copy

import pytest

from runtime.persistent_session_reconstruction import (
    PersistentSessionError,
    build_reconstruction_projection,
    session_head_sha256,
    validate_session_head,
    verify_successor,
)


def head(generation=0, prior=None):
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
            "evidence_refs": ["github:StegVerse-Labs/continuity-vault-kit#142"],
            "last_verified_observations": [
                {
                    "subject": "continuity-vault-kit",
                    "state": "SOURCE_IMPLEMENTATION_IN_PROGRESS",
                    "observed_at": "2026-08-30T20:00:00Z",
                    "source_ref": "github:StegVerse-Labs/continuity-vault-kit#142",
                }
            ],
            "authorization_boundaries": [
                "TV/TVC credential authority",
                "live repo/runtime verification required",
            ],
            "next_executable_action": "Validate and merge the source slice.",
        },
        "provenance": {
            "client_class": "ECOSYSTEM_CHAT",
            "source_session_ref": "chat-session:opaque",
            "requires_live_verification": True,
        },
        "authority": {
            "authority_transfer": False,
            "execution_authority": "NONE",
            "credential_authority": "TV/TVC",
            "canonical_completion_claimed": False,
        },
    }


def test_valid_genesis_head_and_projection():
    value = head()
    assert validate_session_head(value) == value
    projection = build_reconstruction_projection(value)
    assert projection["head_sha256"] == session_head_sha256(value)
    assert projection["requires_live_verification"] is True
    assert projection["stored_state_is_authority"] is False
    assert projection["transcript_required"] is False


def test_successor_requires_exact_hash_and_generation():
    first = head()
    second = head(1, session_head_sha256(first))
    assert verify_successor(first, second)["generation"] == 1

    stale = copy.deepcopy(second)
    stale["generation"] = 2
    with pytest.raises(PersistentSessionError, match="generation discontinuity"):
        verify_successor(first, stale)

    wrong_hash = copy.deepcopy(second)
    wrong_hash["prior_head_sha256"] = "sha256:" + ("0" * 64)
    with pytest.raises(PersistentSessionError, match="predecessor hash mismatch"):
        verify_successor(first, wrong_hash)


def test_transcript_and_secret_like_fields_fail_closed():
    value = head()
    value["semantic_state"]["transcript"] = "raw chat content"
    with pytest.raises(PersistentSessionError):
        validate_session_head(value)

    value = head()
    value["semantic_state"]["last_verified_observations"][0]["token_hint"] = "forbidden"
    with pytest.raises(PersistentSessionError, match="forbidden field"):
        validate_session_head(value)


def test_authority_expansion_and_live_verification_disable_fail_closed():
    value = head()
    value["authority"]["execution_authority"] = "SESSION"
    with pytest.raises(PersistentSessionError, match="authority boundary mismatch"):
        validate_session_head(value)

    value = head()
    value["provenance"]["requires_live_verification"] = False
    with pytest.raises(PersistentSessionError, match="live verification"):
        validate_session_head(value)


def test_successor_timestamp_cannot_roll_back():
    first = head()
    second = head(1, session_head_sha256(first))
    second["created_at"] = "2026-08-30T19:59:59Z"
    with pytest.raises(PersistentSessionError, match="timestamp rollback"):
        verify_successor(first, second)
