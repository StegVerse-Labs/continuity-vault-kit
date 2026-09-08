#!/usr/bin/env python3
"""Safely initialize and verify a standalone KnowledgeVault instance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_VAULT = REPO_ROOT / "vault_template" / "KnowledgeVault"
VERSION_FILE = REPO_ROOT / "VERSION"
RECEIPT_NAME = "installation.receipt.json"
INSTANCE_RECORD = Path("_System/Instances/instance.json")
INSTANCE_SCHEMA = "stegverse.kv.instance/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path, *, exclude_generated: bool = False) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    generated = {f"_System/{RECEIPT_NAME}", INSTANCE_RECORD.as_posix()}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if exclude_generated and relative in generated:
            continue
        files.append({"path": relative, "size": path.stat().st_size, "sha256": sha256_file(path)})
    return files


def default_vault_name(instance_number: int) -> str:
    return "KnowledgeVault" if instance_number == 1 else f"KnowledgeVault-{instance_number}"


def validate_vault_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("vault name cannot be empty")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise argparse.ArgumentTypeError("vault name must be a single folder name")
    if not re.fullmatch(r"[A-Za-z0-9._ -]+", value):
        raise argparse.ArgumentTypeError("vault name contains unsupported characters")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a verified KnowledgeVault instance without overwriting an existing vault.")
    parser.add_argument("target_dir", type=Path, help="Parent directory that will receive the new KnowledgeVault instance folder.")
    parser.add_argument("--instance", type=int, default=1, help="Logical KV instance number. 1 -> KnowledgeVault; 2 -> KnowledgeVault-2; n -> KnowledgeVault-n.")
    parser.add_argument("--vault-name", type=validate_vault_name, help="Override the destination folder name without changing the logical instance number.")
    parser.add_argument("--set-id", default="default", help="Non-secret identifier grouping related KV instances for the same owner/continuity set.")
    parser.add_argument("--storage-medium", default="filesystem", help="Descriptive storage medium/provider class, e.g. icloud-drive, google-drive, onedrive, local-disk.")
    parser.add_argument("--storage-locator", default=None, help="Optional non-secret provider/path locator recorded as metadata. Do not supply credentials or tokens.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print the destination without copying files.")
    args = parser.parse_args()
    if args.instance < 1:
        parser.error("--instance must be >= 1")
    if not args.set_id.strip():
        parser.error("--set-id cannot be empty")
    if not args.storage_medium.strip():
        parser.error("--storage-medium cannot be empty")
    return args


def main() -> int:
    args = parse_args()
    target_dir = args.target_dir.expanduser().resolve()
    vault_name = args.vault_name or default_vault_name(args.instance)
    target_vault = target_dir / vault_name

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
        print(f"DRY RUN: would initialize KV #{args.instance} ({len(source_inventory)} files) at {target_vault} on storage medium {args.storage_medium}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(TEMPLATE_VAULT, target_vault)
        manifest_path = target_vault / "_Meta" / "vault.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest["created_utc"] = created_utc
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        source_by_path = {entry["path"]: entry for entry in source_inventory}
        target_inventory = inventory(target_vault, exclude_generated=True)
        target_by_path = {entry["path"]: entry for entry in target_inventory}
        if set(source_by_path) != set(target_by_path):
            raise RuntimeError("source and destination file sets differ")

        mutable_path = "_Meta/vault.manifest.json"
        mismatches = [path for path in source_by_path if path != mutable_path and source_by_path[path]["sha256"] != target_by_path[path]["sha256"]]
        if mismatches:
            raise RuntimeError("copied file hash mismatch: " + ", ".join(mismatches[:3]))

        instance_id = f"kvi_{uuid.uuid4().hex}"
        instance_record = {
            "schema": INSTANCE_SCHEMA,
            "instance_id": instance_id,
            "instance_number": args.instance,
            "logical_name": f"KV #{args.instance}",
            "kv_set_id": args.set_id.strip(),
            "relationship": {
                "set_membership": "PEER",
                "tier": "NOT_CONNECTED",
                "tier_order": 0,
                "inter_comms": False,
                "data_movement": False,
                "replication": False,
                "unified_ai_corpus": False,
                "ordinal_is_authority": False,
                "inherits_authority_from_kv_1": False,
                "authority_effect": "NONE",
                "activation_effect": False,
                "notes": "New instances are isolated by default. Relationship-tier changes require separate governed admission when runtime authority is active.",
            },
            "storage": {"medium": args.storage_medium.strip(), "locator": args.storage_locator, "provider_authority_effect": "NONE"},
            "created_utc": created_utc,
            "kit_version": VERSION_FILE.read_text(encoding="utf-8").strip(),
        }
        instance_path = target_vault / INSTANCE_RECORD
        instance_path.parent.mkdir(parents=True, exist_ok=True)
        instance_path.write_text(json.dumps(instance_record, indent=2) + "\n", encoding="utf-8")

        receipt = {
            "schema_version": "1.1",
            "kit_version": VERSION_FILE.read_text(encoding="utf-8").strip(),
            "created_utc": created_utc,
            "source": "vault_template/KnowledgeVault",
            "destination": str(target_vault),
            "instance": {"instance_id": instance_id, "instance_number": args.instance, "logical_name": f"KV #{args.instance}", "kv_set_id": args.set_id.strip(), "record": INSTANCE_RECORD.as_posix()},
            "relationship": {"tier": "NOT_CONNECTED", "tier_order": 0},
            "storage": {"medium": args.storage_medium.strip(), "locator": args.storage_locator},
            "file_count": len(target_inventory),
            "manifest_sha256": target_by_path[mutable_path]["sha256"],
            "verification": {"file_set_matches": True, "immutable_file_hashes_match": True, "overwrote_existing_vault": False, "instance_root_isolated": True},
        }
        receipt_path = target_vault / "_System" / RECEIPT_NAME
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        shutil.rmtree(target_vault, ignore_errors=True)
        print(f"Initialization failed and partial destination was removed: {exc}")
        return 7

    print(f"Initialized and verified KV #{args.instance} at: {target_vault}")
    print(f"Instance record: {target_vault / INSTANCE_RECORD}")
    print(f"Receipt: {target_vault / '_System' / RECEIPT_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
