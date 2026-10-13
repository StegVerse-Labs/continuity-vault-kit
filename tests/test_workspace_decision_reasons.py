"""Every WorkSpace session and assistant-binding decision carries an explanation-ready record with a
plain-language reason (StegVerse-Labs/.github#3106 universal explanation contract)."""
from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

from runtime import workspace_assistant_binding as B
from runtime import workspace_session_authentication as S
from runtime.workspace_decision_reasons import BINDING_REASONS, SESSION_REASONS

ROOT = Path(__file__).resolve().parents[1]
PREDICATE_TOKEN = re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b")


def _source_predicates(module_path: Path) -> set[str]:
    return set(re.findall(r'_decision\(\s*"[A-Z_]+",\s*"([A-Z_]+)"', module_path.read_text(encoding="utf-8")))


def test_every_reachable_predicate_has_a_reason():
    session = _source_predicates(ROOT / "runtime" / "workspace_session_authentication.py") | set(S.NON_AUTHENTICATION_SOURCES.values())
    binding = _source_predicates(ROOT / "runtime" / "workspace_assistant_binding.py")
    assert session and binding
    assert session <= set(SESSION_REASONS), sorted(session - set(SESSION_REASONS))
    assert binding <= set(BINDING_REASONS), sorted(binding - set(BINDING_REASONS))
    assert set(SESSION_REASONS) <= session, "reason for a predicate the module never returns"
    assert set(BINDING_REASONS) <= binding, "reason for a predicate the module never returns"


@pytest.mark.parametrize("reasons", [SESSION_REASONS, BINDING_REASONS])
def test_reasons_are_plain_language(reasons):
    for predicate, reason in reasons.items():
        assert reason.strip() == reason and len(reason) > 20, predicate
        assert not PREDICATE_TOKEN.search(reason), (predicate, reason)
        assert reason[0].islower() and not reason.endswith("."), predicate  # rendered as "Because <reason>."
        assert "authorized" not in reason or "never" in reason or "not" in reason, predicate


def _session(**over):
    s = {"source_class": "CALLER_AUTHENTICATION_RECEIPT", "principal_id": "user:owner", "workspace_id": "ws:personal:owner",
         "authentication": {"authenticated": True, "credential_authority": "TV/TVC", "receipt_ref": "tv://receipt/1", "principal_id": "user:owner"}}
    s.update(over)
    return s


def _session_cases():
    yield _session()
    yield {}
    for source in S.NON_AUTHENTICATION_SOURCES:
        yield _session(source_class=source)
    yield _session(source_class="SOMETHING_ELSE")
    yield _session(principal_id="")
    yield _session(authentication=None)
    for key, value in (("authenticated", False), ("credential_authority", "OTHER"), ("receipt_ref", ""), ("principal_id", "user:other"), ("execution_authority", True)):
        s = _session()
        s["authentication"] = dict(s["authentication"], **{key: value})
        yield s


def test_every_session_decision_carries_a_matching_explanation_record():
    seen = set()
    for case in _session_cases():
        d = S.resolve_session_authentication(copy.deepcopy(case))
        r = d["explanation_record"]
        # Receipt invariant: no ALLOW without its receipt; this decision holds none, so ALLOW is explained as UNKNOWN.
        held = d["disposition"] == "ALLOW"
        assert (r["disposition"], r["predicate"]) == ("UNKNOWN" if held else d["disposition"], d["predicate"])
        assert r["why"] == SESSION_REASONS[d["predicate"]]
        assert (r["authority_source"], r["consequence_observation"]) == ("NONE", "UNKNOWN" if held else "NOT_AUTHENTICALLY_OBSERVED")
        assert d["action_eligible"] is False and d["authority_effect"] == "NONE"
        seen.add(d["predicate"])
    assert seen == set(SESSION_REASONS)


def test_binding_decisions_carry_a_matching_explanation_record():
    d = B.resolve_assistant_binding(None, principal_id="", workspace_type="PERSONAL", workspace_id=None)
    assert d["explanation_record"]["why"] == BINDING_REASONS["SESSION_PRINCIPAL_UNAUTHENTICATED"]
    for predicate in BINDING_REASONS:
        d = B._decision("ALLOW" if predicate == "MYKV_ASSISTANT_BOUND" else "FAIL_CLOSED", predicate)
        r = d["explanation_record"]
        held = d["disposition"] == "ALLOW"
        assert r["disposition"] == ("UNKNOWN" if held else d["disposition"])
        assert (r["predicate"], r["why"], r["consequence_observation"]) == (predicate, BINDING_REASONS[predicate], "UNKNOWN" if held else "NOT_AUTHENTICALLY_OBSERVED")
        assert d["generic_llm_fallback"] == "FORBIDDEN" and d["action_eligible"] is False


def _gh_explanation_module():
    path = ROOT.parent / "gh" / "scripts" / "user_facing_explanation.py"
    if not path.exists():
        pytest.skip(".github checkout not present")
    spec = importlib.util.spec_from_file_location("user_facing_explanation", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["user_facing_explanation"] = module
    spec.loader.exec_module(module)
    return module


def test_records_build_conformant_explanations_whose_why_is_the_reason():
    U = _gh_explanation_module()
    surface = {"repository": "StegVerse-Labs/continuity-vault-kit", "surface_id": "workspace-session"}
    for reasons, disposition_for in ((SESSION_REASONS, lambda p: "ALLOW" if p == "CALLER_AUTHENTICATION_RECEIPT_PRESENT" else "FAIL_CLOSED"),
                                     (BINDING_REASONS, lambda p: "ALLOW" if p == "MYKV_ASSISTANT_BOUND" else "FAIL_CLOSED")):
        for predicate, reason in reasons.items():
            from runtime.workspace_decision_reasons import explanation_record
            record = explanation_record(disposition_for(predicate), predicate, reasons, "Sign in to this WorkSpace")
            artifact = U.validate_explanation(U.build_explanation(record, surface=surface))
            assert artifact["prose"]["why"] == "Because " + reason + "."
            assert artifact["execution"]["executed"] is False
            assert artifact["outcome"]["predicate"] == predicate


def test_mirrors_site_reason_text_when_site_checkout_is_present():
    site = ROOT.parent / "site" / "assets"
    files = {"workspace-session-authentication.js": SESSION_REASONS, "workspace-assistant-binding.js": BINDING_REASONS}
    if not all((site / f).exists() for f in files):
        pytest.skip("Site checkout not present")
    import json as _json
    for name, reasons in files.items():
        js = (site / name).read_text(encoding="utf-8")
        for predicate, reason in reasons.items():
            assert _json.dumps(predicate) + ":" + _json.dumps(reason) in js, (name, predicate)


def test_no_explanation_record_carries_allow():
    # Task Registry invariant: ALLOW exists only with its receipt. These decisions hold none.
    from runtime.workspace_decision_reasons import explanation_record
    for disposition in ("ALLOW", "DENY", "FAIL_CLOSED", "UNKNOWN"):
        r = explanation_record(disposition, "MYKV_ASSISTANT_BOUND", BINDING_REASONS, "Show your MyKV assistant in this WorkSpace")
        assert r["disposition"] != "ALLOW"
        assert r["disposition"] == ("UNKNOWN" if disposition in ("ALLOW", "UNKNOWN") else disposition)


def test_every_explanation_record_is_actionable():
    # Organization Role conformance item 5: a non-ALLOW result carries the six actionable fields.
    from runtime.workspace_decision_reasons import explanation_record, SESSION_REQUESTED_ACTION, BINDING_REQUESTED_ACTION
    six = ("failure_code", "failed_predicate", "required_evidence_or_repair", "retry_entrypoint", "owning_existing_goal", "next_attempt")
    for reasons, action in ((SESSION_REASONS, SESSION_REQUESTED_ACTION), (BINDING_REASONS, BINDING_REQUESTED_ACTION)):
        for predicate in reasons:
            for disposition in ("ALLOW", "DENY", "FAIL_CLOSED"):
                r = explanation_record(disposition, predicate, reasons, action)
                assert all(isinstance(r[k], str) and r[k].strip() for k in six), r
                assert r["failure_code"] == r["failed_predicate"] == predicate
                assert r["owning_existing_goal"] == "STEGVERSE-WORKSPACE-ANY-DEVICE-KV-SURFACE-001"
