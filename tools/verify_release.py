#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 tools/verify_release.py dist/ContinuityVault_vX.Y.Z.zip")
        return 2

    zip_path = Path(sys.argv[1]).resolve()
    manifest_path = zip_path.with_suffix(zip_path.suffix + ".manifest.json")  # .zip.manifest.json
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")              # .zip.sha256

    if not zip_path.exists():
        print(f"Missing: {zip_path}")
        return 3

    digest = sha256_file(zip_path)
    print(f"Computed SHA256: {digest}")

    if sha_path.exists():
        expected = sha_path.read_text(encoding="utf-8").split()[0].strip()
        if expected != digest:
            print(f"FAIL: checksum mismatch. expected={expected}")
            return 4
        print("OK: checksum matches")

    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        if m.get("sha256") and m["sha256"] != digest:
            print("FAIL: manifest sha256 mismatch")
            return 5
        print("OK: manifest matches")

    # Basic structural validation
    with ZipFile(zip_path, "r") as z:
        names = set(z.namelist())
        required = {
            "KnowledgeVault/_Index/Master_Index.md",
            "KnowledgeVault/_Policy/Naming_Standard.md",
            "KnowledgeVault/_Meta/vault.manifest.json",
            "KnowledgeVault/00_Inbox/README.md"
        }
        missing = [r for r in required if r not in names]
        if missing:
            print("FAIL: missing required files:")
            for r in missing:
                print(f" - {r}")
            return 6

    print("OK: release bundle structure looks valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
