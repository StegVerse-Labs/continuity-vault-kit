from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "materialize_ephemeral_browser_projection_context.py"

spec = importlib.util.spec_from_file_location("projection", MODULE_PATH)
projection = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(projection)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def entry(**overrides):
    payload = {
        "schema": projection.ENTRY_SCHEMA,
        "purpose": projection.PURPOSE,
        "state": "ADMITTED",
        "authority_effect": "NONE",
        "continuity_boundary": "KV",
        "kv_lineage_id": "kv-lineage-test-001",
        "transition_commitment": DIGEST_A,
    }
    payload.update(overrides)
    return payload


def capability(**overrides):
    payload = {
        "schema": projection.CAPABILITY_SCHEMA,
        "purpose": projection.PURPOSE,
        "state": "OBSERVED_COMPATIBLE",
        "authority_effect": "NONE",
        "continuity_boundary": "KV",
        "browser_identity_authority": False,
        "kv_lineage_id": "kv-lineage-test-001",
        "capability_commitment": DIGEST_B,
    }
    payload.update(overrides)
    return payload


def test_materializes_only_non_authorizing_ephemeral_context():
    result = projection.materialize(entry(), capability())
    assert result["schema"] == projection.OUTPUT_SCHEMA
    assert result["purpose"] == projection.PURPOSE
    assert result["entry_state"] == "ADMITTED"
    assert result["kv_transition_commitment"] == DIGEST_A
    assert result["admission_commitment"].startswith("sha256:")
    assert result["browser_capability_state"] == "OBSERVED_COMPATIBLE"
    assert result["browser_capability_commitment"] == DIGEST_B
    assert result["persistence_effect"] == "NONE_EPHEMERAL_CONTEXT_ONLY"
    assert result["authority_effect"] == "NONE_PROJECTION_GATE_ONLY"
    assert "kv_lineage_id" not in result


def test_rejects_unadmitted_entry():
    try:
        projection.materialize(entry(state="REQUESTED"), capability())
    except ValueError as exc:
        assert "ADMITTED" in str(exc)
    else:
        raise AssertionError("unadmitted KV entry was accepted")


def test_rejects_browser_identity_as_authority():
    try:
        projection.materialize(entry(), capability(browser_identity_authority=True))
    except ValueError as exc:
        assert "browser identity" in str(exc)
    else:
        raise AssertionError("browser identity authority was accepted")


def test_rejects_cross_kv_lineage_mix():
    try:
        projection.materialize(entry(), capability(kv_lineage_id="other-kv-lineage"))
    except ValueError as exc:
        assert "lineage mismatch" in str(exc)
    else:
        raise AssertionError("cross-lineage projection was accepted")


def test_rejects_non_kv_continuity_boundary():
    try:
        projection.materialize(entry(continuity_boundary="BROWSER"), capability())
    except ValueError as exc:
        assert "continuity boundary" in str(exc)
    else:
        raise AssertionError("browser continuity boundary was accepted")
