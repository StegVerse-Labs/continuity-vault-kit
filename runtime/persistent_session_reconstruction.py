from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


SCHEMA = "stegverse.kv.persistent-session-head/v1"
ALLOWED_CLIENT_CLASSES = {
    "ECOSYSTEM_CHAT",
    "COMPATIBLE_LLM_CLIENT",
    "STEGOS_DEVICE_CLIENT",
    "WORKER_COORDINATOR",
}
FORBIDDEN_FIELD_TOKENS = {
    "password",
    "secret",
    "credential_value",
    "token",
    "cookie",
    "private_key",
    "seed",
    "mnemonic",
    "recovery_code",
    "raw_biometric",
    "transcript",
    "raw_message",
    "conversation_dump",
}


class PersistentSessionError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_uri(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _is_sha256_uri(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 71
        and value.startswith("sha256:")
        and all(ch in "0123456789abcdef" for ch in value[7:])
    )


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise PersistentSessionError("timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PersistentSessionError("invalid timestamp") from exc
    if parsed.tzinfo is None:
        raise PersistentSessionError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _unique_strings(value: Any, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise PersistentSessionError(f"{field} must be unique non-empty strings")
    return value


def _contains_forbidden_key(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in FORBIDDEN_FIELD_TOKENS)


def _reject_forbidden_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise PersistentSessionError(f"non-string field at {path}")
            if _contains_forbidden_key(key):
                raise PersistentSessionError(f"forbidden field at {path}.{key}")
            _reject_forbidden_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_fields(child, f"{path}[{index}]")


def _validate_observations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise PersistentSessionError("last_verified_observations must be an array")
    allowed = {"subject", "state", "observed_at", "source_ref"}
    for item in value:
        if not isinstance(item, dict) or set(item) != allowed:
            raise PersistentSessionError("observation shape invalid")
        if any(not isinstance(item[key], str) or not item[key] for key in ("subject", "state", "source_ref")):
            raise PersistentSessionError("observation text fields required")
        _parse_time(item["observed_at"])
    return value


def validate_session_head(head: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(head, dict):
        raise PersistentSessionError("session head must be an object")
    _reject_forbidden_fields(head)

    required = {
        "schema",
        "session_id",
        "generation",
        "prior_head_sha256",
        "created_at",
        "semantic_state",
        "provenance",
        "authority",
    }
    if set(head) != required:
        raise PersistentSessionError("session head fields invalid")
    if head["schema"] != SCHEMA:
        raise PersistentSessionError("schema mismatch")
    if not isinstance(head["session_id"], str) or not head["session_id"]:
        raise PersistentSessionError("session_id required")
    if not isinstance(head["generation"], int) or head["generation"] < 0:
        raise PersistentSessionError("generation invalid")
    if head["generation"] == 0:
        if head["prior_head_sha256"] is not None:
            raise PersistentSessionError("genesis head cannot have predecessor")
    elif not _is_sha256_uri(head["prior_head_sha256"]):
        raise PersistentSessionError("successor predecessor hash required")
    _parse_time(head["created_at"])

    state = head["semantic_state"]
    state_fields = {
        "active_goals",
        "authoritative_repositories",
        "handoff_refs",
        "blockers",
        "machine_task_refs",
        "evidence_refs",
        "last_verified_observations",
        "authorization_boundaries",
        "next_executable_action",
    }
    if not isinstance(state, dict) or set(state) != state_fields:
        raise PersistentSessionError("semantic_state fields invalid")
    for field in (
        "active_goals",
        "authoritative_repositories",
        "handoff_refs",
        "blockers",
        "machine_task_refs",
        "evidence_refs",
        "authorization_boundaries",
    ):
        _unique_strings(state[field], field)
    _validate_observations(state["last_verified_observations"])
    if not isinstance(state["next_executable_action"], str) or not state["next_executable_action"]:
        raise PersistentSessionError("next_executable_action required")

    provenance = head["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "client_class",
        "source_session_ref",
        "conversation_event_chain_ref",
        "conversation_event_verification_root",
        "requires_live_verification",
    }:
        raise PersistentSessionError("provenance invalid")
    if provenance["client_class"] not in ALLOWED_CLIENT_CLASSES:
        raise PersistentSessionError("client_class invalid")
    if not isinstance(provenance["source_session_ref"], str) or not provenance["source_session_ref"]:
        raise PersistentSessionError("source_session_ref required")
    if not isinstance(provenance["conversation_event_chain_ref"], str) or not provenance["conversation_event_chain_ref"]:
        raise PersistentSessionError("conversation_event_chain_ref required")
    root = provenance["conversation_event_verification_root"]
    if not (
        isinstance(root, str)
        and len(root) == 64
        and all(ch in "0123456789abcdef" for ch in root)
    ):
        raise PersistentSessionError("conversation_event_verification_root invalid")
    if provenance["requires_live_verification"] is not True:
        raise PersistentSessionError("live verification must be required")

    if head["authority"] != {
        "authority_transfer": False,
        "execution_authority": "NONE",
        "credential_authority": "TV/TVC",
        "canonical_completion_claimed": False,
    }:
        raise PersistentSessionError("authority boundary mismatch")

    return copy.deepcopy(head)


def session_head_sha256(head: dict[str, Any]) -> str:
    return sha256_uri(validate_session_head(head))


def verify_successor(prior: dict[str, Any], successor: dict[str, Any]) -> dict[str, Any]:
    prior_valid = validate_session_head(prior)
    successor_valid = validate_session_head(successor)
    if successor_valid["session_id"] != prior_valid["session_id"]:
        raise PersistentSessionError("session_id drift")
    if successor_valid["generation"] != prior_valid["generation"] + 1:
        raise PersistentSessionError("generation discontinuity")
    if successor_valid["prior_head_sha256"] != sha256_uri(prior_valid):
        raise PersistentSessionError("predecessor hash mismatch")
    if _parse_time(successor_valid["created_at"]) < _parse_time(prior_valid["created_at"]):
        raise PersistentSessionError("successor timestamp rollback")
    return successor_valid


def build_reconstruction_projection(head: dict[str, Any]) -> dict[str, Any]:
    valid = validate_session_head(head)
    return {
        "schema": "stegverse.kv.session-reconstruction-projection/v1",
        "session_id": valid["session_id"],
        "generation": valid["generation"],
        "head_sha256": sha256_uri(valid),
        "active_goals": list(valid["semantic_state"]["active_goals"]),
        "authoritative_repositories": list(valid["semantic_state"]["authoritative_repositories"]),
        "handoff_refs": list(valid["semantic_state"]["handoff_refs"]),
        "blockers": list(valid["semantic_state"]["blockers"]),
        "machine_task_refs": list(valid["semantic_state"]["machine_task_refs"]),
        "evidence_refs": list(valid["semantic_state"]["evidence_refs"]),
        "last_verified_observations": copy.deepcopy(valid["semantic_state"]["last_verified_observations"]),
        "authorization_boundaries": list(valid["semantic_state"]["authorization_boundaries"]),
        "next_executable_action": valid["semantic_state"]["next_executable_action"],
        "conversation_event_chain_ref": valid["provenance"]["conversation_event_chain_ref"],
        "conversation_event_verification_root": valid["provenance"]["conversation_event_verification_root"],
        "requires_live_verification": True,
        "stored_state_is_authority": False,
        "transcript_required": False,
        "execution_authority": "NONE",
        "credential_authority": "TV/TVC",
        "authority_effect": "NONE",
    }
