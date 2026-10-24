python3 - <<'PY'
from datetime import date
from pathlib import Path
current = Path("VERSION").read_text(encoding="utf-8").strip()
parts = current.split(".")
if len(parts) != 3 or not all(part.isdigit() for part in parts):
    raise SystemExit(f"VERSION is not semantic x.y.z: {current}")
major, minor, patch = map(int, parts)
next_version = f"{major}.{minor}.{patch + 1}"
Path("VERSION").write_text(next_version + "\n", encoding="utf-8")
changelog = Path("CHANGELOG.md")
text = changelog.read_text(encoding="utf-8")
marker = "## [Unreleased]"
replacement = "## [Unreleased]\n\n_No unreleased changes._\n\n---\n\n" + f"## [{next_version}] – {date.today().isoformat()}"
changelog.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
Path(".next-version").write_text(next_version + "\n", encoding="utf-8")
print(next_version)
PY
echo "value=$(cat .next-version)" >> "$GITHUB_OUTPUT"
