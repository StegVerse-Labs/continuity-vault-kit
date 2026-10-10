"""Workspace continuity checkpoint contract and transition verifier (Site#1509 P5).

Pure and storage-free: this module defines ``stegverse.kv.workspace-continuity-checkpoint/v1``
and decides whether a checkpoint may follow the last accepted one. It writes nothing, holds no
keys and grants no authority. Producing and persisting checkpoints (registry decision
BLK3-WORKSPACE-KV-STORE-WRITER) and anchoring them in a receipt or signature (owner-side) are
out of scope, so callers must supply an anchor verifier; without one, replay status is never
VERIFIED.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

CHECKPOINT_SCHEMA = "stegverse.kv.workspace-continuity-checkpoint/v1"
RESULT_SCHEMA = "stegverse.kv.workspace-continuity-checkpoint-decision/v1"
WORKSPACE_TYPES = {"PERSONAL", "ORGANIZATIONAL"}
ANCHOR_KINDS = {"RECEIPT_REF", "SIGNATURE"}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = {
    "schema", "principal_id", "workspace_type", "workspace_id", "grant_epoch", "source_epoch",
    "sequence", "source_revision", "previous_checkpoint_digest", "observed_at", "anchor",
    "checkpoint_digest", "authority_effect",
}

class CheckpointError(ValueError): pass

def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def checkpoint_digest(checkpoint: dict[str, Any]) -> str:
    """SHA-256 over the canonical checkpoint without its own digest field."""
    body = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
    return hashlib.sha256(_canonical(body)).hexdigest()

def _nonneg_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

def validate_checkpoint(cp: Any) -> dict[str, Any]:
    if not isinstance(cp, dict): raise CheckpointError("checkpoint_object_required")
    extra = sorted(set(cp) - _FIELDS)
    if extra: raise CheckpointError("checkpoint_field_forbidden:" + extra[0])
    if cp.get("schema") != CHECKPOINT_SCHEMA: raise CheckpointError("checkpoint_schema_invalid")
    if cp.get("authority_effect") != "NONE": raise CheckpointError("checkpoint_authority_invalid")
    if not isinstance(cp.get("principal_id"), str) or not cp["principal_id"]: raise CheckpointError("checkpoint_principal_required")
    if cp.get("workspace_type") not in WORKSPACE_TYPES: raise CheckpointError("checkpoint_workspace_type_invalid")
    if cp.get("workspace_id") is not None and (not isinstance(cp["workspace_id"], str) or not cp["workspace_id"]): raise CheckpointError("checkpoint_workspace_id_invalid")
    for key in ("grant_epoch", "source_epoch", "sequence"):
        if not _nonneg_int(cp.get(key)): raise CheckpointError("checkpoint_" + key + "_invalid")
    if not isinstance(cp.get("source_revision"), str) or not _HEX64.match(cp["source_revision"]): raise CheckpointError("checkpoint_source_revision_invalid")
    prev = cp.get("previous_checkpoint_digest")
    if prev is not None and (not isinstance(prev, str) or not _HEX64.match(prev)): raise CheckpointError("checkpoint_previous_digest_invalid")
    if not isinstance(cp.get("observed_at"), str) or not cp["observed_at"]: raise CheckpointError("checkpoint_observed_at_required")
    anchor = cp.get("anchor")
    if not isinstance(anchor, dict) or anchor.get("kind") not in ANCHOR_KINDS or not isinstance(anchor.get("ref"), str) or not anchor["ref"]:
        raise CheckpointError("checkpoint_anchor_invalid")
    if cp.get("checkpoint_digest") != checkpoint_digest(cp): raise CheckpointError("checkpoint_digest_mismatch")
    return cp

def _decision(disposition: str, predicate: str, *, replay_status: str) -> dict[str, Any]:
    return {"schema": RESULT_SCHEMA, "disposition": disposition, "predicate": predicate,
            "replay_status": replay_status, "authority_effect": "NONE"}

def verify_transition(
    previous: dict[str, Any] | None,
    current: Any,
    *,
    principal_id: str,
    workspace_type: str,
    workspace_id: str | None,
    revoked_grant_epochs: frozenset[int] | set[int] = frozenset(),
    anchor_verifier: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Decide whether ``current`` may follow ``previous`` (the last accepted checkpoint, or None).

    Ordering is by (source_epoch, sequence) and digest links, never by wall clock, so clock
    regression is tolerated. A producer restart increments source_epoch, resets sequence to 0
    and links to the last accepted digest. The producing device is not part of the binding.
    """
    try: cur = validate_checkpoint(current)
    except CheckpointError as exc: return _decision("FAIL_CLOSED", "CHECKPOINT_MALFORMED:" + str(exc), replay_status="REFUSED")
    if previous is not None:
        try: validate_checkpoint(previous)
        except CheckpointError as exc: return _decision("FAIL_CLOSED", "PREVIOUS_CHECKPOINT_MALFORMED:" + str(exc), replay_status="UNKNOWN")
    if (cur["principal_id"], cur["workspace_type"], cur["workspace_id"]) != (principal_id, workspace_type, workspace_id):
        return _decision("DENY", "CHECKPOINT_CONTEXT_MISMATCH", replay_status="REFUSED")
    if cur["grant_epoch"] in revoked_grant_epochs:
        return _decision("DENY", "CHECKPOINT_GRANT_REVOKED", replay_status="REFUSED")
    linked = "FIRST_CHECKPOINT"
    if previous is not None:
        if (previous["principal_id"], previous["workspace_type"], previous["workspace_id"]) != (principal_id, workspace_type, workspace_id):
            return _decision("FAIL_CLOSED", "PREVIOUS_CHECKPOINT_CONTEXT_MISMATCH", replay_status="UNKNOWN")
        if cur["grant_epoch"] < previous["grant_epoch"]:
            return _decision("DENY", "CHECKPOINT_GRANT_EPOCH_REGRESSED", replay_status="REFUSED")
        if cur["source_epoch"] < previous["source_epoch"]:
            return _decision("DENY", "CHECKPOINT_SOURCE_EPOCH_REGRESSED", replay_status="REFUSED")
        if cur["source_epoch"] > previous["source_epoch"]:
            if cur["sequence"] != 0 or cur["previous_checkpoint_digest"] != previous["checkpoint_digest"]:
                return _decision("DENY", "CHECKPOINT_RESTART_UNLINKED", replay_status="REFUSED")
            linked = "VALID_RESTART"
        elif cur["sequence"] == previous["sequence"]:
            if cur["checkpoint_digest"] != previous["checkpoint_digest"]:
                return _decision("DENY", "CHECKPOINT_FORK", replay_status="REFUSED")
            linked = "IDEMPOTENT_REOBSERVATION"
        elif cur["sequence"] < previous["sequence"]:
            return _decision("DENY", "CHECKPOINT_REPLAY_OR_ROLLBACK", replay_status="REFUSED")
        elif cur["sequence"] > previous["sequence"] + 1:
            return _decision("FAIL_CLOSED", "CHECKPOINT_CHAIN_GAP", replay_status="UNKNOWN")
        elif cur["previous_checkpoint_digest"] != previous["checkpoint_digest"]:
            return _decision("DENY", "CHECKPOINT_FORK", replay_status="REFUSED")
        else:
            linked = "SEQUENCE_ADVANCED"
    elif cur["source_epoch"] != 0 or cur["sequence"] != 0 or cur["previous_checkpoint_digest"] is not None:
        # Without a prior accepted checkpoint, a mid-chain checkpoint cannot be ordered.
        return _decision("FAIL_CLOSED", "CHECKPOINT_PRIOR_UNKNOWN", replay_status="UNKNOWN")
    if anchor_verifier is None:
        return _decision("FAIL_CLOSED", "CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE:" + linked, replay_status="UNKNOWN")
    try: anchored = anchor_verifier(cur["anchor"]) is True
    except Exception: anchored = False
    if not anchored:
        return _decision("FAIL_CLOSED", "CHECKPOINT_ANCHOR_UNVERIFIED:" + linked, replay_status="UNKNOWN")
    return _decision("ALLOW", linked, replay_status="VERIFIED")
