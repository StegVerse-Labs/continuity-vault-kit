"""Continuity checkpoint delivery reader (Site#1509 WS-ASSISTANT delivery): read-only, verifier decision never ALLOW here."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.workspace_continuity_checkpoint import CHECKPOINT_SCHEMA, checkpoint_digest
from runtime.workspace_projection import WorkspaceProjectionError
from runtime.workspace_continuity_checkpoint_projection import DELIVERY_SCHEMA, get_personal_continuity_checkpoint

FIXED = datetime(2026, 10, 11, 16, 0, 0, tzinfo=timezone.utc)
REV = "a" * 64


def make(*, seq=0, epoch=0, grant=0, rev=REV, prev=None, observed="2026-10-10T12:00:00Z", principal="user:owner", workspace_id="ws:personal:owner", **extra):
    cp = {"schema": CHECKPOINT_SCHEMA, "principal_id": principal, "workspace_type": "PERSONAL", "workspace_id": workspace_id,
          "grant_epoch": grant, "source_epoch": epoch, "sequence": seq, "source_revision": rev, "previous_checkpoint_digest": prev,
          "observed_at": observed, "anchor": {"kind": "RECEIPT_REF", "ref": "receipt:%d:%d" % (epoch, seq)}, "authority_effect": "NONE", **extra}
    cp["checkpoint_digest"] = checkpoint_digest(cp)
    return cp


def write(root: Path, name: str, value) -> Path:
    p = root / "_System" / "Workspace" / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value, encoding="utf-8"); return p


def fixture(tmp_path, current=None, previous=None, context=True):
    root = tmp_path / "KnowledgeVault"; (root / "_System" / "Workspace").mkdir(parents=True)
    if context:
        write(root, "workspace.json", {"schema": "stegverse.kv.workspace-context/v1", "authority_effect": "NONE", "workspace_id": "ws:personal:owner", "owner_principal_id": "user:owner"})
    if current is not None:
        write(root, "continuity-checkpoint.json", current)
    if previous is not None:
        write(root, "continuity-checkpoint.previous.json", previous)
    return root


def digest_dir(root: Path) -> str:
    return hashlib.sha256(b"".join(sorted(p.read_bytes() for p in root.rglob("*") if p.is_file()))).hexdigest()


def test_first_checkpoint_is_delivered_with_an_unverified_decision(tmp_path):
    first = make(); root = fixture(tmp_path, current=first); before = digest_dir(root)
    d = get_personal_continuity_checkpoint(kv_data_root=root, clock=lambda: FIXED)
    assert digest_dir(root) == before
    assert d["schema"] == DELIVERY_SCHEMA and d["state"] == "KV_CHECKPOINT_PROJECTED" and d["checkpoint"] == first and d["anchor_verified"] is False
    dec = d["decision"]
    assert dec["schema"] == "stegverse.kv.workspace-continuity-checkpoint-decision/v1" and dec["disposition"] == "FAIL_CLOSED"
    assert dec["predicate"] == "CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE:FIRST_CHECKPOINT" and dec["replay_status"] == "UNKNOWN" and dec["authority_effect"] == "NONE"
    assert d["action_authority"] == "NONE" and d["workspace_grants_authority"] is False and d["projection_metadata"]["owner_principal_id"] == "user:owner"
    assert get_personal_continuity_checkpoint(kv_data_root=root, clock=lambda: FIXED) == d


def test_linked_advance_and_chain_faults_follow_the_verifier(tmp_path):
    first = make(); second = make(seq=1, rev="b" * 64, prev=first["checkpoint_digest"], observed="2026-10-10T13:00:00Z")
    d = get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "ok", current=second, previous=first), clock=lambda: FIXED)
    assert d["decision"]["predicate"] == "CHECKPOINT_ANCHOR_VERIFIER_UNAVAILABLE:SEQUENCE_ADVANCED" and d["decision"]["disposition"] == "FAIL_CLOSED"
    fork = make(seq=1, rev="c" * 64, prev="d" * 64, observed="2026-10-10T13:00:00Z")
    d = get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "fork", current=fork, previous=first), clock=lambda: FIXED)
    assert d["decision"]["disposition"] == "DENY" and d["decision"]["predicate"] == "CHECKPOINT_FORK" and d["decision"]["replay_status"] == "REFUSED"
    other = make(principal="user:other")
    d = get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "other", current=other), clock=lambda: FIXED)
    assert d["decision"]["disposition"] == "DENY" and d["decision"]["predicate"] == "CHECKPOINT_CONTEXT_MISMATCH"
    tampered = dict(first, observed_at="2026-10-10T12:00:01Z")
    d = get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "tamper", current=tampered), clock=lambda: FIXED)
    assert d["decision"]["disposition"] == "FAIL_CLOSED" and d["decision"]["predicate"].startswith("CHECKPOINT_MALFORMED:checkpoint_digest_mismatch")


def test_absent_checkpoint_is_a_valid_absent_delivery_and_file_faults_fail_closed(tmp_path):
    d = get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "absent"), clock=lambda: FIXED)
    assert d["state"] == "KV_CHECKPOINT_ABSENT" and d["checkpoint"] is None and d["decision"] is None
    cases = [
        (dict(current=None, previous=make()), "checkpoint_previous_without_current"),
        (dict(current="{not json"), "checkpoint_file_unreadable:continuity-checkpoint.json"),
        (dict(current=[1]), "checkpoint_file_object_required:continuity-checkpoint.json"),
        (dict(current=dict(make(), schema="other/v1")), "checkpoint_file_schema_invalid:continuity-checkpoint.json"),
        (dict(current=make(api_token="x")), "secret_field_forbidden:continuity-checkpoint.json.api_token"),
        (dict(current=make(), context=False), "checkpoint_context_owner_required"),
    ]
    for kw, reason in cases:
        root = fixture(tmp_path / reason.replace(":", "_").replace(".", "_"), **kw)
        with pytest.raises(WorkspaceProjectionError) as exc:
            get_personal_continuity_checkpoint(kv_data_root=root, clock=lambda: FIXED)
        assert str(exc.value) == reason, (reason, str(exc.value))
    with pytest.raises(WorkspaceProjectionError, match="projection_clock_must_be_timezone_aware"):
        get_personal_continuity_checkpoint(kv_data_root=fixture(tmp_path / "clock", current=make()), clock=lambda: datetime(2026, 10, 11))
