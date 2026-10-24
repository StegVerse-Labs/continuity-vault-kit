mkdir -p reports/downstream_propagation
python3 - <<'PY'
import json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
tag=os.environ.get("EVENT_TAG") or os.environ.get("INPUT_TAG") or ""
if not tag:
    tags=subprocess.run(["git","tag","--sort=-version:refname"],text=True,capture_output=True,check=False).stdout.splitlines()
    tag=tags[0] if tags else ""
registry=json.loads(Path("automation/downstream-propagation.json").read_text(encoding="utf-8"))
results=[]
for destination in registry["destinations"]:
    results.append({
        "repository":destination["repository"],
        "default_branch":destination.get("default_branch","main"),
        "search_terms":destination["search_terms"],
        "determination":"NON_HOSTED_REVIEW_REQUIRED",
    })
payload={
    "schema":"stegverse.kv.downstream-propagation-observation/v1",
    "source_repository":os.environ["REPOSITORY"],
    "source_release":tag or None,
    "configured_destination_count":len(results),
    "results":results,
    "repository_mutation_performed":False,
    "issue_mutation_performed":False,
    "downstream_mutation_performed":False,
    "github_actions_role":"VALIDATION_TRANSPORT_ONLY",
    "canonical_next_transition":"NON_HOSTED_DOWNSTREAM_PROPAGATION_REVIEW",
    "authority_effect":"NONE",
    "observed_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
}
Path("reports/downstream_propagation/observation.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(payload,sort_keys=True))
PY
