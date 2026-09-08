from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT = REPO_ROOT / "tools" / "init_vault.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INIT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _load_instance(root: Path) -> dict:
    return json.loads((root / "_System/Instances/instance.json").read_text(encoding="utf-8"))


def test_second_instance_can_coexist_with_first(tmp_path: Path) -> None:
    first = _run(str(tmp_path), "--instance", "1", "--storage-medium", "icloud-drive")
    assert first.returncode == 0, first.stdout + first.stderr

    second = _run(str(tmp_path), "--instance", "2", "--storage-medium", "icloud-drive")
    assert second.returncode == 0, second.stdout + second.stderr

    kv1 = tmp_path / "KnowledgeVault"
    kv2 = tmp_path / "KnowledgeVault-2"
    assert kv1.is_dir()
    assert kv2.is_dir()
    assert kv1.resolve() != kv2.resolve()

    one = _load_instance(kv1)
    two = _load_instance(kv2)
    assert one["instance_number"] == 1
    assert two["instance_number"] == 2
    assert one["logical_name"] == "KV #1"
    assert two["logical_name"] == "KV #2"
    assert one["storage"]["medium"] == "icloud-drive"
    assert two["storage"]["medium"] == "icloud-drive"
    assert one["kv_set_id"] == two["kv_set_id"] == "default"
    assert one["instance_id"] != two["instance_id"]
    assert one["relationship"]["set_membership"] == "PEER"
    assert two["relationship"]["set_membership"] == "PEER"
    assert two["relationship"]["inherits_authority_from_kv_1"] is False


def test_nth_instance_can_use_any_described_storage_medium(tmp_path: Path) -> None:
    result = _run(
        str(tmp_path),
        "--instance",
        "17",
        "--storage-medium",
        "removable-encrypted-volume",
        "--storage-locator",
        "owner-volume-a",
        "--set-id",
        "personal-continuity",
    )
    assert result.returncode == 0, result.stdout + result.stderr

    kvn = tmp_path / "KnowledgeVault-17"
    instance = _load_instance(kvn)
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
