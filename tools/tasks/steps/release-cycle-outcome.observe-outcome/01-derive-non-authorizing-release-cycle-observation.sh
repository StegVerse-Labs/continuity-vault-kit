python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
marker = "## [Unreleased]"
start = changelog.index(marker) + len(marker)
end = changelog.find("\n---", start)
if end == -1:
    raise SystemExit("CHANGELOG Unreleased section terminator not found")
section = changelog[start:end].strip()
release_required = bool(section and section != "_No unreleased changes._")

conclusion = os.environ.get("SOURCE_CONCLUSION") or "manual-dispatch"
source_run_id = os.environ.get("SOURCE_RUN_ID") or os.environ["CURRENT_RUN_ID"]
source_sha = os.environ.get("SOURCE_HEAD_SHA") or ""
version = Path("VERSION").read_text(encoding="utf-8").strip()
state = "SOURCE_OBSERVED"
if conclusion not in {"success", "skipped", "manual-dispatch"}:
    state = "SOURCE_FAILURE_OBSERVED"
elif release_required:
    state = "RELEASE_CANDIDATE_REQUIRES_TVC_ADMISSION"

out = Path("reports/release_cycle")
out.mkdir(parents=True, exist_ok=True)
payload = {
    "schema": "stegverse.kv.release-cycle-hosted-observation/v1",
    "state": state,
    "source_workflow_conclusion": conclusion,
    "source_workflow_run_id": str(source_run_id),
    "source_head_sha": source_sha,
    "current_version": version,
    "release_required": release_required,
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "repository_mutation_performed": False,
    "canonical_evidence_transition_performed": False,
    "release_publication_performed": False,
    "authority_effect": "NONE",
}
(out / "hosted-release-cycle-observation.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
