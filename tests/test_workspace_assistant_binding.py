import copy, json
from datetime import datetime, timezone
from pathlib import Path

from runtime.workspace_assistant_binding import BINDING_SCHEMA, resolve_assistant_binding
from runtime.workspace_projection import get_personal_workspace_projection

FIXED = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]
CTX = {"principal_id": "user:owner", "workspace_type": "PERSONAL", "workspace_id": "ws:personal:owner"}

def write(root, name, value):
    p = root / "_System" / "Workspace" / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value), encoding="utf-8")

def produced(tmp_path, *, assistant=True, owner="user:owner", extra_principals=()):
    root = tmp_path / "KnowledgeVault"; (root / "_System").mkdir(parents=True)
    write(root, "workspace.json", {"schema": "stegverse.kv.workspace-context/v1", "authority_effect": "NONE", "workspace_id": "ws:personal:owner", "owner_principal_id": owner})
    write(root, "principals.json", {"schema": "stegverse.kv.workspace-principals/v1", "authority_effect": "NONE",
        "principals": [{"principal_id": "user:owner", "principal_type": "HUMAN", "display_name": "Owner"}, *extra_principals]})
    if assistant:
        write(root, "assistant.json", {"schema": "stegverse.kv.workspace-assistant/v1", "authority_effect": "NONE",
            "assistant": {"principal_id": "auri:primary", "principal_type": "AI_ENTITY", "display_name": "Auri", "roles": ["WORKSPACE_ASSISTANT"]}})
    return get_personal_workspace_projection(kv_data_root=root, clock=lambda: FIXED)

def relationship(**over):
    rel = json.loads((ROOT / "fixtures/relationship-declarations/user-auri-v0.1.json").read_text(encoding="utf-8"))
    rel.update(over); return rel

def test_same_assistant_binds_from_real_producer_output(tmp_path):
    d = resolve_assistant_binding(produced(tmp_path), **CTX, relationship_declaration=relationship())
    b = d["binding"]
    assert d["schema"] == BINDING_SCHEMA and d["disposition"] == "ALLOW" and d["predicate"] == "MYKV_ASSISTANT_BOUND"
    assert d["action_eligible"] is False and d["authority_effect"] == "NONE" and d["generic_llm_fallback"] == "FORBIDDEN"
    assert b["assistant_principal_id"] == "auri:primary" and b["owner_principal_id"] == "user:owner" and b["relationship_state"] == "ACTIVE_DECLARED"
    assert b["continuity"]["key"] == {"owner_principal_id": "user:owner", "assistant_principal_id": "auri:primary", "workspace_id": "ws:personal:owner"}
    assert b["continuity"]["replay_status"] == "UNKNOWN" and b["invocation_route"] == "NOT_AVAILABLE" and b["ephemeral_inference"] == "NOT_AVAILABLE"
    assert len(b["continuity"]["source_revision"]) == 64

def test_binding_is_device_independent_and_deterministic(tmp_path):
    p = produced(tmp_path)
    assert resolve_assistant_binding(p, **CTX) == resolve_assistant_binding(copy.deepcopy(p), **CTX)
    assert "device" not in json.dumps(resolve_assistant_binding(p, **CTX)).lower()

def test_missing_assistant_fails_closed_without_generic_fallback(tmp_path):
    d = resolve_assistant_binding(produced(tmp_path, assistant=False), **CTX)
    assert d["disposition"] == "FAIL_CLOSED" and d["predicate"] == "MYKV_ASSISTANT_BINDING_ABSENT" and d["binding"] is None and d["generic_llm_fallback"] == "FORBIDDEN"

def test_other_user_and_other_workspace_are_denied(tmp_path):
    p = produced(tmp_path)
    assert resolve_assistant_binding(p, **dict(CTX, principal_id="user:other"))["predicate"] == "PROJECTION_OWNER_MISMATCH"
    assert resolve_assistant_binding(p, **dict(CTX, workspace_id="ws:personal:other"))["predicate"] == "PROJECTION_WORKSPACE_MISMATCH"
    assert resolve_assistant_binding(produced(tmp_path / "u", owner=None), **CTX)["predicate"] == "PROJECTION_OWNER_UNBOUND"
    assert resolve_assistant_binding(p, **dict(CTX, principal_id=""))["predicate"] == "SESSION_PRINCIPAL_UNAUTHENTICATED"

def test_org_context_does_not_reuse_personal_kv(tmp_path):
    d = resolve_assistant_binding(produced(tmp_path), **dict(CTX, workspace_type="ORGANIZATIONAL"))
    assert d["disposition"] == "FAIL_CLOSED" and d["predicate"] == "ORG_KV_ASSISTANT_CONTEXT_NOT_OBSERVED" and d["binding"] is None

def test_revoked_grant_denies(tmp_path):
    p = produced(tmp_path); p["projection_metadata"]["grant_state"] = "REVOKED"
    assert resolve_assistant_binding(p, **CTX)["disposition"] == "DENY"

def test_second_assistant_candidate_is_ambiguous(tmp_path):
    other = {"principal_id": "ai:other", "principal_type": "AI_ENTITY", "display_name": "Other", "roles": ["WORKSPACE_ASSISTANT"]}
    assert resolve_assistant_binding(produced(tmp_path, extra_principals=[other]), **CTX)["predicate"] == "MYKV_ASSISTANT_AMBIGUOUS"
    friend = {"principal_id": "ai:friend", "principal_type": "AI_ENTITY", "display_name": "Friend"}
    assert resolve_assistant_binding(produced(tmp_path / "f", extra_principals=[friend]), **CTX)["disposition"] == "ALLOW"

def test_relationship_must_match_parties_and_be_active(tmp_path):
    p = produced(tmp_path)
    assert resolve_assistant_binding(p, **CTX, relationship_declaration=relationship(ai_entity={"entity_id": "ai:other", "entity_type": "governed_ai"}))["predicate"] == "RELATIONSHIP_PARTIES_MISMATCH"
    paused = relationship(status="paused")
    assert resolve_assistant_binding(p, **CTX, relationship_declaration=paused)["predicate"] == "RELATIONSHIP_NOT_ACTIVE"
    assert resolve_assistant_binding(p, **CTX, relationship_declaration={"x": 1})["predicate"] == "RELATIONSHIP_DECLARATION_INVALID"

def test_malformed_or_authority_asserting_projection_fails_closed(tmp_path):
    p = produced(tmp_path)
    for bad in [None, "x", dict(p, schema="other"), dict(p, authority_effect="ALLOW"), dict(p, workspace_grants_authority=True), dict(p, projection_metadata=None),
                dict(p, assistant={"principal_id": "auri:primary", "principal_type": "HUMAN", "display_name": "A", "roles": ["WORKSPACE_ASSISTANT"]}),
                dict(p, assistant=dict(p["assistant"], principal_id="user:owner"))]:
        assert resolve_assistant_binding(bad, **CTX)["disposition"] == "FAIL_CLOSED"
