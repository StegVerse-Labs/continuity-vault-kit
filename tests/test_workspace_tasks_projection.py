"""Tasks/commitments projection producer (Site#1509 WS-TASKS): read-only fixture, provenance, revocation, no execution."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.workspace_projection import WorkspaceProjectionError
from runtime.workspace_tasks_projection import PROJECTION_SCHEMA, get_personal_tasks_projection

FIXED = datetime(2026, 10, 11, 1, 0, 0, tzinfo=timezone.utc)


def write(root: Path, name: str, value: dict) -> Path:
    p = root / "_System" / "Workspace" / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value, sort_keys=True), encoding="utf-8"); return p


def fixture(tmp_path, **over):
    root = tmp_path / "KnowledgeVault"; (root / "_System").mkdir(parents=True)
    write(root, "workspace.json", {"schema": "stegverse.kv.workspace-context/v1", "authority_effect": "NONE", "workspace_id": "ws:personal:owner", "owner_principal_id": "user:owner"})
    tasks = {"schema": "stegverse.kv.workspace-tasks/v1", "authority_effect": "NONE",
             "tasks": [{"task_id": "t-2", "title": "Review aurora release", "status": "OPEN", "due_at": "2026-10-12T09:00:00Z", "source_ref": "kv:tasks/t-2"},
                       {"task_id": "t-1", "title": "Undated chore", "status": "IN_PROGRESS"}],
             "commitments": [{"commitment_id": "c-1", "statement": "Send Alice the draft", "status": "ACTIVE", "counterparty_principal_id": "user:alice", "due_at": "2026-10-11T18:00:00Z"},
                             {"commitment_id": "c-2", "statement": "Old promise", "status": "REVOKED", "due_at": "2026-10-01T00:00:00Z"}]}
    tasks.update(over)
    write(root, "tasks.json", tasks)
    return root


def digest_dir(root: Path) -> str:
    return hashlib.sha256(b"".join(sorted(p.read_bytes() for p in root.rglob("*") if p.is_file()))).hexdigest()


def test_read_only_fixture_projects_rows_timeline_and_provenance(tmp_path):
    root = fixture(tmp_path); before = digest_dir(root)
    p = get_personal_tasks_projection(kv_data_root=root, clock=lambda: FIXED)
    assert digest_dir(root) == before, "producer must not write"
    assert p["schema"] == PROJECTION_SCHEMA and p["state"] == "KV_TASKS_PROJECTED" and p["workspace_type"] == "PERSONAL"
    assert [t["task_id"] for t in p["tasks"]] == ["t-2", "t-1"] and [c["commitment_id"] for c in p["commitments"]] == ["c-1", "c-2"]
    assert [i["id"] for i in p["timeline"]] == ["c-2", "c-1", "t-2", "t-1"], p["timeline"]
    assert all(row["action_eligible"] is False and row["execution_requires_admitted_manifest"] is True and row["authority_effect"] == "NONE" for row in p["tasks"] + p["commitments"] + p["timeline"])
    assert p["credential_material_present"] is False and p["provider_operation_authorized"] is False and p["workspace_grants_authority"] is False and p["action_authority"] == "NONE" and p["authority_effect"] == "NONE"
    m = p["projection_metadata"]
    assert m["schema"] == "stegverse.kv.workspace-projection-metadata/v1" and m["observed_at"] == "2026-10-11T01:00:00Z" and m["observed_at_semantics"] == "KV_PROJECTION_PRODUCTION_TIME"
    assert m["workspace_id"] == "ws:personal:owner" and m["owner_principal_id"] == "user:owner" and m["grant_state"] == "UNKNOWN" and m["revocation_epoch"] is None
    assert len(m["source_revision"]) == 64 and m["provenance_ref"] == "kv-workspace-tasks-source:sha256:" + m["source_revision"]


def test_provenance_tracks_exact_source_bytes(tmp_path):
    a = get_personal_tasks_projection(kv_data_root=fixture(tmp_path), clock=lambda: FIXED)
    b = get_personal_tasks_projection(kv_data_root=fixture(tmp_path / "again"), clock=lambda: FIXED)
    assert a == b, "deterministic over equal sources"
    c = get_personal_tasks_projection(kv_data_root=fixture(tmp_path / "changed", tasks=[{"task_id": "t-9", "title": "Other", "status": "OPEN"}]), clock=lambda: FIXED)
    assert c["projection_metadata"]["source_revision"] != a["projection_metadata"]["source_revision"]


def test_revoked_commitment_is_projected_as_revoked_never_hidden_or_acted_on(tmp_path):
    p = get_personal_tasks_projection(kv_data_root=fixture(tmp_path), clock=lambda: FIXED)
    revoked = [c for c in p["commitments"] if c["commitment_id"] == "c-2"][0]
    assert revoked["status"] == "REVOKED" and revoked["action_eligible"] is False
    assert any(i["id"] == "c-2" and i["status"] == "REVOKED" for i in p["timeline"])


def test_absent_tasks_file_is_empty(tmp_path):
    root = tmp_path / "KnowledgeVault"; (root / "_System").mkdir(parents=True)
    p = get_personal_tasks_projection(kv_data_root=root, clock=lambda: FIXED)
    assert p["state"] == "KV_TASKS_EMPTY" and p["tasks"] == [] and p["commitments"] == [] and p["timeline"] == []
    assert p["projection_metadata"]["owner_principal_id"] is None


@pytest.mark.parametrize("over,reason", [
    ({"tasks": [{"task_id": "t", "title": "x", "status": "EXECUTE_NOW"}]}, "task_status_invalid"),
    ({"tasks": [{"task_id": "", "title": "x", "status": "OPEN"}]}, "task_id_required"),
    ({"tasks": [{"task_id": "t", "title": "x", "status": "OPEN", "due_at": "tomorrow"}]}, "task_due_at_invalid"),
    ({"tasks": [{"task_id": "t", "title": "x", "status": "OPEN", "due_at": "2026-10-12T09:00:00"}]}, "task_due_at_timezone_required"),
    ({"commitments": [{"commitment_id": "c", "statement": "x", "status": "SIGNED"}]}, "commitment_status_invalid"),
    ({"tasks": [{"task_id": "dup", "title": "x", "status": "OPEN"}], "commitments": [{"commitment_id": "dup", "statement": "y", "status": "ACTIVE"}]}, "task_or_commitment_id_duplicate"),
    ({"tasks": [{"task_id": "t", "title": "x", "status": "OPEN", "api_token": "abc"}]}, "secret_field_forbidden"),
    ({"authority_effect": "ALLOW"}, "workspace_file_authority_invalid"),
    ({"schema": "stegverse.kv.other/v1"}, "workspace_file_schema_invalid"),
])
def test_malformed_sources_fail_closed(tmp_path, over, reason):
    with pytest.raises(WorkspaceProjectionError) as exc:
        get_personal_tasks_projection(kv_data_root=fixture(tmp_path, **over), clock=lambda: FIXED)
    assert reason in str(exc.value)


def test_naive_clock_fails_closed(tmp_path):
    with pytest.raises(WorkspaceProjectionError):
        get_personal_tasks_projection(kv_data_root=fixture(tmp_path), clock=lambda: datetime(2026, 10, 11))
