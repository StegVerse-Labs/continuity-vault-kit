#!/usr/bin/env python3
import json
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_VAULT = REPO_ROOT / "vault_template" / "KnowledgeVault"

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 tools/init_vault.py /path/to/target_dir")
        return 2

    target_dir = Path(sys.argv[1]).expanduser().resolve()
    target_vault = target_dir / "KnowledgeVault"

    if target_vault.exists():
        print(f"Refusing to overwrite existing: {target_vault}")
        return 3

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_VAULT, target_vault)

    manifest_path = target_vault / "_Meta" / "vault.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Initialized vault at: {target_vault}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
