#!/usr/bin/env python3
"""Build a portable KnowledgeVault release with verifiable integrity metadata."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "vault_template"
DIST_DIR = REPO_ROOT / "dist"
VERSION_FILE = REPO_ROOT / "VERSION"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def template_files() -> list[Path]:
    """Return template files in a stable order for reproducible manifests."""
    return sorted(
        path
        for path in TEMPLATE_DIR.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def validate_inputs() -> str:
    if not TEMPLATE_DIR.is_dir():
        raise FileNotFoundError(f"Missing template directory: {TEMPLATE_DIR}")
    if not VERSION_FILE.is_file():
        raise FileNotFoundError(f"Missing version file: {VERSION_FILE}")

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("VERSION must not be empty")

    required = [
        TEMPLATE_DIR / "KnowledgeVault" / "_Index" / "Master_Index.md",
        TEMPLATE_DIR / "KnowledgeVault" / "_Policy" / "Naming_Standard.md",
        TEMPLATE_DIR / "KnowledgeVault" / "_Meta" / "vault.manifest.json",
        TEMPLATE_DIR / "KnowledgeVault" / "00_Inbox" / "README.md",
    ]
    missing = [str(path.relative_to(REPO_ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required template files: " + ", ".join(missing))

    return version


def main() -> int:
    try:
        version = validate_inputs()
        files = template_files()
        if not files:
            raise ValueError("Vault template contains no files")

        DIST_DIR.mkdir(parents=True, exist_ok=True)
        zip_name = f"ContinuityVault_v{version}.zip"
        zip_path = DIST_DIR / zip_name
        checksum_path = DIST_DIR / f"{zip_name}.sha256"
        manifest_path = DIST_DIR / f"{zip_name}.manifest.json"

        for output in (zip_path, checksum_path, manifest_path):
            if output.exists():
                output.unlink()

        file_entries: list[dict[str, object]] = []
        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for source in files:
                relative = source.relative_to(TEMPLATE_DIR).as_posix()
                archive.write(source, arcname=relative)
                file_entries.append(
                    {
                        "path": relative,
                        "size": source.stat().st_size,
                        "sha256": sha256_file(source),
                    }
                )

        digest = sha256_file(zip_path)
        checksum_path.write_text(f"{digest}  {zip_name}\n", encoding="utf-8")

        manifest = {
            "schema_version": "1.0",
            "artifact": zip_name,
            "version": version,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sha256": digest,
            "contents_root": "KnowledgeVault",
            "file_count": len(file_entries),
            "files": file_entries,
            "notes": (
                "This ZIP contains the portable KnowledgeVault template. "
                "Hashes verify package integrity, not the truth or safety of user content."
            ),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        print(f"Built: {zip_path}")
        print(f"Manifest: {manifest_path}")
        print(f"Checksum: {checksum_path}")
        print(f"Files: {len(file_entries)}")
        print(f"SHA256: {digest}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
