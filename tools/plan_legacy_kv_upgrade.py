#!/usr/bin/env python3
"""Produce a non-destructive upgrade/reinstall plan for an existing KnowledgeVault."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_TEMPLATE = REPO_ROOT / "vault_template" / "KnowledgeVault"
VERSION_FILE = REPO_ROOT / "VERSION"
MUTABLE_TEMPLATE_PATHS = {"_Meta/vault.manifest.json"}
RECEIPT_PATH = "_System/installation.receipt.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel = p.relative_to(root).as_posix()
        rows[rel] = {"size": p.stat().st_size, "sha256": sha256_file(p)}
    return rows


def read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def detect_legacy_version(vault: Path, manifest: dict[str, object] | None) -> str:
    for key in ("kit_version", "version", "vault_version"):
        value = manifest.get(key) if manifest else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    fmt = vault / "_Meta" / "FORMAT_VERSION.md"
    if fmt.is_file():
        text = fmt.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return text
    return "UNKNOWN"


def build_plan(vault: Path) -> dict[str, object]:
    if not vault.is_dir():
        raise ValueError(f"legacy vault directory not found: {vault}")
    if not CURRENT_TEMPLATE.is_dir():
        raise ValueError(f"current template missing: {CURRENT_TEMPLATE}")

    legacy = inventory(vault)
    current = inventory(CURRENT_TEMPLATE)
    manifest = read_json(vault / "_Meta" / "vault.manifest.json")
    current_version = VERSION_FILE.read_text(encoding="utf-8").strip()

    matches: list[str] = []
    updates: list[str] = []
    additions: list[str] = []

    for path, src in current.items():
        if path in MUTABLE_TEMPLATE_PATHS:
            continue
        dst = legacy.get(path)
        if dst is None:
            additions.append(path)
        elif dst["sha256"] == src["sha256"]:
            matches.append(path)
        else:
            updates.append(path)

    preserve = sorted(
        p for p in legacy
        if p not in current and p != RECEIPT_PATH
    )

    receipt = read_json(vault / RECEIPT_PATH)

    return {
        "schema": "stegverse.kv.legacy-upgrade-plan/v1",
        "state": "MIGRATION_PLAN_READY",
        "source_vault": str(vault),
        "source_version": detect_legacy_version(vault, manifest),
        "target_version": current_version,
        "current_template_root": "vault_template/KnowledgeVault",
        "counts": {
            "legacy_files": len(legacy),
            "current_template_files": len(current),
            "template_matches": len(matches),
            "template_updates_required": len(updates),
            "template_additions_required": len(additions),
            "legacy_only_preserve": len(preserve),
        },
        "template_matches": matches,
        "template_updates_required": updates,
        "template_additions_required": additions,
        "legacy_only_preserve": preserve,
        "legacy_receipt_present": RECEIPT_PATH in legacy,
        "legacy_receipt_schema_version": receipt.get("schema_version") if receipt else None,
        "legacy_receipt_source_tree_sha": receipt.get("current_verified_source_tree_sha") if receipt else None,
        "mutation_performed": False,
        "overwrite_existing_vault": False,
        "owner_acceptance_required": True,
        "rollback_copy_required": True,
        "credential_material_required": False,
        "authority_effect": "NONE_PLAN_ONLY",
        "next_action": "Review this plan, preserve a rollback copy, then apply only an explicitly admitted upgrade/reinstall operation.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("legacy_vault", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    try:
        plan = build_plan(args.legacy_vault.expanduser().resolve())
    except Exception as exc:
        print(f"LEGACY_KV_UPGRADE_PLAN_FAIL: {exc}")
        return 2

    text = json.dumps(plan, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
