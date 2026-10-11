"""Family projections delivery reader (Site#1509 P4 delivery): read-only, per-file validation, ambiguity and secrets fail closed."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.workspace_projection import WorkspaceProjectionError
from runtime.workspace_family_projections import DELIVERY_SCHEMA, get_personal_family_projections

FIXED = datetime(2026, 10, 11, 16, 0, 0, tzinfo=timezone.utc)
REV = "a" * 64


def meta(**over):
    m = {"schema": "stegverse.kv.workspace-projection-metadata/v1", "observed_at": "2026-10-11T15:00:00Z", "observed_at_semantics": "KV_PROJECTION_PRODUCTION_TIME",
         "source_revision": REV, "provenance_ref": "cryptobot-portfolio-snapshot:sha256:" + REV, "workspace_type": "PERSONAL", "workspace_id": None,
         "owner_principal_id": None, "grant_state": "UNKNOWN", "revocation_epoch": None, "authority_effect": "NONE"}
    m.update(over); return m


def portfolio(**over):
    p = {"schema": "stegverse.kv.cryptobot-portfolio-projection/v1", "workspace_type": "PERSONAL",
         "portfolio": {"positions": [{"product_id": "ETH-USD", "asset": "ETH", "quantity": 0.5, "price_usd": 2000.0, "value_usd": 1000.0}], "total_value_usd": 1000.0,
                       "drawdown_percent": None, "source_observed_at": "2026-10-11T14:59:00Z", "provider": "coinbase", "unavailable_fields": {"fee_components": "UNAVAILABLE_FROM_SOURCE_SNAPSHOT"}},
         "source": {"schema": "stegverse.crypto_bot.money_manager_portfolio_snapshot.v1", "snapshot_id": "s-1", "portfolio_digest": "sha256:" + REV, "authority": "StegVerse-Labs/TVC"},
         "credential_material_present": False, "provider_operation_authorized": False, "trade_authority_granted": False, "workspace_grants_authority": False,
         "projection_metadata": meta(), "authority_effect": "NONE"}
    p.update(over); return p


def write(root: Path, rel: str, value) -> Path:
    p = root / "_System" / "Workspace" / rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value, encoding="utf-8"); return p


def fixture(tmp_path, files=None, context=True):
    root = tmp_path / "KnowledgeVault"; (root / "_System").mkdir(parents=True)
    if context:
        write(root, "workspace.json", {"schema": "stegverse.kv.workspace-context/v1", "authority_effect": "NONE", "workspace_id": "ws:personal:owner", "owner_principal_id": "user:owner"})
    for name, value in (files if files is not None else {"projections/cryptobot-portfolio.json": portfolio()}).items():
        write(root, name, value)
    return root


def digest_dir(root: Path) -> str:
    return hashlib.sha256(b"".join(sorted(p.read_bytes() for p in root.rglob("*") if p.is_file()))).hexdigest()


def test_reads_family_projections_read_only_with_delivery_metadata(tmp_path):
    root = fixture(tmp_path); before = digest_dir(root)
    d = get_personal_family_projections(kv_data_root=root, clock=lambda: FIXED)
    assert digest_dir(root) == before
    assert d["schema"] == DELIVERY_SCHEMA and d["state"] == "KV_FAMILY_PROJECTIONS_PROJECTED" and d["workspace_type"] == "PERSONAL"
    assert d["projection_schemas"] == ["stegverse.kv.cryptobot-portfolio-projection/v1"] and d["projections"][0] == portfolio()
    assert d["credential_material_present"] is False and d["provider_operation_authorized"] is False and d["workspace_grants_authority"] is False and d["action_authority"] == "NONE" and d["authority_effect"] == "NONE"
    m = d["projection_metadata"]
    assert m["observed_at"] == "2026-10-11T16:00:00Z" and m["workspace_id"] == "ws:personal:owner" and m["owner_principal_id"] == "user:owner" and m["provenance_ref"].endswith(m["source_revision"])
    again = get_personal_family_projections(kv_data_root=root, clock=lambda: FIXED)
    assert again == d


def test_empty_or_missing_directory_is_a_valid_empty_delivery(tmp_path):
    root = fixture(tmp_path, files={})
    d = get_personal_family_projections(kv_data_root=root, clock=lambda: FIXED)
    assert d["state"] == "KV_FAMILY_PROJECTIONS_EMPTY" and d["projections"] == [] and d["projection_schemas"] == []
    (root / "_System" / "Workspace" / "projections").mkdir(parents=True)
    assert get_personal_family_projections(kv_data_root=root, clock=lambda: FIXED)["state"] == "KV_FAMILY_PROJECTIONS_EMPTY"


def test_malformed_files_fail_closed_with_stable_reasons(tmp_path):
    cases = [
        ({"projections/a.json": portfolio(workspace_type="ORGANIZATIONAL")}, "family_projection_workspace_type_invalid:a.json"),
        ({"projections/a.json": portfolio(authority_effect="ALLOW")}, "family_projection_authority_invalid:a.json"),
        ({"projections/a.json": portfolio(workspace_grants_authority=True)}, "family_projection_flag_invalid:a.json:workspace_grants_authority"),
        ({"projections/a.json": portfolio(trade_authority_granted=True)}, "family_projection_trade_authority_invalid:a.json"),
        ({"projections/a.json": portfolio(projection_metadata=None)}, "family_projection_metadata_invalid:a.json"),
        ({"projections/a.json": portfolio(projection_metadata=meta(workspace_type="ORGANIZATIONAL"))}, "family_projection_metadata_context_invalid:a.json"),
        ({"projections/a.json": portfolio(projection_metadata=meta(observed_at=""))}, "family_projection_metadata_observed_at_missing:a.json"),
        ({"projections/a.json": portfolio(schema="stegverse.kv.personal-workspace-projection/v1")}, "family_projection_schema_reserved:a.json"),
        ({"projections/a.json": portfolio(schema="stegverse.kv.workspace-tasks-projection/v1")}, "family_projection_schema_reserved:a.json"),
        ({"projections/a.json": portfolio(schema="other/v1")}, "family_projection_schema_invalid:a.json"),
        ({"projections/a.json": [1, 2]}, "family_projection_object_required:a.json"),
        ({"projections/a.json": "{not json"}, "family_projection_unreadable:a.json"),
        ({"projections/a.json": portfolio(api_token="x")}, "secret_field_forbidden:a.json.api_token"),
        ({"projections/a.json": portfolio(), "projections/b.json": portfolio()}, "family_projection_schema_ambiguous:stegverse.kv.cryptobot-portfolio-projection/v1"),
        ({"projections/bad name.json": portfolio()}, "family_projection_name_invalid:bad name.json"),
    ]
    for index, (files, reason) in enumerate(cases):
        root = fixture(tmp_path / ("case%02d" % index), files=files)
        with pytest.raises(WorkspaceProjectionError) as exc:
            get_personal_family_projections(kv_data_root=root, clock=lambda: FIXED)
        assert str(exc.value) == reason, (reason, str(exc.value))


def test_clock_and_root_are_checked(tmp_path):
    root = fixture(tmp_path)
    with pytest.raises(WorkspaceProjectionError, match="projection_clock_must_be_timezone_aware"):
        get_personal_family_projections(kv_data_root=root, clock=lambda: datetime(2026, 10, 11))
    with pytest.raises(WorkspaceProjectionError, match="kv_data_root_not_knowledgevault"):
        get_personal_family_projections(kv_data_root=tmp_path / "elsewhere", clock=lambda: FIXED)
