#!/usr/bin/env python3
"""Independently verify an automated KnowledgeVault update ZIP and sidecar report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR_PATH = ROOT / "tools" / "apply_legacy_kv_upgrade.py"
SPEC = importlib.util.spec_from_file_location("kv_auto_upgrade", EXECUTOR_PATH)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def verify(package: Path, report: Path) -> dict[str, object]:
    package = package.expanduser().resolve()
    report = report.expanduser().resolve()
    if not package.is_file() or not report.is_file():
        raise ValueError("package and verification report must both exist")
    value = json.loads(report.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "stegverse.kv.automated-upgrade-verification/v1":
        raise ValueError("invalid automated-upgrade verification report schema")
    expected_zip = value.get("updated_zip_sha256")
    expected_content = value.get("verified_updated_content_inventory_sha256")
    if not isinstance(expected_zip, str) or not isinstance(expected_content, str):
        raise ValueError("verification report lacks required hashes")
    actual_zip = MOD.sha256_file(package)
    if actual_zip != expected_zip:
        raise ValueError("updated ZIP SHA-256 mismatch")
    with tempfile.TemporaryDirectory(prefix="kv-upgrade-verify-") as td:
        extracted = Path(td)
        MOD.extract_zip_safely(package, extracted)
        vault = MOD.locate_vault_root(extracted)
        actual_content = MOD.inventory_hash(MOD.inventory(vault, exclude_generated=True))
    if actual_content != expected_content:
        raise ValueError("updated content inventory SHA-256 mismatch")
    return {
        "schema": "stegverse.kv.automated-upgrade-independent-verification/v1",
        "result": "PASS",
        "goal_task_id": "KV-ICLOUD-AUTOMATED-UPGRADE-001",
        "updated_zip_sha256": actual_zip,
        "updated_content_inventory_sha256": actual_content,
        "authority_effect": "NONE_VERIFICATION_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("verification_report", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.package, args.verification_report)
    except Exception as exc:
        print(f"AUTOMATED_KV_UPGRADE_VERIFY_FAIL: {exc}")
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
