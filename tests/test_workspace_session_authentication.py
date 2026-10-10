"""Session-authentication contract (Site#1509 W4): producer-side mirror of Site assets/workspace-session-authentication.js."""
import copy, inspect, json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime import workspace_session_authentication as m
from runtime.workspace_assistant_binding import resolve_assistant_binding
from runtime.workspace_projection import get_personal_workspace_projection
from runtime.workspace_session_authentication import SESSION_AUTHENTICATION_SCHEMA, resolve_session_authentication

FIXED = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)


def receipt(**over):
    r = {"authenticated": True, "credential_authority": "TV/TVC", "receipt_ref": "tv-tvc:session-receipt:example", "principal_id": "user:owner", "authority_effect": "NONE"}
    r.update(over); return r


def session(**over):
    s = {"principal_id": "user:owner", "workspace_id": "ws:personal:owner", "source_class": "CALLER_AUTHENTICATION_RECEIPT", "authentication": receipt()}
    s.update(over); return s


def test_receipt_backed_session_is_admitted_without_any_evidence_claim():
    d = resolve_session_authentication(session())
    assert d["schema"] == SESSION_AUTHENTICATION_SCHEMA and d["disposition"] == "ALLOW" and d["predicate"] == "CALLER_AUTHENTICATION_RECEIPT_PRESENT"
    assert d["session"] == {"principal_id": "user:owner", "workspace_id": "ws:personal:owner", "source_class": "CALLER_AUTHENTICATION_RECEIPT", "receipt_ref": "tv-tvc:session-receipt:example", "credential_authority": "TV/TVC"}
    assert d["admission_class"] == "CALLER_SUPPLIED_FIELDS_ACCEPTED" and d["verification"] == "CALLER_SUPPLIED_NOT_PAGE_VERIFIED"
    assert d["runtime_authentication_evidence"] is False and d["identity_from_projection"] is False and d["action_eligible"] is False and d["authority_effect"] == "NONE"
    s = session(); del s["workspace_id"]
    assert resolve_session_authentication(s)["session"]["workspace_id"] is None


def test_contract_reads_the_session_only():
    sig = inspect.signature(resolve_session_authentication)
    assert list(sig.parameters) == ["session"], "projection, device and process state are never inputs"
    code = inspect.getsource(resolve_session_authentication) + inspect.getsource(m._decision)
    code = "\n".join(l for l in code.splitlines() if not l.strip().startswith("#"))
    for forbidden in ("projection_metadata", "owner_principal_id", "principals", "registration", "node_id", "os.environ", "getpass", "socket", "open("):
        assert forbidden not in code, forbidden
    assert not any(name in ("os", "sys", "socket", "json", "pathlib") for name in dir(m) if not name.startswith("_")), "no I/O modules imported"


@pytest.mark.parametrize("value,predicate", [
    (None, "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    ({}, "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    ("user:owner", "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    ({"principal_id": None, "workspace_id": None, "source_class": "NO_AUTHENTICATED_SESSION_PRINCIPAL", "authentication": None}, "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    ({"principal_id": "user:owner", "source_class": "NO_AUTHENTICATED_SESSION_PRINCIPAL"}, "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    # The projection owner is whose data was projected, never who the caller is.
    ({"principal_id": "user:owner", "source_class": "KV_PROJECTION_OWNER"}, "KV_OWNERSHIP_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "KV_PROJECTION_METADATA", "authentication": receipt()}, "KV_OWNERSHIP_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "KV_PROJECTION_PRINCIPAL"}, "KV_OWNERSHIP_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "KV_WORKSPACE_CONTEXT"}, "KV_OWNERSHIP_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "stegos-node://node-1", "source_class": "DEVICE_REGISTRATION"}, "DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "node-1", "source_class": "STEGOS_NODE_REGISTRATION"}, "DEVICE_REGISTRATION_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "BROWSER_STORAGE"}, "BROWSER_STATE_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "PAGE_STATE"}, "BROWSER_STATE_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "URL_PARAMETER"}, "BROWSER_STATE_IS_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "BOOTSTRAP_DATA"}, "BROWSER_STATE_IS_NOT_AUTHENTICATION"),
    # A bare principal_id, however it was obtained, is not authentication.
    ({"principal_id": "user:owner"}, "SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION"),
    ({"principal_id": "user:owner", "source_class": "TEST_INJECTED"}, "SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION"),
    ({"principal_id": "", "source_class": "CALLER_AUTHENTICATION_RECEIPT", "authentication": receipt()}, "SESSION_PRINCIPAL_UNAUTHENTICATED"),
    (session(authentication=None), "SESSION_AUTHENTICATION_RECEIPT_ABSENT"),
    (session(authentication="receipt"), "SESSION_AUTHENTICATION_RECEIPT_ABSENT"),
    (session(authentication=receipt(authenticated=False)), "SESSION_NOT_AUTHENTICATED"),
    (session(authentication=receipt(authenticated="true")), "SESSION_NOT_AUTHENTICATED"),
    (session(authentication=receipt(credential_authority="GITHUB_TOKEN")), "SESSION_CREDENTIAL_AUTHORITY_INVALID"),
    (session(authentication=receipt(receipt_ref="")), "SESSION_AUTHENTICATION_RECEIPT_REF_ABSENT"),
    (session(authentication=receipt(principal_id="user:other")), "SESSION_AUTHENTICATION_PRINCIPAL_MISMATCH"),
    (session(authentication=receipt(transaction_authority=True)), "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY"),
    (session(authentication=receipt(execution_authority=True)), "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY"),
    (session(authentication=receipt(delegation_authority=True)), "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY"),
    (session(authentication=receipt(authority_effect="ALLOW")), "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY"),
])
def test_refusals_match_site_predicates(value, predicate):
    d = resolve_session_authentication(value)
    assert d["disposition"] == "FAIL_CLOSED" and d["predicate"] == predicate and d["session"] is None
    assert d["action_eligible"] is False and d["runtime_authentication_evidence"] is False


def test_deterministic_and_input_untouched():
    s = session(); before = copy.deepcopy(s)
    assert resolve_session_authentication(s) == resolve_session_authentication(copy.deepcopy(s))
    assert s == before


def test_mirrors_site_module_predicate_names_when_site_checkout_is_present():
    # Optional cross-repository parity check: the Site module lists the same predicates and source classes.
    site = Path(__file__).resolve().parents[2] / "site" / "assets" / "workspace-session-authentication.js"
    if not site.exists():
        pytest.skip("Site checkout not present")
    js = site.read_text(encoding="utf-8")
    for key, pred in m.NON_AUTHENTICATION_SOURCES.items():
        assert f"{key}:\"{pred}\"" in js, key
    for pred in ("SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION", "SESSION_AUTHENTICATION_RECEIPT_ABSENT", "SESSION_NOT_AUTHENTICATED",
                 "SESSION_CREDENTIAL_AUTHORITY_INVALID", "SESSION_AUTHENTICATION_RECEIPT_REF_ABSENT", "SESSION_AUTHENTICATION_PRINCIPAL_MISMATCH",
                 "SESSION_AUTHENTICATION_CLAIMS_AUTHORITY", "CALLER_AUTHENTICATION_RECEIPT_PRESENT", "CALLER_SUPPLIED_FIELDS_ACCEPTED", "runtime_authentication_evidence:false"):
        assert pred in js, pred


def _produced(tmp_path):
    root = tmp_path / "KnowledgeVault"; sysdir = root / "_System" / "Workspace"; sysdir.mkdir(parents=True)
    (sysdir / "workspace.json").write_text(json.dumps({"schema": "stegverse.kv.workspace-context/v1", "authority_effect": "NONE", "workspace_id": "ws:personal:owner", "owner_principal_id": "user:owner"}), encoding="utf-8")
    (sysdir / "principals.json").write_text(json.dumps({"schema": "stegverse.kv.workspace-principals/v1", "authority_effect": "NONE", "principals": [{"principal_id": "user:owner", "principal_type": "HUMAN", "display_name": "Owner"}]}), encoding="utf-8")
    (sysdir / "assistant.json").write_text(json.dumps({"schema": "stegverse.kv.workspace-assistant/v1", "authority_effect": "NONE", "assistant": {"principal_id": "auri:primary", "principal_type": "AI_ENTITY", "display_name": "Auri", "roles": ["WORKSPACE_ASSISTANT"]}}), encoding="utf-8")
    return get_personal_workspace_projection(kv_data_root=root, clock=lambda: FIXED)


def bind(projection, session_value):
    """The only path a session principal may take to the binding resolver: through an ALLOW session decision."""
    sa = resolve_session_authentication(session_value)
    if sa["disposition"] != "ALLOW":
        return {"disposition": "FAIL_CLOSED", "predicate": sa["predicate"], "binding": None, "action_eligible": False}
    return resolve_assistant_binding(projection, principal_id=sa["session"]["principal_id"], workspace_type="PERSONAL", workspace_id=sa["session"]["workspace_id"])


def test_kv_owner_copied_principal_never_reaches_the_binding_resolver(tmp_path):
    p = _produced(tmp_path)
    owner = p["projection_metadata"]["owner_principal_id"]
    # Equal to the projection owner and would otherwise bind, but copied from KV ownership data.
    d = bind(p, {"principal_id": owner, "workspace_id": "ws:personal:owner", "source_class": "KV_PROJECTION_OWNER"})
    assert d["disposition"] == "FAIL_CLOSED" and d["predicate"] == "KV_OWNERSHIP_IS_NOT_AUTHENTICATION" and d["binding"] is None
    d = bind(p, {"principal_id": owner, "workspace_id": "ws:personal:owner"})
    assert d["predicate"] == "SESSION_PRINCIPAL_SOURCE_NOT_AUTHENTICATION"
    d = bind(p, {"principal_id": None, "workspace_id": None, "source_class": "NO_AUTHENTICATED_SESSION_PRINCIPAL", "authentication": None})
    assert d["predicate"] == "SESSION_PRINCIPAL_UNAUTHENTICATED"


def test_receipt_backed_session_binds_display_only(tmp_path):
    p = _produced(tmp_path)
    d = bind(p, session())
    assert d["disposition"] == "ALLOW" and d["predicate"] == "MYKV_ASSISTANT_BOUND" and d["action_eligible"] is False
    assert d["binding"]["assistant_principal_id"] == "auri:primary" and d["binding"]["invocation_route"] == "NOT_AVAILABLE"
    d = bind(p, session(principal_id="user:other", authentication=receipt(principal_id="user:other")))
    assert d["disposition"] == "DENY" and d["predicate"] == "PROJECTION_OWNER_MISMATCH"
