python3 - <<'PY'
import json
from pathlib import Path
version = Path("VERSION").read_text(encoding="utf-8").strip()
manifest_path = Path("dist") / f"ContinuityVault_v{version}.zip.manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
required = {"schema_version", "artifact", "version", "created_utc", "sha256", "contents_root", "file_count", "files"}
missing = sorted(required - manifest.keys())
if missing:
    raise SystemExit(f"manifest missing fields: {missing}")
if manifest["file_count"] != len(manifest["files"]):
    raise SystemExit("manifest file_count does not match files inventory")
if not manifest["files"]:
    raise SystemExit("manifest files inventory is empty")
print(f"manifest validated: {manifest['file_count']} files")
PY
