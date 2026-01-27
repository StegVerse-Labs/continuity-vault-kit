#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "vault_template"
DIST_DIR = REPO_ROOT / "dist"
VERSION_FILE = REPO_ROOT / "VERSION"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    zip_name = f"ContinuityVault_v{version}.zip"
    zip_path = DIST_DIR / zip_name

    if zip_path.exists():
        zip_path.unlink()

    # Create zip of vault_template contents
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as z:
        for root, _, files in os.walk(TEMPLATE_DIR):
            root_path = Path(root)
            for fname in files:
                fpath = root_path / fname
                rel = fpath.relative_to(TEMPLATE_DIR)
                z.write(fpath, arcname=str(rel))

    digest = sha256_file(zip_path)
    (DIST_DIR / f"{zip_name}.sha256").write_text(f"{digest}  {zip_name}\n", encoding="utf-8")

    manifest = {
        "artifact": zip_name,
        "version": version,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256": digest,
        "contents_root": "KnowledgeVault",
        "notes": "This ZIP contains the portable KnowledgeVault template and policy/index scaffolding."
    }
    (DIST_DIR / f"{zip_name}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Built: {zip_path}")
    print(f"SHA256: {digest}")

if __name__ == "__main__":
    sys.exit(main())
