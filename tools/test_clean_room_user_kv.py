#!/usr/bin/env python3
"""Deterministic clean-room proof for a packageable, creator-independent KnowledgeVault."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "vault_template" / "KnowledgeVault"
DIST = REPO_ROOT / "dist"

FORBIDDEN_INSTALLER_MARKERS = (
    "1c8OdhJeLD6E4ALmi-aR7dXvG8PjDLSfi",  # connected-user Drive root
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GITHUB_TOKEN",
    "CLOUDFLARE_API_TOKEN",
    "COINBASE_API_KEY",
    "/run/stegverse/",
)
FORBIDDEN_RECEIPT_MARKERS = (
    "drive.google.com",
    "1c8OdhJeLD6E4ALmi-aR7dXvG8PjDLSfi",
    "/run/stegverse/",
    "coinbase",
    "cloudflare",
)
FORBIDDEN_FRESH_RUNTIME_PREFIXES = (
    "_Vault/",
    "_System/Execution/",
    "_System/Identity/",
    "_System/Governance/",
    "_System/Modules/",
    "_System/Services/",
    "_System/Readiness/",
    "03_Records/Health/",
    "05_Projects/OWV/",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        out[rel] = {"size": path.stat().st_size, "sha256": sha256_file(path)}
    return out


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def main() -> int:
    source = inventory(TEMPLATE)
    if not source:
        raise RuntimeError("template inventory is empty")
    if any(path.is_symlink() for path in TEMPLATE.rglob("*")):
        raise RuntimeError("template must not contain symlinks")

    installer_text = (REPO_ROOT / "tools" / "init_vault.py").read_text(encoding="utf-8")
    for marker in FORBIDDEN_INSTALLER_MARKERS:
        if marker in installer_text:
            raise RuntimeError(f"initializer contains creator/provider-specific dependency marker: {marker}")

    clean_env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    shutil.rmtree(DIST, ignore_errors=True)
    run([sys.executable, "tools/build_release.py"], env=clean_env)

    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    zip_path = DIST / f"ContinuityVault_v{version}.zip"
    manifest_path = DIST / f"ContinuityVault_v{version}.zip.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest["file_count"] != len(source):
        raise RuntimeError(
            f"release manifest count {manifest['file_count']} != source count {len(source)}"
        )

    manifest_files = {entry["path"]: entry for entry in manifest["files"]}
    expected_archive_paths = {f"KnowledgeVault/{path}" for path in source}
    if set(manifest_files) != expected_archive_paths:
        raise RuntimeError("release manifest path set differs from clean source template")

    with tempfile.TemporaryDirectory(prefix="stegverse-kv-clean-room-") as td:
        root = Path(td)
        extracted = root / "release"
        initialized_parent = root / "initializer"

        with ZipFile(zip_path) as archive:
            archive.extractall(extracted)

        extracted_vault = extracted / "KnowledgeVault"
        extracted_inventory = inventory(extracted_vault)
        if set(extracted_inventory) != set(source):
            raise RuntimeError("extracted release path set differs from source")

        for rel, src in source.items():
            arc = manifest_files[f"KnowledgeVault/{rel}"]
            if arc["sha256"] != src["sha256"]:
                raise RuntimeError(f"manifest source hash mismatch: {rel}")
            if extracted_inventory[rel]["sha256"] != src["sha256"]:
                raise RuntimeError(f"extracted release hash mismatch: {rel}")

        run([sys.executable, "tools/init_vault.py", str(initialized_parent)], env=clean_env)
        initialized = initialized_parent / "KnowledgeVault"
        receipt_path = initialized / "_System" / "installation.receipt.json"
        if not receipt_path.is_file():
            raise RuntimeError("clean-room initializer did not emit installation receipt")

        init_inventory = inventory(initialized)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt_text = json.dumps(receipt, sort_keys=True).lower()
        for marker in FORBIDDEN_RECEIPT_MARKERS:
            if marker.lower() in receipt_text:
                raise RuntimeError(f"installation receipt leaked creator/provider marker: {marker}")

        expected_initialized_paths = set(source) | {"_System/installation.receipt.json"}
        if set(init_inventory) != expected_initialized_paths:
            raise RuntimeError("initialized path set includes unexpected creator/runtime state")

        for prefix in FORBIDDEN_FRESH_RUNTIME_PREFIXES:
            if any(path.startswith(prefix) for path in init_inventory):
                raise RuntimeError(f"fresh vault inherited connected-user runtime state: {prefix}")

        mutable = "_Meta/vault.manifest.json"
        for rel, src in source.items():
            if rel == mutable:
                continue
            if init_inventory[rel]["sha256"] != src["sha256"]:
                raise RuntimeError(f"initializer immutable hash mismatch: {rel}")

        verification = receipt.get("verification", {})
        if verification.get("file_set_matches") is not True:
            raise RuntimeError("initializer receipt lacks file_set_matches=true")
        if verification.get("immutable_file_hashes_match") is not True:
            raise RuntimeError("initializer receipt lacks immutable_file_hashes_match=true")
        if verification.get("overwrote_existing_vault") is not False:
            raise RuntimeError("initializer receipt does not preserve overwrite refusal")

        refused = subprocess.run(
            [sys.executable, "tools/init_vault.py", str(initialized_parent)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=clean_env,
        )
        if refused.returncode != 5 or "Refusing to overwrite existing" not in refused.stdout:
            raise RuntimeError("clean-room overwrite refusal failed")

    print(
        json.dumps(
            {
                "result": "PASS",
                "template_files": len(source),
                "release_manifest_files": manifest["file_count"],
                "creator_specific_infrastructure_dependency": False,
                "cloud_credentials_required": False,
                "network_required": False,
                "connected_user_runtime_state_inherited": False,
                "authority_effect": "NONE",
                "activation_effect": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
