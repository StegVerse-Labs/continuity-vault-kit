#!/usr/bin/env python3
"""Safely initialize and verify a standalone KnowledgeVault copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_VAULT = REPO_ROOT / "vault_template" / "KnowledgeVault"
VERSION_FILE = REPO_ROOT / "VERSION"
RECEIPT_NAME = "installation.receipt.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path, *, exclude_receipt: bool = False) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if exclude_receipt and relative == f"_System/{RECEIPT_NAME}":
            continue
        files.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a verified KnowledgeVault without overwriting an existing vault."
    )
    parser.add_argument(
        "target_dir",
        type=Path,
        help="Parent directory that will receive a new KnowledgeVault folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the destination without copying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_dir = args.target_dir.expanduser().resolve()
    target_vault = target_dir / "KnowledgeVault"

    if not TEMPLATE_VAULT.is_dir():
        print(f"Missing template vault: {TEMPLATE_VAULT}")
        return 3
    if not VERSION_FILE.is_file():
        print(f"Missing version file: {VERSION_FILE}")
        return 4
    if target_vault.exists():
        print(f"Refusing to overwrite existing: {target_vault}")
        return 5

    source_inventory = inventory(TEMPLATE_VAULT)
    if not source_inventory:
        print("Template vault contains no files")
        return 6

    if args.dry_run:
        print(f"DRY RUN: would initialize {len(source_inventory)} files at {target_vault}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(TEMPLATE_VAULT, target_vault)
        manifest_path = target_vault / "_Meta" / "vault.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest["created_utc"] = created_utc
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        # The manifest timestamp intentionally differs from the packaged template,
        # so verify all other files exactly and record the initialized manifest hash.
        source_by_path = {entry["path"]: entry for entry in source_inventory}
        target_inventory = inventory(target_vault)
        target_by_path = {entry["path"]: entry for entry in target_inventory}
        if set(source_by_path) != set(target_by_path):
            raise RuntimeError("source and destination file sets differ")

        mutable_path = "_Meta/vault.manifest.json"
        mismatches = [
            path
            for path in source_by_path
            if path != mutable_path
            and source_by_path[path]["sha256"] != target_by_path[path]["sha256"]
        ]
        if mismatches:
            raise RuntimeError("copied file hash mismatch: " + ", ".join(mismatches[:3]))

        receipt = {
            "schema_version": "1.0",
            "kit_version": VERSION_FILE.read_text(encoding="utf-8").strip(),
            "created_utc": created_utc,
            "source": "vault_template/KnowledgeVault",
            "destination": str(target_vault),
            "file_count": len(target_inventory),
            "manifest_sha256": target_by_path[mutable_path]["sha256"],
            "verification": {
                "file_set_matches": True,
                "immutable_file_hashes_match": True,
                "overwrote_existing_vault": False,
            },
        }
        receipt_path = target_vault / "_System" / RECEIPT_NAME
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        shutil.rmtree(target_vault, ignore_errors=True)
        print(f"Initialization failed and partial destination was removed: {exc}")
        return 7

    print(f"Initialized and verified vault at: {target_vault}")
    print(f"Receipt: {target_vault / '_System' / RECEIPT_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
