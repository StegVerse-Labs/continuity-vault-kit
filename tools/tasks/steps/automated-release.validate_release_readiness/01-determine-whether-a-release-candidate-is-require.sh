python3 - <<'PY'
import os
import subprocess
from pathlib import Path
conclusion = os.environ.get("SOURCE_CONCLUSION", "")
source_sha = os.environ.get("SOURCE_HEAD_SHA", "")
source_on_main = False
if source_sha:
    source_on_main = subprocess.run(["git", "merge-base", "--is-ancestor", source_sha, "HEAD"], check=False).returncode == 0
text = Path("CHANGELOG.md").read_text(encoding="utf-8")
marker = "## [Unreleased]"
if text.count(marker) != 1:
    raise SystemExit("CHANGELOG must contain exactly one Unreleased section")
section = text.split(marker, 1)[1].split("\n---", 1)[0]
normalized = " ".join(section.split()).lower()
substantive = normalized not in {"", "_no unreleased changes._", "no unreleased changes."}
eligible_source = conclusion == "success" and source_on_main
enabled = eligible_source and substantive
reason = (
    "release required; TVC-admitted publication continuation required"
    if enabled
    else "source integrity SHA is not contained in main or did not succeed"
    if not eligible_source
    else "no unreleased changes; release skipped"
)
with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
    handle.write(f"eligible_source={'true' if eligible_source else 'false'}\n")
    handle.write(f"source_on_main={'true' if source_on_main else 'false'}\n")
    handle.write(f"substantive={'true' if substantive else 'false'}\n")
    handle.write(f"enabled={'true' if enabled else 'false'}\n")
    handle.write(f"reason={reason}\n")
print(reason)
PY
