python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path
release_required = os.environ.get("RELEASE_REQUIRED") == "true"
eligible = os.environ.get("ELIGIBLE_SOURCE") == "true"
state = "TVC_ADMITTED_RELEASE_CONTINUATION_REQUIRED" if release_required else "NO_RELEASE_REQUIRED" if eligible else "SOURCE_NOT_ELIGIBLE"
out = Path("reports/release_readiness")
out.mkdir(parents=True, exist_ok=True)
payload = {
    "schema": "stegverse.kv.release-readiness-hosted-observation/v1",
    "state": state,
    "reason": os.environ.get("REASON", ""),
    "source_workflow_conclusion": os.environ.get("SOURCE_CONCLUSION", ""),
    "source_head_sha": os.environ.get("SOURCE_HEAD_SHA", ""),
    "candidate_version": os.environ.get("CANDIDATE_VERSION") or None,
    "release_required": release_required,
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "repository_mutation_performed": False,
    "version_mutation_persisted": False,
    "changelog_mutation_persisted": False,
    "tag_mutation_performed": False,
    "release_publication_performed": False,
    "authority_effect": "NONE",
    "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
(out / "release-readiness-observation.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, sort_keys=True))
PY
