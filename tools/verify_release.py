#!/usr/bin/env python3
"""Verify a Continuity Vault release bundle and its integrity sidecars."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

REQUIRED_FILES = {
    "KnowledgeVault/_Index/Master_Index.md",
    "KnowledgeVault/_Policy/Naming_Standard.md",
    "KnowledgeVault/_Meta/vault.manifest.json",
    "KnowledgeVault/00_Inbox/README.md",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str, code: int) -> int:
    print(f"FAIL: {message}")
    return code


def safe_archive_path(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 tools/verify_release.py dist/ContinuityVault_vX.Y.Z.zip")
        return 2

    zip_path = Path(sys.argv[1]).resolve()
    manifest_path = zip_path.with_suffix(zip_path.suffix + ".manifest.json")
    checksum_path = zip_path.with_suffix(zip_path.suffix + ".sha256")

    if not zip_path.is_file():
        return fail(f"missing release bundle: {zip_path}", 3)
    if not checksum_path.is_file():
        return fail(f"missing checksum sidecar: {checksum_path.name}", 4)
    if not manifest_path.is_file():
        return fail(f"missing manifest sidecar: {manifest_path.name}", 5)

    digest = sha256_file(zip_path)
    print(f"Computed SHA256: {digest}")

    checksum_parts = checksum_path.read_text(encoding="utf-8").split()
    if len(checksum_parts) < 2:
        return fail("checksum sidecar must contain a digest and artifact name", 6)
    expected_digest, expected_name = checksum_parts[0], checksum_parts[1]
    if expected_digest != digest:
        return fail(f"checksum mismatch; expected={expected_digest}", 7)
    if expected_name != zip_path.name:
        return fail(f"checksum artifact mismatch; expected={expected_name}", 8)
    print("OK: checksum matches")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"invalid manifest JSON: {exc}", 9)

    if manifest.get("artifact") != zip_path.name:
        return fail("manifest artifact name does not match bundle", 10)
    if manifest.get("sha256") != digest:
        return fail("manifest sha256 does not match bundle", 11)
    if manifest.get("contents_root") != "KnowledgeVault":
        return fail("manifest contents_root must be KnowledgeVault", 12)
    if not manifest.get("version"):
        return fail("manifest version is missing", 13)
    print("OK: manifest bundle metadata matches")

    try:
        with ZipFile(zip_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                return fail("archive contains duplicate paths", 14)
            unsafe = [name for name in names if not safe_archive_path(name)]
            if unsafe:
                return fail(f"archive contains unsafe path: {unsafe[0]}", 15)

            name_set = set(names)
            missing = sorted(REQUIRED_FILES - name_set)
            if missing:
                return fail("missing required files: " + ", ".join(missing), 16)

            manifest_files = manifest.get("files")
            if not isinstance(manifest_files, list):
                return fail("manifest files list is missing", 17)

            entries: dict[str, dict[str, object]] = {}
            for entry in manifest_files:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    return fail("manifest contains an invalid file entry", 18)
                path = entry["path"]
                if path in entries:
                    return fail(f"manifest contains duplicate file entry: {path}", 19)
                entries[path] = entry

            if manifest.get("file_count") != len(entries):
                return fail("manifest file_count does not match files list", 20)
            if set(entries) != name_set:
                missing_from_manifest = sorted(name_set - set(entries))
                missing_from_archive = sorted(set(entries) - name_set)
                detail = []
                if missing_from_manifest:
                    detail.append("unlisted=" + ",".join(missing_from_manifest[:3]))
                if missing_from_archive:
                    detail.append("absent=" + ",".join(missing_from_archive[:3]))
                return fail("manifest/archive file set mismatch; " + "; ".join(detail), 21)

            for name in names:
                payload = archive.read(name)
                entry = entries[name]
                actual_hash = hashlib.sha256(payload).hexdigest()
                if entry.get("sha256") != actual_hash:
                    return fail(f"file hash mismatch: {name}", 22)
                if entry.get("size") != len(payload):
                    return fail(f"file size mismatch: {name}", 23)
    except (BadZipFile, OSError) as exc:
        return fail(f"invalid ZIP archive: {exc}", 24)

    print(f"OK: verified {len(names)} files and release structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
