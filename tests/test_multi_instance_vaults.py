from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from runtime.kv_instance_relationships import KVRelationshipTier, capabilities_for, relationship_record

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT = REPO_ROOT / "tools" / "init_vault.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(INIT), *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False)


def _load_instance(root: Path) -> dict:
    return json.loads((root / "_System/Instances/instance.json").read_text(encoding="utf-8"))


def test_second_instance_can_coexist_with_first(tmp_path: Path) -> None:
    first = _run(str(tmp_path), "--instance", "1", "--storage-medium", "icloud-drive")
    assert first.returncode == 0, first.stdout + first.stderr
    second = _run(str(tmp_path), "--instance", "2", "--storage-medium", "icloud-drive")
    assert second.returncode == 0, second.stdout + second.stderr

    kv1 = tmp_path / "KnowledgeVault"
    kv2 = tmp_path / "KnowledgeVault-2"
    assert kv1.is_dir() and kv2.is_dir() and kv1.resolve() != kv2.resolve()

    one = _load_instance(kv1)
    two = _load_instance(kv2)
    assert one["instance_number"] == 1
    assert two["instance_number"] == 2
    assert one["logical_name"] == "KV #1"
    assert two["logical_name"] == "KV #2"
    assert one["storage"]["medium"] == two["storage"]["medium"] == "icloud-drive"
    assert one["kv_set_id"] == two["kv_set_id"] == "default"
    assert one["instance_id"] != two["instance_id"]
    assert one["relationship"]["set_membership"] == "PEER"
    assert two["relationship"]["set_membership"] == "PEER"
    assert two["relationship"]["inherits_authority_from_kv_1"] is False
    assert one["relationship"]["tier"] == two["relationship"]["tier"] == "NOT_CONNECTED"
    assert one["relationship"]["inter_comms"] is False
    assert two["relationship"]["data_movement"] is False


def test_nth_instance_can_use_any_described_storage_medium(tmp_path: Path) -> None:
    result = _run(str(tmp_path), "--instance", "17", "--storage-medium", "removable-encrypted-volume", "--storage-locator", "owner-volume-a", "--set-id", "personal-continuity")
    assert result.returncode == 0, result.stdout + result.stderr
    instance = _load_instance(tmp_path / "KnowledgeVault-17")
    assert instance["instance_number"] == 17
    assert instance["logical_name"] == "KV #17"
    assert instance["kv_set_id"] == "personal-continuity"
    assert instance["storage"]["medium"] == "removable-encrypted-volume"
    assert instance["storage"]["locator"] == "owner-volume-a"
    assert instance["storage"]["provider_authority_effect"] == "NONE"


def test_existing_instance_root_is_never_overwritten(tmp_path: Path) -> None:
    assert _run(str(tmp_path), "--instance", "2").returncode == 0
    refused = _run(str(tmp_path), "--instance", "2")
    assert refused.returncode == 5
    assert "Refusing to overwrite existing" in refused.stdout


def test_custom_folder_name_does_not_change_logical_instance_number(tmp_path: Path) -> None:
    result = _run(str(tmp_path), "--instance", "2", "--vault-name", "MyKV-iCloud-Secondary")
    assert result.returncode == 0, result.stdout + result.stderr
    instance = _load_instance(tmp_path / "MyKV-iCloud-Secondary")
    assert instance["instance_number"] == 2
    assert instance["logical_name"] == "KV #2"


def test_relationship_tiers_are_cumulative() -> None:
    not_connected = capabilities_for(KVRelationshipTier.NOT_CONNECTED)
    connected = capabilities_for(KVRelationshipTier.CONNECTED)
    synced = capabilities_for(KVRelationshipTier.SYNCED)
    ai = capabilities_for(KVRelationshipTier.AI_INTERACTION)

    assert (not_connected.inter_comms, not_connected.data_movement, not_connected.replication, not_connected.unified_ai_corpus) == (False, False, False, False)
    assert (connected.inter_comms, connected.data_movement, connected.replication, connected.unified_ai_corpus) == (True, True, False, False)
    assert (synced.inter_comms, synced.data_movement, synced.replication, synced.unified_ai_corpus) == (True, True, True, False)
    assert (ai.inter_comms, ai.data_movement, ai.replication, ai.unified_ai_corpus) == (True, True, True, True)


def test_relationship_record_never_claims_runtime_activation() -> None:
    record = relationship_record("AI_INTERACTION")
    assert record["tier_order"] == 3
    assert record["unified_ai_corpus"] is True
    assert record["authority_effect"] == "NONE"
    assert record["activation_effect"] is False
