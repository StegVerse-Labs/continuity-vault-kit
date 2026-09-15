#!/usr/bin/env python3
"""Build a rollback-safe, verified updated KnowledgeVault copy from an owner-selected vault.

The executor never mutates the selected source in place. It accepts either a KnowledgeVault
folder or a ZIP containing exactly one KnowledgeVault, creates rollback evidence first, reuses
the deterministic legacy-upgrade planner, applies only bounded non-lossy framework changes to
an isolated copy, emits receipts, packages the updated copy, and re-verifies the package.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import stat
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_TEMPLATE = REPO_ROOT / "vault_template" / "KnowledgeVault"
VERSION_FILE = REPO_ROOT / "VERSION"
PLANNER_PATH = REPO_ROOT / "tools" / "plan_legacy_kv_upgrade.py"

PLAN_SPEC = importlib.util.spec_from_file_location("legacy_kv_upgrade_planner", PLANNER_PATH)
PLANNER = importlib.util.module_from_spec(PLAN_SPEC)
assert PLAN_SPEC.loader is not None
PLAN_SPEC.loader.exec_module(PLANNER)

RECEIPT_REL = "_System/Upgrade/latest-upgrade.receipt.json"
VERIFY_REL = "_System/Upgrade/latest-upgrade.verification.json"

PERSONAL_PREFIXES = (
    "00_Inbox/",
    "01_Notes/",
    "02_Research/",
    "03_Records/",
    "04_Media/",
    "05_Projects/",
    "06_Archive/",
    "_AI/",
    "_Entities/",
    "_Vault/",
)

PROTECTED_RUNTIME_PREFIXES = (
    "_System/Instances/",
    "_System/Execution/",
    "_System/Identity/",
    "_System/Continuity/",
    "_System/Providers/",
    "_System/Provider/",
    "_System/Receipts/",
    "_System/Recovery/",
    "_System/SKAP/",
)

FRAMEWORK_MANAGED_PREFIXES = (
    "_Policy/",
    "_Templates/",
    "_Index/",
    "_migration/",
    "docs/",
)

GENERATED_EXCLUDE = {RECEIPT_REL, VERIFY_REL}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path, *, exclude_generated: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if exclude_generated and rel in GENERATED_EXCLUDE:
            continue
        rows.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def inventory_hash(rows: list[dict[str, object]]) -> str:
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(canonical)


def safe_zip_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe ZIP member path: {name}")
    return path


def extract_zip_safely(source_zip: Path, destination: Path) -> None:
    with zipfile.ZipFile(source_zip) as archive:
        for info in archive.infolist():
            rel = safe_zip_member(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError(f"ZIP symbolic links are not permitted: {info.filename}")
            target = destination.joinpath(*rel.parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def locate_vault_root(root: Path) -> Path:
    direct = root / "_Meta" / "vault.manifest.json"
    if direct.is_file():
        return root
    candidates = sorted({p.parent.parent for p in root.rglob("_Meta/vault.manifest.json")})
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one KnowledgeVault root, found {len(candidates)}")
    return candidates[0]


def write_deterministic_zip(root: Path, destination: Path, *, root_name: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to replace existing archive: {destination}")
    prefix = root_name or root.name
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(f"{prefix}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def is_personal(path: str) -> bool:
    return path.startswith(PERSONAL_PREFIXES)


def is_protected_runtime(path: str) -> bool:
    return path.startswith(PROTECTED_RUNTIME_PREFIXES) or path == "_System/installation.receipt.json"


def is_framework_managed(path: str) -> bool:
    return path.startswith(FRAMEWORK_MANAGED_PREFIXES)


def copy_with_parents(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def stage_candidate(updated_root: Path, rel: str, template_source: Path) -> str:
    target = updated_root / "_System" / "Upgrade" / "Candidates" / rel
    copy_with_parents(template_source, target)
    return target.relative_to(updated_root).as_posix()


def preserve_before_replace(updated_root: Path, rel: str, existing: Path) -> str:
    target = updated_root / "_System" / "Upgrade" / "Preserved" / rel
    copy_with_parents(existing, target)
    return target.relative_to(updated_root).as_posix()


def merge_manifest(updated_root: Path) -> bool:
    source = CURRENT_TEMPLATE / "_Meta" / "vault.manifest.json"
    target = updated_root / "_Meta" / "vault.manifest.json"
    if not source.is_file():
        return False
    incoming = json.loads(source.read_text(encoding="utf-8"))
    existing: dict[str, object] = {}
    if target.is_file():
        try:
            value = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                existing = value
        except Exception:
            preserve_before_replace(updated_root, "_Meta/vault.manifest.json", target)
    created = existing.get("created_utc")
    merged = dict(existing)
    merged.update(incoming)
    if created is not None:
        merged["created_utc"] = created
    merged["kit_version"] = VERSION_FILE.read_text(encoding="utf-8").strip()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return True


def apply_plan(source_vault: Path, updated_root: Path, plan: dict[str, object]) -> dict[str, object]:
    actions: dict[str, list[str]] = {
        "added": [],
        "framework_replaced_with_preservation": [],
        "personal_or_runtime_conflicts_staged": [],
        "protected_missing_staged": [],
        "unchanged": [],
    }

    template_rows = {row["path"]: row for row in inventory(CURRENT_TEMPLATE)}
    for rel in sorted(template_rows):
        if rel == "_Meta/vault.manifest.json":
            continue
        incoming = CURRENT_TEMPLATE / rel
        target = updated_root / rel
        if target.exists() and target.is_file():
            if sha256_file(target) == sha256_file(incoming):
                actions["unchanged"].append(rel)
                continue
            if is_personal(rel) or is_protected_runtime(rel) or not is_framework_managed(rel):
                stage_candidate(updated_root, rel, incoming)
                actions["personal_or_runtime_conflicts_staged"].append(rel)
                continue
            preserve_before_replace(updated_root, rel, target)
            copy_with_parents(incoming, target)
            actions["framework_replaced_with_preservation"].append(rel)
            continue

        if target.exists() and not target.is_file():
            raise ValueError(f"path collision: template file collides with non-file destination: {rel}")
        if is_protected_runtime(rel):
            stage_candidate(updated_root, rel, incoming)
            actions["protected_missing_staged"].append(rel)
        else:
            copy_with_parents(incoming, target)
            actions["added"].append(rel)

    actions["manifest_merged"] = ["_Meta/vault.manifest.json"] if merge_manifest(updated_root) else []
    return actions


def verify_owner_only_preservation(source_rows: list[dict[str, object]], updated_root: Path) -> list[str]:
    current_paths = {row["path"] for row in inventory(CURRENT_TEMPLATE)}
    failures: list[str] = []
    for row in source_rows:
        rel = str(row["path"])
        if rel in current_paths:
            continue
        target = updated_root / rel
        if not target.is_file() or sha256_file(target) != row["sha256"]:
            failures.append(rel)
    return failures


def verify_protected_existing_preservation(source_rows: list[dict[str, object]], updated_root: Path) -> list[str]:
    source_map = {str(row["path"]): str(row["sha256"]) for row in source_rows}
    failures: list[str] = []
    for rel, expected in source_map.items():
        if not (is_personal(rel) or is_protected_runtime(rel)):
            continue
        target = updated_root / rel
        if not target.is_file() or sha256_file(target) != expected:
            failures.append(rel)
    return failures


def prepare_source(source: Path, work_root: Path) -> tuple[Path, str]:
    if source.is_dir():
        return locate_vault_root(source), "directory"
    if source.is_file() and zipfile.is_zipfile(source):
        extracted = work_root / "source-extracted"
        extracted.mkdir(parents=True, exist_ok=False)
        extract_zip_safely(source, extracted)
        return locate_vault_root(extracted), "zip"
    raise ValueError("source must be a KnowledgeVault directory or ZIP archive")


def execute(source: Path, output_parent: Path, *, timestamp: str | None = None) -> dict[str, object]:
    if not CURRENT_TEMPLATE.is_dir() or not VERSION_FILE.is_file():
        raise ValueError("current template/version is unavailable")
    source = source.expanduser().resolve()
    output_parent = output_parent.expanduser().resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    with tempfile.TemporaryDirectory(prefix="kv-upgrade-") as td:
        temp = Path(td)
        source_vault, source_kind = prepare_source(source, temp)
        source_rows = inventory(source_vault)
        source_tree_sha = inventory_hash(source_rows)
        if not source_rows:
            raise ValueError("source vault contains no files")

        base_name = source_vault.name or "KnowledgeVault"
        rollback_zip = output_parent / f"{base_name}-rollback-{stamp}.zip"
        updated_dir = output_parent / f"{base_name}-updated-{stamp}"
        updated_zip = output_parent / f"{base_name}-updated-{stamp}.zip"
        external_verify = output_parent / f"{base_name}-updated-{stamp}.verification.json"
        for path in (rollback_zip, updated_dir, updated_zip, external_verify):
            if path.exists():
                raise FileExistsError(f"refusing output collision: {path}")

        # Rollback evidence must exist before constructing the mutable output copy.
        if source_kind == "zip":
            shutil.copy2(source, rollback_zip)
            rollback_mode = "EXACT_INPUT_ARCHIVE_COPY"
        else:
            write_deterministic_zip(source_vault, rollback_zip, root_name=base_name)
            rollback_mode = "DETERMINISTIC_FILE_BYTES_ARCHIVE"
        rollback_sha = sha256_file(rollback_zip)

        plan = PLANNER.build_plan(source_vault)
        shutil.copytree(source_vault, updated_dir)
        actions = apply_plan(source_vault, updated_dir, plan)

        owner_failures = verify_owner_only_preservation(source_rows, updated_dir)
        protected_failures = verify_protected_existing_preservation(source_rows, updated_dir)
        if owner_failures or protected_failures:
            shutil.rmtree(updated_dir, ignore_errors=True)
            raise RuntimeError(
                "preservation verification failed: "
                + json.dumps({"owner_only": owner_failures, "protected": protected_failures})
            )

        updated_rows = inventory(updated_dir, exclude_generated=True)
        updated_content_sha = inventory_hash(updated_rows)
        target_version = VERSION_FILE.read_text(encoding="utf-8").strip()
        receipt = {
            "schema": "stegverse.kv.automated-upgrade-receipt/v1",
            "goal_task_id": "KV-ICLOUD-AUTOMATED-UPGRADE-001",
            "state": "UPDATED_COPY_BUILT_VERIFICATION_PENDING",
            "source_kind": source_kind,
            "source_name": source_vault.name,
            "source_tree_sha256": source_tree_sha,
            "source_file_count": len(source_rows),
            "source_version": plan.get("source_version"),
            "target_version": target_version,
            "rollback": {"archive": rollback_zip.name, "sha256": rollback_sha, "mode": rollback_mode, "created_before_output_mutation": True},
            "plan": {
                "schema": plan.get("schema"),
                "counts": plan.get("counts"),
                "mutation_performed_by_planner": plan.get("mutation_performed"),
            },
            "actions": actions,
            "preservation": {
                "owner_only_exact_byte_failures": owner_failures,
                "protected_existing_exact_byte_failures": protected_failures,
                "live_source_overwritten": False,
                "legacy_only_files_removed": False,
            },
            "updated_content_inventory_sha256": updated_content_sha,
            "updated_content_file_count": len(updated_rows),
            "owner_acceptance_required": True,
            "owner_acceptance_observed": False,
            "provider_credentials_required": False,
            "provider_operation_performed": False,
            "google_drive_kv2_request_modified": False,
            "authority_effect": "NONE_FILE_UPDATE_RECEIPT_ONLY",
        }
        receipt_path = updated_dir / RECEIPT_REL
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

        verification = {
            "schema": "stegverse.kv.automated-upgrade-verification/v1",
            "goal_task_id": "KV-ICLOUD-AUTOMATED-UPGRADE-001",
            "source_tree_sha256": source_tree_sha,
            "expected_updated_content_inventory_sha256": updated_content_sha,
            "owner_only_exact_byte_preserved": True,
            "protected_existing_exact_byte_preserved": True,
            "rollback_exists": rollback_zip.is_file(),
            "rollback_sha256": rollback_sha,
            "result": "PREPACKAGE_PASS",
        }
        verify_path = updated_dir / VERIFY_REL
        verify_path.parent.mkdir(parents=True, exist_ok=True)
        verify_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")

        write_deterministic_zip(updated_dir, updated_zip, root_name=updated_dir.name)
        updated_zip_sha = sha256_file(updated_zip)

        check_root = temp / "verification-extract"
        check_root.mkdir()
        extract_zip_safely(updated_zip, check_root)
        verified_vault = locate_vault_root(check_root)
        verified_rows = inventory(verified_vault, exclude_generated=True)
        verified_content_sha = inventory_hash(verified_rows)
        if verified_content_sha != updated_content_sha:
            raise RuntimeError("packaged updated vault content hash does not match pre-package verification")
        if verify_owner_only_preservation(source_rows, verified_vault):
            raise RuntimeError("packaged updated vault failed owner-only exact-byte preservation")
        if verify_protected_existing_preservation(source_rows, verified_vault):
            raise RuntimeError("packaged updated vault failed protected-state exact-byte preservation")

        verification.update({
            "result": "PASS",
            "updated_zip": updated_zip.name,
            "updated_zip_sha256": updated_zip_sha,
            "verified_updated_content_inventory_sha256": verified_content_sha,
            "package_readback_verified": True,
        })
        external_verify.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")

        return {
            "schema": "stegverse.kv.automated-upgrade-result/v1",
            "result": "PASS",
            "goal_task_id": "KV-ICLOUD-AUTOMATED-UPGRADE-001",
            "source_tree_sha256": source_tree_sha,
            "rollback_zip": str(rollback_zip),
            "rollback_sha256": rollback_sha,
            "updated_directory": str(updated_dir),
            "updated_zip": str(updated_zip),
            "updated_zip_sha256": updated_zip_sha,
            "verification_report": str(external_verify),
            "updated_content_inventory_sha256": verified_content_sha,
            "owner_acceptance_required": True,
            "owner_acceptance_observed": False,
            "live_source_overwritten": False,
            "manual_file_by_file_work_required": False,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a verified rollback-safe KnowledgeVault update package without mutating the selected source.")
    parser.add_argument("source", type=Path, help="Owner-selected KnowledgeVault directory or ZIP archive.")
    parser.add_argument("output_parent", type=Path, help="Directory that will receive rollback, updated copy, ZIP, and verification report.")
    parser.add_argument("--owner-authorized", action="store_true", help="Required acknowledgment that the owner selected this source for bounded file-only upgrade packaging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.owner_authorized:
        print("AUTOMATED_KV_UPGRADE_FAIL: --owner-authorized is required; source access is not inferred")
        return 2
    try:
        result = execute(args.source, args.output_parent)
    except Exception as exc:
        print(f"AUTOMATED_KV_UPGRADE_FAIL: {exc}")
        return 3
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
