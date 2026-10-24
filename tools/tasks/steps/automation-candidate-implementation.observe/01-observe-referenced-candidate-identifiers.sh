python3 - <<'PY'
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

text = os.environ.get("PR_TITLE", "") + "\n" + os.environ.get("PR_BODY", "")
patterns = [
    r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)",
    r"(?i)\bautomation[- ]candidate\s+#(\d+)",
]
numbers = sorted({int(value) for pattern in patterns for value in re.findall(pattern, text)})
out = Path("reports/automation_candidates")
out.mkdir(parents=True, exist_ok=True)
payload = {
    "schema": "stegverse.kv.automation-candidate-implementation-observation/v1",
    "state": "MERGED_PR_REFERENCES_OBSERVED" if numbers else "NO_CANDIDATE_REFERENCES_OBSERVED",
    "pull_request_number": int(os.environ["PR_NUMBER"]),
    "pull_request_url": os.environ["PR_URL"],
    "merge_sha": os.environ["MERGE_SHA"],
    "referenced_candidate_numbers": numbers,
    "candidate_support_state_resolved": False,
    "candidate_lifecycle_mutation_performed": False,
    "issue_mutation_performed": False,
    "changelog_mutation_performed": False,
    "repository_mutation_performed": False,
    "workflow_dispatch_performed": False,
    "release_authority": "NONE",
    "credential_authority": "TV/TVC",
    "github_actions_role": "VALIDATION_TRANSPORT_ONLY",
    "canonical_next_transition": "NON_HOSTED_CANDIDATE_RECONCILIATION" if numbers else "NONE",
    "authority_effect": "NONE",
    "observed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
}
(out / "candidate-implementation-observation.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(payload, sort_keys=True))
PY
