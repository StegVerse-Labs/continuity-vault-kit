#!/usr/bin/env python3
"""Non-destructively adopt an existing KnowledgeVault into the multi-instance model.

This tool is intentionally narrow. It never creates a new vault, rewrites private
content, changes the existing installation receipt, authenticates a provider, or
materializes relationship/provider authority. Apply mode is bound to the caller's
expected SHA-256 of the existing installation receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.kv_my_kv_projection import build_set_projection

INSTANCE_SCHEMA = "stegverse.kv.instance/v1"
INSTANCE_RECORD = Path("_System/Instances/instance.json")
INSTALLATION_RECEIPT = Path("_System/installation.receipt.json")
SET_PROJECTION_RECORD = Path("_System/my-kv-set-projection.json")
ADOPTION_RECEIPT = Path("_System/Instances/adoption.receipt.json")
ADOPTION_RECEIPT_SCHEMA = "stegverse.kv.existing-instance-adoption-receipt/v1"


class AdoptionError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AdoptionError(f"unreadable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AdoptionError(f"expected JSON object: {path}")
    return value


def atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def validate_existing_vault(root: Path) -> tuple[Path, str, dict]:
    if not root.is_dir():
        raise AdoptionError(f"KnowledgeVault root not found: {root}")
    receipt_path = root / INSTALLATION_RECEIPT
    if not receipt_path.is_file():
        raise AdoptionError("existing installation receipt missing")
    receipt = read_json(receipt_path)
    if str(receipt.get("schema_version") or "") != "1.1":
        raise AdoptionError("existing installation receipt schema must be 1.1")
    if not isinstance(receipt.get("source"), str) or "KnowledgeVault" not in receipt["source"]:
        raise AdoptionError("installation receipt source is not a KnowledgeVault source")
    return receipt_path, sha256_file(receipt_path), receipt


def build_instance_record(*, instance_number: int, set_id: str, storage_medium: str, storage_locator: str | None, created_utc: str) -> dict:
    if instance_number < 1:
        raise AdoptionError("instance number must be >= 1")
    if not set_id.strip():
        raise AdoptionError("set id cannot be empty")
    if not storage_medium.strip():
        raise AdoptionError("storage medium cannot be empty")
    return {
        "schema": INSTANCE_SCHEMA,
        "instance_id": f"kvi_{uuid.uuid4().hex}",
        "instance_number": instance_number,
        "logical_name": f"KV #{instance_number}",
        "kv_set_id": set_id.strip(),
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
            "notes": "Existing vault adopted into the multi-instance identity model. Relationship changes require separate governed admission.",
        },
        "storage": {
            "medium": storage_medium.strip(),
            "locator": storage_locator,
            "provider_authority_effect": "NONE",
        },
        "created_utc": created_utc,
        "adoption": {
            "existing_vault": True,
            "private_content_modified": False,
            "installation_receipt_modified": False,
            "provider_operation_executed": False,
            "authority_effect": "NONE",
            "activation_effect": False,
        },
    }


def plan(root: Path, *, instance_number: int, set_id: str, storage_medium: str, storage_locator: str | None) -> dict:
    root = root.expanduser().resolve()
    receipt_path, receipt_sha256, _ = validate_existing_vault(root)
    instance_path = root / INSTANCE_RECORD
    projection_path = root / SET_PROJECTION_RECORD
    adoption_receipt_path = root / ADOPTION_RECEIPT
    return {
        "schema": "stegverse.kv.existing-instance-adoption-plan/v1",
        "vault_root": str(root),
        "installation_receipt": str(receipt_path),
        "installation_receipt_sha256": f"sha256:{receipt_sha256}",
        "instance_number": instance_number,
        "logical_name": f"KV #{instance_number}",
        "kv_set_id": set_id.strip(),
        "storage": {"medium": storage_medium.strip(), "locator": storage_locator},
        "writes": [str(INSTANCE_RECORD), str(ADOPTION_RECEIPT), str(SET_PROJECTION_RECORD)],
        "instance_record_exists": instance_path.exists(),
        "adoption_receipt_exists": adoption_receipt_path.exists(),
        "set_projection_exists": projection_path.exists(),
        "private_content_modified": False,
        "installation_receipt_modified": False,
        "provider_operation_executed": False,
        "relationship_tier_materialized": "NOT_CONNECTED",
        "authority_effect": "NONE_PLAN_ONLY",
        "activation_effect": False,
    }


def apply_adoption(root: Path, *, instance_number: int, set_id: str, storage_medium: str, storage_locator: str | None, expected_receipt_sha256: str) -> dict:
    root = root.expanduser().resolve()
    receipt_path, actual_sha256, _ = validate_existing_vault(root)
    expected = expected_receipt_sha256.removeprefix("sha256:").lower()
    if expected != actual_sha256:
        raise AdoptionError("installation receipt SHA-256 mismatch; refusing adoption")

    instance_path = root / INSTANCE_RECORD
    adoption_receipt_path = root / ADOPTION_RECEIPT
    projection_path = root / SET_PROJECTION_RECORD
    for path, label in ((instance_path, "instance identity"), (adoption_receipt_path, "adoption receipt"), (projection_path, "set projection")):
        if path.exists():
            raise AdoptionError(f"existing {label} would be overwritten: {path}")

    created_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    instance = build_instance_record(
        instance_number=instance_number,
        set_id=set_id,
        storage_medium=storage_medium,
        storage_locator=storage_locator,
        created_utc=created_utc,
    )
    atomic_write_json(instance_path, instance)
    try:
        projection = build_set_projection([root])
        if projection.get("private_content_included") is not False or projection.get("credential_material_included") is not False:
            raise AdoptionError("bounded projection violated content boundary")
        if projection.get("authority_effect") != "NONE_STATUS_ONLY" or projection.get("activation_effect") is not False:
            raise AdoptionError("bounded projection violated authority boundary")
        atomic_write_json(projection_path, projection)
        adoption_receipt = {
            "schema": ADOPTION_RECEIPT_SCHEMA,
            "state": "EXISTING_KV_ADOPTED_AS_INSTANCE",
            "created_utc": created_utc,
            "vault_root": str(root),
            "installation_receipt_path": str(INSTALLATION_RECEIPT),
            "installation_receipt_sha256": f"sha256:{actual_sha256}",
            "instance_record_path": str(INSTANCE_RECORD),
            "instance_id": instance["instance_id"],
            "instance_number": instance_number,
            "kv_set_id": set_id.strip(),
            "set_projection_path": str(SET_PROJECTION_RECORD),
            "set_projection_schema": projection["schema"],
            "private_content_modified": False,
            "installation_receipt_modified": False,
            "provider_operation_executed": False,
            "relationship_tier": "NOT_CONNECTED",
            "credential_material_present": False,
            "provider_mutation_authorized": False,
            "relationship_mutation_authorized": False,
            "authority_effect": "NONE",
            "activation_effect": False,
        }
        atomic_write_json(adoption_receipt_path, adoption_receipt)
    except Exception:
        for generated in (adoption_receipt_path, projection_path, instance_path):
            try:
                generated.unlink()
            except FileNotFoundError:
                pass
        raise
    return adoption_receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adopt an existing KnowledgeVault as a bounded multi-instance KV without overwriting existing state.")
    parser.add_argument("vault_root", type=Path)
    parser.add_argument("--instance", type=int, default=1)
    parser.add_argument("--set-id", required=True)
    parser.add_argument("--storage-medium", required=True)
    parser.add_argument("--storage-locator")
    parser.add_argument("--apply", action="store_true", help="Create identity/adoption receipt/set projection after exact receipt-hash validation.")
    parser.add_argument("--expected-installation-receipt-sha256", help="Required with --apply. Accepts raw hex or sha256:<hex>.")
    args = parser.parse_args()
    if args.instance < 1:
        parser.error("--instance must be >= 1")
    if args.apply and not args.expected_installation_receipt_sha256:
        parser.error("--expected-installation-receipt-sha256 is required with --apply")
    return args


def main() -> int:
    args = parse_args()
    try:
        if not args.apply:
            value = plan(args.vault_root, instance_number=args.instance, set_id=args.set_id, storage_medium=args.storage_medium, storage_locator=args.storage_locator)
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0
        value = apply_adoption(
            args.vault_root,
            instance_number=args.instance,
            set_id=args.set_id,
            storage_medium=args.storage_medium,
            storage_locator=args.storage_locator,
            expected_receipt_sha256=args.expected_installation_receipt_sha256,
        )
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    except AdoptionError as exc:
        print(f"ADOPTION_REFUSED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
